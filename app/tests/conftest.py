"""Fixtures de pruebas.

Las pruebas de base de datos levantan una instancia **temporal** de PostgreSQL (initdb en un
directorio temporal, solo socket Unix, con pgaudit cargado), igual a la configuración de
producción de ADR-008. No usan ni modifican la instancia del sistema.
"""

import glob
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import psycopg
import pytest

from votoseguro.datos.conexion import crear_roles, instalar_esquema


def _bin_postgres() -> Path | None:
    if os.environ.get("VOTOSEGURO_PG_BIN"):
        return Path(os.environ["VOTOSEGURO_PG_BIN"])
    candidatos = sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True)
    for c in candidatos:
        if Path(c, "initdb").exists():
            return Path(c)
    return Path(shutil.which("initdb")).parent if shutil.which("initdb") else None


@pytest.fixture(scope="session")
def instancia_pg(tmp_path_factory):
    binarios = _bin_postgres()
    if binarios is None:
        pytest.skip("PostgreSQL no está instalado (sudo apt install postgresql)")
    base = tmp_path_factory.mktemp("pg")
    datos, socket, log = base / "datos", base / "sock", base / "pg.log"
    socket.mkdir()
    subprocess.run(
        [binarios / "initdb", "-D", datos, "-U", "postgres", "--auth=trust",
         "--encoding=UTF8", "--locale=C.UTF-8"],
        check=True, capture_output=True,
    )
    opciones = " ".join([
        f"-k {socket}", "-c listen_addresses=''",
        "-c shared_preload_libraries=pgaudit", "-c pgaudit.log=ddl,role,write",
        "-c pgaudit.log_parameter=off",
        "-c wal_level=minimal", "-c max_wal_senders=0", "-c archive_mode=off",
        "-c fsync=off",  # solo en pruebas, para velocidad
    ])
    subprocess.run(
        [binarios / "pg_ctl", "-D", datos, "-o", opciones, "-l", log, "-w", "start"],
        check=True, capture_output=True,
    )
    with psycopg.connect(host=str(socket), dbname="postgres", user="postgres", autocommit=True) as c:
        crear_roles(c)
    yield {"host": str(socket), "log": log}
    subprocess.run([binarios / "pg_ctl", "-D", datos, "-m", "immediate", "stop"], capture_output=True)


@pytest.fixture
def bd(instancia_pg):
    """Base de datos nueva con el esquema instalado. Devuelve una función para conectarse
    con distintos roles: ``bd("postgres")``, ``bd("vs_app")``, ``bd("vs_auditor")``."""
    nombre = f"t_{uuid.uuid4().hex[:12]}"
    host = instancia_pg["host"]
    with psycopg.connect(host=host, dbname="postgres", user="postgres", autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{nombre}"')
    with psycopg.connect(host=host, dbname=nombre, user="postgres", autocommit=True) as c:
        c.execute("CREATE EXTENSION pgaudit")
        instalar_esquema(c)

    conexiones = []

    def conectar(usuario: str = "vs_app", autocommit: bool = False) -> psycopg.Connection:
        conn = psycopg.connect(host=host, dbname=nombre, user=usuario, autocommit=autocommit)
        conexiones.append(conn)
        return conn

    conectar.dsn = f"host={host} dbname={nombre}"
    yield conectar
    for conn in conexiones:
        conn.close()
    with psycopg.connect(host=host, dbname="postgres", user="postgres", autocommit=True) as c:
        c.execute(f'DROP DATABASE "{nombre}" WITH (FORCE)')
