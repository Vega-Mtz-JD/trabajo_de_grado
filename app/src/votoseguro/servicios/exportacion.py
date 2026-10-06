"""Fase 10 — Exportación: paquete de auditoría cifrado para el USB.

El paquete (.vsx) es un ZIP cifrado con AES-256-GCM (clave derivada de una frase con
Argon2id) que contiene el expediente completo de la elección en JSON canónico y un
manifiesto con el SHA3-256 de cada archivo, firmado por el dispositivo.
"""

import io
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import canonico, sha3
from votoseguro.cripto.llavero import b64, cifrar_con_frase
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado
from votoseguro.servicios.base import Contexto, exigir_estado

CONTEXTO_PAQUETE = b"votoseguro:paquete"


@dataclass(frozen=True)
class PaqueteExportado:
    ruta: Path
    hash_manifiesto: str


def reunir_expediente(conn, eleccion_id: str, clave_publica_dispositivo_pem: bytes) -> dict[str, Any]:
    """Arma el expediente de la elección (lo mismo que se exporta y que verifica el auditor)."""
    eleccion = repo.obtener_eleccion(conn, eleccion_id)
    return {
        "eleccion.json": {
            "id": eleccion.id, "nombre": eleccion.nombre, "estado": eleccion.estado.value,
            "umbral": eleccion.umbral, "partes": eleccion.partes, "checkpoint_cada": eleccion.checkpoint_cada,
            "clave_publica_pem": eleccion.clave_publica_pem.decode(),
            "opciones": [{"codigo": o.codigo, "nombre": o.nombre, "tipo": o.tipo.value, "orden": o.orden}
                         for o in repo.opciones(conn, eleccion_id)],
        },
        "votos.json": [{"hash": h, "cifrado": b64(c)} for c, h in repo.votos(conn, eleccion_id)],
        "actas.json": {t: {"contenido": a["contenido"], "hash": a["hash"], "firma": b64(a["firma"])}
                       for t, a in repo.actas(conn, eleccion_id).items()},
        "checkpoints.json": repo.checkpoints(conn, eleccion_id),
        "bitacora.json": [{**e, "momento": bitacora.momento_texto(e["momento"])}
                          for e in repo.bitacora_completa(conn)],
        "outbox.json": [{"id": o["id"], "funcion": o["funcion"], "argumentos": o["argumentos"],
                         "estado": o["estado"]} for o in repo.outbox(conn)],
        "dispositivo.json": {"clave_publica_pem": clave_publica_dispositivo_pem.decode(),
                             "huella": firmas.huella(serialization.load_pem_public_key(
                                 clave_publica_dispositivo_pem))},
    }


def _zip(archivos: dict[str, bytes]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, datos in sorted(archivos.items()):
            info = zipfile.ZipInfo(nombre, date_time=(1980, 1, 1, 0, 0, 0))  # reproducible
            z.writestr(info, datos)
    return memoria.getvalue()


def exportar(ctx: Contexto, eleccion_id: str, carpeta: Path, frase: str) -> PaqueteExportado:
    exigir_estado(ctx, eleccion_id, Estado.ESCRUTADA)
    publica_pem = ctx.llavero.clave_firma.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    archivos = {n: canonico(c) for n, c in reunir_expediente(ctx.conn, eleccion_id, publica_pem).items()}
    manifiesto = canonico({
        "eleccion_id": eleccion_id,
        "archivos": {n: sha3(d) for n, d in archivos.items()},
        "huella_dispositivo": ctx.llavero.huella_dispositivo,
        "momento": datetime.now(UTC).isoformat(timespec="seconds"),
    })
    archivos["manifiesto.json"] = manifiesto
    archivos["manifiesto.firma"] = firmas.firmar(ctx.llavero.clave_firma, manifiesto)
    hash_manifiesto = sha3(manifiesto)

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"votoseguro_{eleccion_id[:8]}.vsx"
    ruta.write_bytes(cifrar_con_frase(_zip(archivos), frase, CONTEXTO_PAQUETE))

    with ctx.conn.transaction():
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.EXPORTADA)
        bitacora.registrar(ctx.conn, ctx.actor, "EXPORTACION",
                           {"eleccion": eleccion_id, "hash_manifiesto": hash_manifiesto})
        outbox.encolar(ctx.conn, "RegistrarExportacion",
                       {"eleccion_id": eleccion_id, "hash_manifiesto": hash_manifiesto})
    return PaqueteExportado(ruta, hash_manifiesto)
