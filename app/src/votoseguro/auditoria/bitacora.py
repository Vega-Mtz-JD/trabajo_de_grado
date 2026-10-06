"""Bitácora de auditoría encadenada (ADR-004).

Cada entrada guarda el hash de la anterior y su propio hash:

    hash_i = SHA3-256( hash_{i-1} ‖ JSON canónico {momento, actor, evento, detalle} )

Alterar, borrar o reordenar cualquier entrada rompe la cadena desde ese punto, y el
verificador lo detecta. Además, la base de datos impide UPDATE/DELETE (triggers) y exige
que cada inserción apunte al último hash.

Regla de secreto del voto: el detalle **nunca** debe contener el identificador ni el hash
de un voto, ni nada que vincule a un votante con su voto.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from votoseguro.cripto.hashing import canonico, sha3
from votoseguro.datos.conexion import traducir_error

HASH_GENESIS = "0" * 64

# Claves que nunca deben aparecer en el detalle de un evento (secreto del voto).
_CLAVES_PROHIBIDAS = {"voto", "voto_id", "hash_voto", "voto_cifrado", "opcion"}


@dataclass(frozen=True)
class Entrada:
    seq: int
    momento: datetime
    actor: str
    evento: str
    detalle: dict[str, Any]
    hash_anterior: str
    hash: str


@dataclass(frozen=True)
class ResultadoVerificacion:
    integra: bool
    entradas: int
    primera_falla: int | None = None
    motivo: str = ""


def _momento_texto(momento: datetime) -> str:
    # Precisión de microsegundos en UTC: es lo que conserva timestamptz de PostgreSQL.
    return momento.astimezone(UTC).isoformat(timespec="microseconds")


def calcular_hash(hash_anterior: str, momento: datetime, actor: str, evento: str,
                  detalle: dict[str, Any]) -> str:
    contenido = canonico({
        "momento": _momento_texto(momento),
        "actor": actor,
        "evento": evento,
        "detalle": detalle,
    })
    return sha3(bytes.fromhex(hash_anterior) + contenido)


def registrar(conn: psycopg.Connection, actor: str, evento: str,
              detalle: dict[str, Any] | None = None) -> Entrada:
    """Agrega un evento a la bitácora (dentro de la transacción en curso)."""
    detalle = detalle or {}
    prohibidas = _CLAVES_PROHIBIDAS & set(detalle)
    if prohibidas:
        raise ValueError(f"la bitácora no puede registrar datos del voto: {sorted(prohibidas)}")
    momento = datetime.now(UTC)
    try:
        # Serializa a los escritores concurrentes, igual que el trigger de la BD.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('auditoria.bitacora'))")
        fila = conn.execute(
            "SELECT hash FROM auditoria.bitacora ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        anterior = fila[0] if fila else HASH_GENESIS
        nuevo = calcular_hash(anterior, momento, actor, evento, detalle)
        seq = conn.execute(
            """INSERT INTO auditoria.bitacora (momento, actor, evento, detalle, hash_anterior, hash)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING seq""",
            (momento, actor, evento, Jsonb(detalle), anterior, nuevo),
        ).fetchone()[0]
    except psycopg.Error as e:
        raise traducir_error(e) from e
    return Entrada(seq, momento, actor, evento, detalle, anterior, nuevo)


def verificar(conn: psycopg.Connection, ultimo_hash_anclado: str | None = None) -> ResultadoVerificacion:
    """Recorre la bitácora completa y recalcula la cadena de hashes.

    La cadena por sí sola no detecta que se borren las *últimas* entradas. Por eso el hash
    final se ancla fuera de la BD (acta impresa y Fabric); si se pasa ``ultimo_hash_anclado``,
    se exige que la bitácora contenga esa entrada.
    """
    filas = conn.execute(
        """SELECT seq, momento, actor, evento, detalle, hash_anterior, hash
             FROM auditoria.bitacora ORDER BY seq"""
    ).fetchall()
    anterior = HASH_GENESIS
    for seq, momento, actor, evento, detalle, hash_anterior, hash_guardado in filas:
        if hash_anterior != anterior:
            return ResultadoVerificacion(False, len(filas), seq, "enlace con la entrada anterior roto")
        if calcular_hash(hash_anterior, momento, actor, evento, detalle) != hash_guardado:
            return ResultadoVerificacion(False, len(filas), seq, "contenido alterado")
        anterior = hash_guardado
    if ultimo_hash_anclado is not None and ultimo_hash_anclado not in {f[6] for f in filas}:
        return ResultadoVerificacion(False, len(filas), None, "falta la entrada anclada (¿entradas eliminadas?)")
    return ResultadoVerificacion(True, len(filas))
