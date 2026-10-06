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


class ResultadoSincronizacion:
    def __init__(self):
        self.enviados = 0
        self.pendientes = 0
        self.error: str | None = None
        self.rechazado = False

    @property
    def al_dia(self) -> bool:
        return self.pendientes == 0 and self.error is None


def sincronizar(conn: psycopg.Connection, cliente) -> ResultadoSincronizacion:
    """Envía los anclajes pendientes **en orden**. Se detiene en el primer fallo, para no
    anclar un hito antes que su predecesor.

    * Fabric no disponible → el anclaje queda PENDIENTE (modo degradado) y se reintenta luego.
    * Rechazo del chaincode → queda en ERROR: indica incoherencia y debe revisarlo un auditor.
    """
    from votoseguro.blockchain.cliente import AnclajeRechazado, PuenteNoDisponible

    r = ResultadoSincronizacion()
    filas = pendientes(conn)
    for i, (id_, funcion, argumentos) in enumerate(filas):
        try:
            tx_id = cliente.enviar(funcion, argumentos)
        except PuenteNoDisponible as e:
            conn.execute("UPDATE blockchain.outbox SET intentos = intentos + 1 WHERE id = %s", (id_,))
            r.error, r.pendientes = str(e), len(filas) - i
            return r
        except AnclajeRechazado as e:
            conn.execute("UPDATE blockchain.outbox SET intentos = intentos + 1, estado = 'ERROR' WHERE id = %s",
                         (id_,))
            r.error, r.rechazado, r.pendientes = str(e), True, len(filas) - i
            return r
        conn.execute("UPDATE blockchain.outbox SET intentos = intentos + 1, estado = 'ENVIADO', tx_id = %s "
                     "WHERE id = %s", (tx_id, id_))
        r.enviados += 1
    return r
