"""Cola de anclajes pendientes para Fabric (patrón *outbox*, ADR-002).

Cada hito electoral se registra en ``blockchain.outbox`` dentro de la misma transacción
que el cambio de estado. Un trabajador (Sprint 3) los envía al puente Go en orden y de
forma idempotente. Si Fabric no está disponible, la votación continúa (modo degradado).

Regla: los argumentos solo contienen hashes, conteos y raíces de Merkle; nunca datos
personales, porque el ledger no permite borrar.
"""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

FUNCIONES = {
    "RegistrarEleccion", "RegistrarApertura", "RegistrarCheckpoint",
    "RegistrarCierre", "RegistrarEscrutinio", "RegistrarExportacion",
}
_CLAVES_PROHIBIDAS = {"ci", "nombres", "apellidos", "plantilla", "voto_cifrado"}


def encolar(conn: psycopg.Connection, funcion: str, argumentos: dict[str, Any]) -> int:
    if funcion not in FUNCIONES:
        raise ValueError(f"función de chaincode desconocida: {funcion}")
    if _CLAVES_PROHIBIDAS & set(argumentos):
        raise ValueError("no se pueden enviar datos personales al ledger")
    return conn.execute(
        "INSERT INTO blockchain.outbox (funcion, argumentos) VALUES (%s, %s) RETURNING id",
        (funcion, Jsonb(argumentos)),
    ).fetchone()[0]


def pendientes(conn: psycopg.Connection) -> list[tuple[int, str, dict]]:
    return conn.execute(
        "SELECT id, funcion, argumentos FROM blockchain.outbox WHERE estado <> 'ENVIADO' ORDER BY id"
    ).fetchall()
