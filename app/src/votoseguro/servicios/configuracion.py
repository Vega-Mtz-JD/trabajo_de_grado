"""Fase 1 — Configuración (ADR-003, ADR-009).

1. ``definir_eleccion``: nombre, opciones (más BLANCO y NULO), mesas, umbral de custodios.
2. ``exportar_definicion`` / ``importar_definicion``: archivo ``.vsd`` cifrado y firmado para llevar
   la misma definición a las demás urnas. No contiene datos personales.
3. ``instalar_mesa``: en cada urna, crea su mesa con **su propia** clave de elección y reparte
   la clave entre los custodios (jurados) de esa mesa.

``crear_eleccion`` hace 1 + 3 en un solo paso, para una elección de una sola urna.
"""

import json
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import canonico, hash_canonico
from votoseguro.cripto.llavero import b64, cifrar_con_frase, descifrar_con_frase, desde_b64
from votoseguro.cripto.shamir import Parte
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Definicion, Opcion, TipoOpcion
from votoseguro.hardware.impresora import Documento
from votoseguro.servicios.base import Contexto, ErrorServicio

CONTEXTO_DEFINICION = b"votoseguro:definicion"


class DefinicionInvalida(ErrorServicio):
    pass


@dataclass(frozen=True)
class Candidatura:
    codigo: str
    nombre: str
    frente: str | None = None


@dataclass(frozen=True)
class EleccionCreada:
    eleccion_id: str
    partes: list[Parte]
    hash_configuracion: str


def definir_eleccion(nombre: str, candidaturas: list[Candidatura], *, mesas: list[str] | None = None,
                     umbral: int = 3, partes: int = 5, checkpoint_cada: int = 10) -> Definicion:
    if not candidaturas:
        raise ValueError("se requiere al menos una candidatura")
    mesas = mesas or ["01"]
    if len(set(mesas)) != len(mesas):
        raise ValueError("los códigos de mesa deben ser distintos")
    opciones = [Opcion(c.codigo, c.nombre, TipoOpcion.CANDIDATO, i, c.frente)
                for i, c in enumerate(candidaturas, 1)]
    opciones += [Opcion("BLANCO", "VOTO BLANCO", TipoOpcion.BLANCO, len(opciones) + 1),
                 Opcion("NULO", "VOTO NULO", TipoOpcion.NULO, len(opciones) + 2)]
    return Definicion(str(uuid.uuid4()), nombre, tuple(opciones), tuple(mesas), umbral, partes,
                      checkpoint_cada, secrets.token_hex(16))


def hash_definicion(definicion: Definicion) -> str:
    return hash_canonico(definicion.a_dict())


# --- Definición exportable -----------------------------------------------------------------------

def exportar_definicion(ctx: Contexto, definicion: Definicion, ruta: Path, frase: str) -> str:
    """Guarda la definición firmada por este equipo y cifrada con ``frase``. Imprime una hoja con
    el hash y la huella del equipo, para comprobarlos al importar en las otras urnas."""
    cuerpo = definicion.a_dict()
    publica_pem = ctx.llavero.clave_firma.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    contenido = json.dumps({
        "definicion": cuerpo,
        "firma": b64(firmas.firmar(ctx.llavero.clave_firma, canonico(cuerpo))),
        "clave_publica_pem": publica_pem.decode(),
    }).encode()
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(cifrar_con_frase(contenido, frase, CONTEXTO_DEFINICION))
    h = hash_definicion(definicion)
    bitacora.registrar(ctx.conn, ctx.actor, "DEFINICION_EXPORTADA",
                       {"eleccion_global": definicion.eleccion_global, "hash_configuracion": h})
    ctx.impresora.imprimir_documento(Documento(
        "DEFINICIÓN DE ELECCIÓN — HOJA DE CONTROL",
        [f"Elección: {definicion.nombre}", f"Identificador global: {definicion.eleccion_global}",
         f"Mesas: {', '.join(definicion.mesas)}",
         f"Opciones: {', '.join(o.codigo for o in definicion.opciones)}", "",
         f"HASH DE LA DEFINICIÓN: {h}", f"HUELLA DEL EQUIPO:     {ctx.llavero.huella_dispositivo}", "",
         "Compare ambos valores en cada urna al importar la definición."],
        h, "definicion_eleccion"))
    return h


