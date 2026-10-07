"""Fase 2 — Empadronamiento en la propia urna: datos personales, foto y huella (ADR-009).

Incluye el **cruce de padrones** entre mesas: cada urna exporta un resumen cifrado y firmado de
su padrón (``.vsp``); el cruce detecta CI empadronados en más de una mesa, para inhabilitarlos
en todas menos una antes de la apertura.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from votoseguro.auditoria import bitacora
from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import canonico
from votoseguro.cripto.llavero import b64, cifrar_con_frase, descifrar_con_frase, desde_b64
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado
from votoseguro.hardware.huella import LectorNoDisponible
from votoseguro.hardware.impresora import Documento
from votoseguro.servicios.base import Contexto, ErrorServicio, HardwareNoDisponible, exigir_estado

CONTEXTO_RESUMEN = b"votoseguro:resumen-padron"


def iniciar(ctx: Contexto, eleccion_id: str) -> None:
    exigir_estado(ctx, eleccion_id, Estado.CONFIGURACION)
    with ctx.conn.transaction():
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.EMPADRONAMIENTO)
        bitacora.registrar(ctx.conn, ctx.actor, "EMPADRONAMIENTO_INICIADO", {"eleccion": eleccion_id})


def registrar_votante(ctx: Contexto, eleccion_id: str, ci: str, nombres: str, apellidos: str) -> None:
    """Toma la foto de registro y la huella (la persona debe estar frente a la cámara y con el
    dedo sobre el lector) y agrega al votante al padrón. Foto y plantilla se guardan cifradas.
    Imprime la constancia de empadronamiento para el votante."""
    eleccion = exigir_estado(ctx, eleccion_id, Estado.EMPADRONAMIENTO)
    foto = ctx.tomar_foto()
    try:
        plantilla = ctx.lector.capturar()
    except LectorNoDisponible as e:
        raise HardwareNoDisponible(str(e)) from e
    with ctx.conn.transaction():
        repo.insertar_votante(
            ctx.conn, eleccion_id, ci, nombres.strip(), apellidos.strip(),
            ctx.llavero.cifrar_personal("plantilla", eleccion_id, ci, plantilla),
            ctx.llavero.cifrar_personal("foto_registro", eleccion_id, ci, foto))
        bitacora.registrar(ctx.conn, ctx.actor, "VOTANTE_REGISTRADO", {"eleccion": eleccion_id, "ci": ci})
    ctx.impresora.imprimir_documento(Documento(
        "CONSTANCIA DE EMPADRONAMIENTO",
        [f"Elección: {eleccion.nombre}", f"Mesa: {eleccion.mesa}", "",
         f"Cédula de identidad: {ci}", f"Apellidos: {apellidos.strip()}", f"Nombres: {nombres.strip()}",
         f"Fecha de registro: {datetime.now().strftime('%d/%m/%Y %H:%M')}", "",
         "Huella dactilar: registrada (se guarda solo la plantilla, cifrada)",
         "Fotografía: registrada (cifrada)", "",
         f"El día de la votación preséntese en la mesa {eleccion.mesa} con su cédula de identidad.",
         "", "Firma del operador: ______________________"],
        None, f"constancia_{ci}", foto))


def inhabilitar_votante(ctx: Contexto, eleccion_id: str, ci: str, motivo: str) -> None:
    """Quita a un votante del padrón activo (p. ej. empadronado también en otra mesa)."""
    exigir_estado(ctx, eleccion_id, Estado.EMPADRONAMIENTO)
    if len(motivo.strip()) < 10:
        raise ValueError("describa el motivo (mínimo 10 caracteres)")
    with ctx.conn.transaction():
        if not repo.inhabilitar_votante(ctx.conn, eleccion_id, ci):
            raise ErrorServicio(f"el CI {ci} no está en el padrón o ya estaba inhabilitado")
        bitacora.registrar(ctx.conn, ctx.actor, "VOTANTE_INHABILITADO",
                           {"eleccion": eleccion_id, "ci": ci, "motivo": motivo.strip()})


def cerrar_padron(ctx: Contexto, eleccion_id: str) -> dict[str, int]:
    exigir_estado(ctx, eleccion_id, Estado.EMPADRONAMIENTO)
    conteos = repo.conteos_padron(ctx.conn, eleccion_id)
    if conteos["habilitados"] == 0:
        raise ValueError("el padrón no tiene votantes habilitados")
    with ctx.conn.transaction():
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.LISTA)
        bitacora.registrar(ctx.conn, ctx.actor, "PADRON_CERRADO", {"eleccion": eleccion_id, **conteos})
    return conteos


# --- Cruce de padrones entre mesas -----------------------------------------------------------

def exportar_resumen_padron(ctx: Contexto, eleccion_id: str, carpeta: Path, frase: str) -> Path:
    """Resumen del padrón de esta mesa (CI y nombres, sin fotos ni huellas), firmado y cifrado."""
    eleccion = exigir_estado(ctx, eleccion_id, Estado.EMPADRONAMIENTO, Estado.LISTA)
    cuerpo = {
        "eleccion_global": eleccion.eleccion_global, "mesa": eleccion.mesa,
        "hash_configuracion": eleccion.hash_configuracion,
        "votantes": [{"ci": v["ci"], "nombres": v["nombres"], "apellidos": v["apellidos"]}
                     for v in repo.padron_completo(ctx.conn, eleccion_id) if v["habilitado"]],
    }
    publica_pem = ctx.llavero.clave_firma.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    contenido = json.dumps({"resumen": cuerpo, "firma": b64(firmas.firmar(ctx.llavero.clave_firma, canonico(cuerpo))),
                            "clave_publica_pem": publica_pem.decode()}).encode()
    ruta = Path(carpeta) / f"padron_mesa{eleccion.mesa}.vsp"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(cifrar_con_frase(contenido, frase, CONTEXTO_RESUMEN))
    bitacora.registrar(ctx.conn, ctx.actor, "RESUMEN_PADRON_EXPORTADO",
                       {"eleccion": eleccion_id, "habilitados": len(cuerpo["votantes"])})
    return ruta


@dataclass
class ResultadoCruce:
    mesas: list[str]
    total_votantes: int
    duplicados: dict[str, list[str]] = field(default_factory=dict)   # CI → mesas
    firmas_invalidas: list[str] = field(default_factory=list)

    @property
    def limpio(self) -> bool:
        return not self.duplicados and not self.firmas_invalidas


def cruzar_padrones(rutas: list[Path], frase: str) -> ResultadoCruce:
    """Detecta CI empadronados en más de una mesa de la misma elección."""
    resumenes = []
    invalidas = []
    for ruta in rutas:
        datos = json.loads(descifrar_con_frase(Path(ruta).read_bytes(), frase, CONTEXTO_RESUMEN))
        publica = serialization.load_pem_public_key(datos["clave_publica_pem"].encode())
        if not firmas.verificar(publica, canonico(datos["resumen"]), desde_b64(datos["firma"])):
            invalidas.append(str(ruta))
            continue
        resumenes.append(datos["resumen"])
    if len({(r["eleccion_global"], r["hash_configuracion"]) for r in resumenes}) > 1:
        raise ErrorServicio("los resúmenes pertenecen a elecciones o definiciones distintas")
    mesas_por_ci = defaultdict(list)
    for r in resumenes:
        for v in r["votantes"]:
            mesas_por_ci[v["ci"]].append(r["mesa"])
    return ResultadoCruce(
        mesas=sorted(r["mesa"] for r in resumenes),
        total_votantes=sum(len(r["votantes"]) for r in resumenes),
        duplicados={ci: sorted(m) for ci, m in mesas_por_ci.items() if len(m) > 1},
        firmas_invalidas=invalidas,
    )
