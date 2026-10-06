"""Consultas SQL usadas por los servicios. Ninguna función hace commit: las transacciones
las controla el servicio que llama (``with conn.transaction()``)."""

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from votoseguro.datos.conexion import traducir_error
from votoseguro.dominio.modelos import Eleccion, Estado, Opcion, TipoOpcion


def _ejecutar(conn: psycopg.Connection, sql: str, params: tuple | dict = ()):
    try:
        return conn.execute(sql, params)
    except psycopg.Error as e:
        raise traducir_error(e) from e


# --- Elección --------------------------------------------------------------------------------

def crear_eleccion(conn, nombre: str, clave_publica_pem: bytes, clave_privada_cifrada: bytes,
                   umbral: int, partes: int, checkpoint_cada: int) -> str:
    return _ejecutar(conn, """
        INSERT INTO eleccion.eleccion (nombre, clave_publica, clave_privada_cifrada, umbral, partes, checkpoint_cada)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id::text""",
        (nombre, clave_publica_pem, clave_privada_cifrada, umbral, partes, checkpoint_cada)).fetchone()[0]


def insertar_opcion(conn, eleccion_id: str, opcion: Opcion) -> None:
    _ejecutar(conn, """
        INSERT INTO eleccion.opcion (eleccion_id, codigo, nombre, frente, orden, tipo)
        VALUES (%s, %s, %s, %s, %s, %s)""",
        (eleccion_id, opcion.codigo, opcion.nombre, opcion.frente, opcion.orden, opcion.tipo.value))


def obtener_eleccion(conn, eleccion_id: str) -> Eleccion:
    fila = _ejecutar(conn, """
        SELECT id::text, nombre, estado, clave_publica, umbral, partes, checkpoint_cada
          FROM eleccion.eleccion WHERE id = %s""", (eleccion_id,)).fetchone()
    if fila is None:
        raise LookupError(f"no existe la elección {eleccion_id}")
    return Eleccion(fila[0], fila[1], Estado(fila[2]), bytes(fila[3]), fila[4], fila[5], fila[6])


def clave_privada_cifrada(conn, eleccion_id: str) -> bytes:
    return bytes(_ejecutar(conn, "SELECT clave_privada_cifrada FROM eleccion.eleccion WHERE id = %s",
                           (eleccion_id,)).fetchone()[0])


def opciones(conn, eleccion_id: str) -> list[Opcion]:
    filas = _ejecutar(conn, """
        SELECT codigo, nombre, tipo, orden, frente FROM eleccion.opcion
         WHERE eleccion_id = %s ORDER BY orden""", (eleccion_id,)).fetchall()
    return [Opcion(c, n, TipoOpcion(t), o, f) for c, n, t, o, f in filas]


def cambiar_estado(conn, eleccion_id: str, nuevo: Estado) -> None:
    _ejecutar(conn, "UPDATE eleccion.eleccion SET estado = %s WHERE id = %s", (nuevo.value, eleccion_id))


# --- Padrón ----------------------------------------------------------------------------------

def insertar_votante(conn, eleccion_id: str, ci: str, nombres: str, apellidos: str,
                     plantilla_cifrada: bytes | None) -> None:
    _ejecutar(conn, """
        INSERT INTO padron.votante (eleccion_id, ci, nombres, apellidos, plantilla_cifrada)
        VALUES (%s, %s, %s, %s, %s)""", (eleccion_id, ci, nombres, apellidos, plantilla_cifrada))


def obtener_votante(conn, eleccion_id: str, ci: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT ci, nombres, apellidos, plantilla_cifrada, habilitado, ya_voto
              FROM padron.votante WHERE eleccion_id = %s AND ci = %s""", (eleccion_id, ci))
        return cur.fetchone()


def cis_padron(conn, eleccion_id: str) -> list[str]:
    return [f[0] for f in _ejecutar(
        conn, "SELECT ci FROM padron.votante WHERE eleccion_id = %s ORDER BY ci", (eleccion_id,)).fetchall()]


def conteos_padron(conn, eleccion_id: str) -> dict[str, int]:
    total, habilitados, votaron = _ejecutar(conn, """
        SELECT count(*), count(*) FILTER (WHERE habilitado), count(*) FILTER (WHERE ya_voto)
          FROM padron.votante WHERE eleccion_id = %s""", (eleccion_id,)).fetchone()
    return {"total": total, "habilitados": habilitados, "votaron": votaron}


# --- Urna y checkpoints ----------------------------------------------------------------------

def contar_votos(conn, eleccion_id: str) -> int:
    return _ejecutar(conn, "SELECT count(*) FROM urna.voto WHERE eleccion_id = %s",
                     (eleccion_id,)).fetchone()[0]


def votos(conn, eleccion_id: str) -> list[tuple[bytes, str]]:
    """Votos cifrados ordenados por hash (nunca por orden de emisión)."""
    return [(bytes(v), h) for v, h in _ejecutar(conn, """
        SELECT voto_cifrado, hash_voto FROM urna.voto WHERE eleccion_id = %s ORDER BY hash_voto""",
        (eleccion_id,)).fetchall()]


def insertar_checkpoint(conn, eleccion_id: str, seq: int, conteo: int, raiz: str) -> None:
    _ejecutar(conn, """
        INSERT INTO eleccion.checkpoint (eleccion_id, seq, conteo, raiz_merkle) VALUES (%s, %s, %s, %s)""",
        (eleccion_id, seq, conteo, raiz))


def checkpoints(conn, eleccion_id: str) -> list[dict[str, Any]]:
    filas = _ejecutar(conn, """
        SELECT seq, conteo, raiz_merkle FROM eleccion.checkpoint WHERE eleccion_id = %s ORDER BY seq""",
        (eleccion_id,)).fetchall()
    return [{"seq": s, "conteo": c, "raiz_merkle": r} for s, c, r in filas]


# --- Actas -----------------------------------------------------------------------------------

def insertar_acta(conn, eleccion_id: str, tipo: str, contenido: dict, hash_: str, firma: bytes) -> str:
    return _ejecutar(conn, """
        INSERT INTO eleccion.acta (eleccion_id, tipo, contenido, hash, firma)
        VALUES (%s, %s, %s, %s, %s) RETURNING id::text""",
        (eleccion_id, tipo, Jsonb(contenido), hash_, firma)).fetchone()[0]


def actas(conn, eleccion_id: str) -> dict[str, dict[str, Any]]:
    filas = _ejecutar(conn, "SELECT tipo, contenido, hash, firma FROM eleccion.acta WHERE eleccion_id = %s",
                      (eleccion_id,)).fetchall()
    return {t: {"contenido": c, "hash": h, "firma": bytes(f)} for t, c, h, f in filas}


# --- Bitácora --------------------------------------------------------------------------------

def bitacora_completa(conn) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT seq, momento, actor, evento, detalle, hash_anterior, hash
                         FROM auditoria.bitacora ORDER BY seq""")
        return cur.fetchall()


def contar_eventos(conn, eleccion_id: str, evento: str) -> int:
    return _ejecutar(conn, """
        SELECT count(*) FROM auditoria.bitacora WHERE evento = %s AND detalle->>'eleccion' = %s""",
        (evento, eleccion_id)).fetchone()[0]


def ultimo_hash_bitacora(conn) -> str:
    fila = _ejecutar(conn, "SELECT hash FROM auditoria.bitacora ORDER BY seq DESC LIMIT 1").fetchone()
    return fila[0] if fila else "0" * 64


def outbox(conn) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, funcion, argumentos, estado, tx_id FROM blockchain.outbox ORDER BY id")
        return cur.fetchall()
