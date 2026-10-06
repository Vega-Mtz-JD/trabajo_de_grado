"""Migraciones versionadas del esquema (ADR-011).

Cada archivo ``migraciones/NNNN_descripcion.sql`` se aplica una sola vez, en orden, dentro de una
transacción y como ``vs_propietario`` (``SET LOCAL ROLE``). La tabla ``meta.migracion`` registra la
versión, el nombre, el momento y el SHA3-256 del archivo: si una migración ya aplicada se modifica
después, ``migrar`` se niega a continuar (el esquema no coincidiría con el código revisado).

Quién migra: un superusuario o un miembro de ``vs_admin_bd`` (que puede asumir ``vs_propietario``
sin heredar sus privilegios). Requiere ``GRANT CREATE ON DATABASE … TO vs_propietario``.
"""

import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import psycopg

from votoseguro.cripto.hashing import sha3

_PATRON = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


class ErrorMigracion(Exception):
    pass


@dataclass(frozen=True)
class Migracion:
    version: int
    nombre: str
    sql: str

    @property
    def hash(self) -> str:
        return sha3(self.sql.encode("utf-8"))


def disponibles(carpeta: Path | None = None) -> list[Migracion]:
    if carpeta is None:
        archivos = [(f.name, f.read_text(encoding="utf-8"))
                    for f in resources.files("votoseguro.datos").joinpath("migraciones").iterdir()]
    else:
        archivos = [(f.name, f.read_text(encoding="utf-8")) for f in Path(carpeta).iterdir()]
    migraciones = []
    for nombre, sql in archivos:
        m = _PATRON.match(nombre)
        if m:
            migraciones.append(Migracion(int(m.group(1)), m.group(2), sql))
    migraciones.sort(key=lambda m: m.version)
    versiones = [m.version for m in migraciones]
    if versiones != list(range(1, len(versiones) + 1)):
        raise ErrorMigracion(f"las migraciones deben numerarse 0001, 0002… sin huecos ni repetidas: {versiones}")
    return migraciones


def _preparar(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute("SET LOCAL ROLE vs_propietario")
        conn.execute("CREATE SCHEMA IF NOT EXISTS meta AUTHORIZATION vs_propietario")
        conn.execute("""CREATE TABLE IF NOT EXISTS meta.migracion (
            version    integer PRIMARY KEY,
            nombre     text NOT NULL,
            hash       text NOT NULL,
            aplicada   timestamptz NOT NULL DEFAULT now(),
            linea_base boolean NOT NULL DEFAULT false)""")
        conn.execute("GRANT USAGE ON SCHEMA meta TO vs_auditor, vs_app, vs_admin_bd")
        conn.execute("GRANT SELECT ON meta.migracion TO vs_auditor, vs_app, vs_admin_bd")


def aplicadas(conn: psycopg.Connection) -> dict[int, tuple[str, str]]:
    existe = conn.execute("SELECT to_regclass('meta.migracion') IS NOT NULL").fetchone()[0]
    if not existe:
        return {}
    return {v: (n, h) for v, n, h in conn.execute("SELECT version, nombre, hash FROM meta.migracion").fetchall()}


def _linea_base(conn: psycopg.Connection, inicial: Migracion) -> bool:
    """BD instalada antes de existir las migraciones: si ya tiene el esquema inicial completo,
    se registra la 0001 como aplicada sin volver a ejecutarla."""
    if conn.execute("SELECT to_regnamespace('eleccion') IS NULL").fetchone()[0]:
        return False
    completo = conn.execute("""SELECT EXISTS (SELECT FROM information_schema.columns
        WHERE table_schema = 'eleccion' AND table_name = 'eleccion' AND column_name = 'definicion')""").fetchone()[0]
    if not completo:
        raise ErrorMigracion("la base de datos tiene un esquema anterior al Sprint 3: recréela con "
                             "scripts/instalar_bd_desarrollo.sh --recrear")
    with conn.transaction():
        conn.execute("SET LOCAL ROLE vs_propietario")
        conn.execute("INSERT INTO meta.migracion (version, nombre, hash, linea_base) VALUES (%s, %s, %s, true)",
                     (inicial.version, inicial.nombre, inicial.hash))
    return True


def migrar(conn: psycopg.Connection, carpeta: Path | None = None) -> list[str]:
    """Aplica las migraciones pendientes. Devuelve los nombres aplicados (vacío si está al día).

    Requiere una conexión en modo autocommit (cada migración es su propia transacción).
    """
    if not conn.autocommit:
        raise ErrorMigracion("migrar requiere una conexión con autocommit=True")
    migraciones = disponibles(carpeta)
    conn.execute("SELECT pg_advisory_lock(hashtext('votoseguro.migraciones'))")
    try:
        _preparar(conn)
        hechas = aplicadas(conn)
        resultado = []
        if not hechas and migraciones and _linea_base(conn, migraciones[0]):
            hechas = aplicadas(conn)
            resultado.append(f"{migraciones[0].version:04d}_{migraciones[0].nombre} (línea base)")
        for m in migraciones:
            if m.version in hechas:
                if hechas[m.version][1] != m.hash:
                    raise ErrorMigracion(f"la migración {m.version:04d} ya aplicada fue modificada después")
                continue
            with conn.transaction():
                conn.execute("SET LOCAL ROLE vs_propietario")
                conn.execute(m.sql)
                conn.execute("INSERT INTO meta.migracion (version, nombre, hash) VALUES (%s, %s, %s)",
                             (m.version, m.nombre, m.hash))
            resultado.append(f"{m.version:04d}_{m.nombre}")
        return resultado
    finally:
        conn.execute("SELECT pg_advisory_unlock(hashtext('votoseguro.migraciones'))")


def estado(conn: psycopg.Connection, carpeta: Path | None = None) -> list[tuple[int, str, str]]:
    """(versión, nombre, estado) de cada migración: APLICADA, LÍNEA BASE, PENDIENTE o MODIFICADA."""
    hechas = aplicadas(conn)
    base = set()
    if hechas:
        base = {v for (v,) in conn.execute("SELECT version FROM meta.migracion WHERE linea_base").fetchall()}
    filas = []
    for m in disponibles(carpeta):
        if m.version not in hechas:
            filas.append((m.version, m.nombre, "PENDIENTE"))
        elif hechas[m.version][1] != m.hash:
            filas.append((m.version, m.nombre, "MODIFICADA"))
        else:
            filas.append((m.version, m.nombre, "LÍNEA BASE" if m.version in base else "APLICADA"))
    return filas
