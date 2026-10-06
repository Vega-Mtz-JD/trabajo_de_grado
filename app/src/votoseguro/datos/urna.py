"""Operaciones sobre la urna: emisión atómica del voto y mezcla (ADR-004, ADR-008)."""

from dataclasses import dataclass

import psycopg

from votoseguro.datos.conexion import traducir_error


@dataclass(frozen=True)
class HuellaUrna:
    conteo: int
    huella: str


def emitir_voto(
    conn: psycopg.Connection, eleccion_id: str, ci: str, voto_cifrado: bytes, hash_voto: str
) -> int:
    """Marca al votante y deposita su voto cifrado en una sola transacción.

    Devuelve el total de votos de la elección. Lanza ``VotanteNoHabilitado`` o
    ``EleccionNoAbierta`` según corresponda. No hace commit: lo decide quien llama.
    """
    try:
        fila = conn.execute(
            "SELECT urna.emitir_voto(%s, %s, %s, %s)", (eleccion_id, ci, voto_cifrado, hash_voto)
        ).fetchone()
    except psycopg.Error as e:
        raise traducir_error(e) from e
    return int(fila[0])


def mezclar(conn: psycopg.Connection) -> HuellaUrna:
    """Reescribe la urna en orden aleatorio; verifica que el contenido no cambie."""
    try:
        conteo, huella = conn.execute("SELECT * FROM urna.mezclar()").fetchone()
    except psycopg.Error as e:
        raise traducir_error(e) from e
    return HuellaUrna(int(conteo), huella)


def huella(conn: psycopg.Connection) -> HuellaUrna:
    conteo, valor = conn.execute("SELECT * FROM urna.huella_urna()").fetchone()
    return HuellaUrna(int(conteo), valor)


def hashes_votos(conn: psycopg.Connection, eleccion_id: str) -> list[str]:
    """Hashes de los votos de la elección, en orden lexicográfico (para la raíz de Merkle)."""
    filas = conn.execute(
        "SELECT hash_voto FROM urna.voto WHERE eleccion_id = %s ORDER BY hash_voto", (eleccion_id,)
    ).fetchall()
    return [f[0] for f in filas]