def importar_definicion(ruta: Path, frase: str, huella_esperada: str | None = None) -> Definicion:
    """Descifra la definición y verifica su firma. Si se da ``huella_esperada`` (de la hoja de
    control impresa), exige que el equipo firmante sea ese."""
    try:
        datos = json.loads(descifrar_con_frase(Path(ruta).read_bytes(), frase, CONTEXTO_DEFINICION))
        publica = serialization.load_pem_public_key(datos["clave_publica_pem"].encode())
        firma = desde_b64(datos["firma"])
    except Exception as e:  # frase incorrecta, archivo dañado o con formato inválido
        raise DefinicionInvalida("no se pudo abrir la definición (frase incorrecta o archivo dañado)") from e
    if not firmas.verificar(publica, canonico(datos["definicion"]), firma):
        raise DefinicionInvalida("la firma de la definición no es válida")
    if huella_esperada and firmas.huella(publica) != huella_esperada.strip().lower():
        raise DefinicionInvalida("la definición no fue firmada por el equipo esperado")
    return Definicion.desde_dict(datos["definicion"])


# --- Instalación de una mesa -----------------------------------------------------------------

def instalar_mesa(ctx: Contexto, definicion: Definicion, mesa: str, *, custodios: list[str] | None = None,
                  bits: int = cv.BITS_CLAVE_ELECCION) -> EleccionCreada:
    """Crea la mesa en este equipo con su propia clave y custodia (umbral de ``definicion``).

    Imprime una hoja por custodio con su parte de la clave (texto + QR). La clave que
    reconstruyen las partes no se guarda en ningún lugar.
    """
    if mesa not in definicion.mesas:
        raise DefinicionInvalida(f"la mesa {mesa} no figura en la definición ({', '.join(definicion.mesas)})")
    custodios = custodios or [f"Custodio {i} — mesa {mesa}" for i in range(1, definicion.partes + 1)]
    if len(custodios) != definicion.partes:
        raise ValueError("debe haber un nombre por cada custodio")

    privada = cv.generar_clave_eleccion(bits)
    publica_pem = cv.publica_a_pem(privada.public_key())
    privada_cifrada, partes = cv.custodiar_clave(privada, definicion.umbral, definicion.partes)
    del privada  # a partir de aquí solo existe cifrada y repartida
    huella_clave = firmas.huella(cv.publica_desde_pem(publica_pem))
    h = hash_definicion(definicion)

    with ctx.conn.transaction():
        eid = repo.crear_eleccion(ctx.conn, definicion, mesa, publica_pem, privada_cifrada, h)
        for o in definicion.opciones:
            repo.insertar_opcion(ctx.conn, eid, o)
        bitacora.registrar(ctx.conn, ctx.actor, "MESA_INSTALADA", {
            "eleccion": eid, "eleccion_global": definicion.eleccion_global, "mesa": mesa,
            "hash_configuracion": h, "huella_clave_eleccion": huella_clave,
            "umbral": definicion.umbral, "partes": definicion.partes,
        })
        outbox.encolar(ctx.conn, "RegistrarEleccion", {
            "eleccion_global": definicion.eleccion_global, "mesa": mesa, "hash_configuracion": h,
            "huella_clave_eleccion": huella_clave, "huella_dispositivo": ctx.llavero.huella_dispositivo,
        })

    for parte, custodio in zip(partes, custodios):
        ctx.impresora.imprimir_documento(Documento(
            f"PARTE DE CLAVE — {custodio.upper()}",
            [f"Elección: {definicion.nombre}", f"Mesa: {mesa}", f"Identificador: {eid}",
             f"Parte {parte.x} de {definicion.partes} (se requieren {definicion.umbral} para el escrutinio)", "",
             parte.a_texto(), "",
             "Guarde esta hoja en un sobre sellado y firmado.",
             "Sin el número mínimo de partes los votos de esta mesa NO pueden contarse."],
            parte.a_texto(), f"parte_mesa{mesa}_custodio_{parte.x}"))
    return EleccionCreada(eid, partes, h)


def crear_eleccion(ctx: Contexto, nombre: str, candidaturas: list[Candidatura], *, mesa: str = "01",
                   umbral: int = 3, partes: int = 5, checkpoint_cada: int = 10,
                   custodios: list[str] | None = None, bits: int = cv.BITS_CLAVE_ELECCION) -> EleccionCreada:
    """Elección de una sola urna: define e instala la mesa en un paso."""
    definicion = definir_eleccion(nombre, candidaturas, mesas=[mesa], umbral=umbral, partes=partes,
                                  checkpoint_cada=checkpoint_cada)
    return instalar_mesa(ctx, definicion, mesa, custodios=custodios, bits=bits)
