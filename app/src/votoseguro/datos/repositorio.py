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

def crear_eleccion(conn, definicion, mesa: str, clave_publica_pem: bytes, clave_privada_cifrada: bytes,
                   hash_configuracion: str) -> str:
    """Instala en este equipo la mesa ``mesa`` de la elección definida en ``definicion``."""
    return _ejecutar(conn, """
        INSERT INTO eleccion.eleccion (eleccion_global, mesa, nombre, sal_padron, hash_configuracion, definicion,
                                       clave_publica, clave_privada_cifrada, umbral, partes, checkpoint_cada)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id::text""",
        (definicion.eleccion_global, mesa, definicion.nombre, definicion.sal_padron, hash_configuracion,
         Jsonb(definicion.a_dict()),
         clave_publica_pem, clave_privada_cifrada, definicion.umbral, definicion.partes,
         definicion.checkpoint_cada)).fetchone()[0]


def insertar_opcion(conn, eleccion_id: str, opcion: Opcion) -> None:
    _ejecutar(conn, """
        INSERT INTO eleccion.opcion (eleccion_id, codigo, nombre, frente, orden, tipo)
        VALUES (%s, %s, %s, %s, %s, %s)""",
        (eleccion_id, opcion.codigo, opcion.nombre, opcion.frente, opcion.orden, opcion.tipo.value))


def obtener_eleccion(conn, eleccion_id: str) -> Eleccion:
    fila = _ejecutar(conn, """
        SELECT id::text, nombre, estado, clave_publica, umbral, partes, checkpoint_cada,
               eleccion_global::text, mesa, sal_padron, hash_configuracion
          FROM eleccion.eleccion WHERE id = %s""", (eleccion_id,)).fetchone()
    if fila is None:
        raise LookupError(f"no existe la elección {eleccion_id}")
    return Eleccion(fila[0], fila[1], Estado(fila[2]), bytes(fila[3]), *fila[4:])


def definicion(conn, eleccion_id: str) -> dict[str, Any]:
    return _ejecutar(conn, "SELECT definicion FROM eleccion.eleccion WHERE id = %s", (eleccion_id,)).fetchone()[0]


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
                     plantilla_cifrada: bytes | None, foto_cifrada: bytes | None) -> None:
    _ejecutar(conn, """
        INSERT INTO padron.votante (eleccion_id, ci, nombres, apellidos, plantilla_cifrada, foto_cifrada)
        VALUES (%s, %s, %s, %s, %s, %s)""", (eleccion_id, ci, nombres, apellidos, plantilla_cifrada, foto_cifrada))


def inhabilitar_votante(conn, eleccion_id: str, ci: str) -> bool:
    return _ejecutar(conn, """
        UPDATE padron.votante SET habilitado = false WHERE eleccion_id = %s AND ci = %s AND habilitado""",
        (eleccion_id, ci)).rowcount == 1


def registrar_presencia(conn, eleccion_id: str, ci: str, metodo: str, foto_cifrada: bytes | None) -> bool:
    """Registra la primera identificación del votante en la jornada. Devuelve False si ya existía."""
    return _ejecutar(conn, """
        INSERT INTO padron.presencia (eleccion_id, ci, metodo, foto_cifrada) VALUES (%s, %s, %s, %s)
        ON CONFLICT (eleccion_id, ci) DO NOTHING""", (eleccion_id, ci, metodo, foto_cifrada)).rowcount == 1


def padron_completo(conn, eleccion_id: str) -> list[dict[str, Any]]:
    """Padrón con participación (sin plantillas ni fotos), ordenado por CI."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT v.ci, v.nombres, v.apellidos, v.habilitado, v.ya_voto,
                   p.ci IS NOT NULL AS presente, p.metodo
              FROM padron.votante v
              LEFT JOIN padron.presencia p USING (eleccion_id, ci)
             WHERE v.eleccion_id = %s ORDER BY v.ci""", (eleccion_id,))
        return cur.fetchall()


def obtener_votante(conn, eleccion_id: str, ci: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT ci, nombres, apellidos, plantilla_cifrada, foto_cifrada, habilitado, ya_voto
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
