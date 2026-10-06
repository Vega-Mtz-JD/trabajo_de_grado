"""Conexión a PostgreSQL e instalación del esquema.

En producción la instancia escucha solo en un socket Unix (``listen_addresses = ''``) y la
aplicación se autentica con ``peer`` como ``vs_app``. El DSN se toma de ``VOTOSEGURO_DSN``.
"""

import os
from importlib import resources

import psycopg

DSN_POR_DEFECTO = "dbname=votoseguro user=vs_app"


class ErrorVotoSeguro(Exception):
    """Error de negocio señalado por la base de datos (SQLSTATE VSxxx)."""


class VotanteNoHabilitado(ErrorVotoSeguro):
    """VS001: el votante no existe, no está habilitado o ya votó."""


class EleccionNoAbierta(ErrorVotoSeguro):
    """VS002: la operación requiere que la elección esté ABIERTA."""


class TransicionInvalida(ErrorVotoSeguro):
    """VS003: cambio de estado no permitido o padrón cerrado."""


class OperacionProhibida(ErrorVotoSeguro):
    """VS100: intento de modificar o borrar datos de solo inserción."""


class IntegridadVulnerada(ErrorVotoSeguro):
    """VS101/VS102: la mezcla alteró la urna o la bitácora no está encadenada."""


_ERRORES = {
    "VS001": VotanteNoHabilitado,
    "VS002": EleccionNoAbierta,
    "VS003": TransicionInvalida,
    "VS100": OperacionProhibida,
    "VS101": IntegridadVulnerada,
    "VS102": IntegridadVulnerada,
}


def traducir_error(error: psycopg.Error) -> Exception:
    """Convierte un error de PostgreSQL con SQLSTATE propio en la excepción de negocio."""
    clase = _ERRORES.get(error.sqlstate or "")
    if clase is None:
        return error
    mensaje = error.diag.message_primary or str(error)
    return clase(mensaje)


def conectar(dsn: str | None = None, **kwargs) -> psycopg.Connection:
    return psycopg.connect(dsn or os.environ.get("VOTOSEGURO_DSN", DSN_POR_DEFECTO), **kwargs)


def _sql(nombre: str) -> str:
    return resources.files("votoseguro.datos").joinpath(nombre).read_text(encoding="utf-8")


def crear_roles(conn: psycopg.Connection) -> None:
    """Crea los roles de la instancia (idempotente). Requiere superusuario."""
    conn.execute(_sql("roles.sql"))


def instalar_esquema(conn: psycopg.Connection) -> None:
    """Crea esquemas, tablas, triggers, funciones y privilegios en una BD vacía."""
    conn.execute(_sql("esquema.sql"))
