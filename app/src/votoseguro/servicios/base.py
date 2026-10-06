"""Contexto de ejecución y errores comunes de los servicios."""

from dataclasses import dataclass

import psycopg

from votoseguro.cripto.llavero import Llavero
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Eleccion, Estado
from votoseguro.hardware.camara import Camara
from votoseguro.hardware.huella import LectorHuella
from votoseguro.hardware.impresora import Impresora

VERSION_SOFTWARE = "votoseguro-0.3.0"


class ErrorServicio(Exception):
    """Error de negocio que el operador debe ver con un mensaje claro."""


class EstadoIncorrecto(ErrorServicio):
    pass


class HardwareNoDisponible(ErrorServicio):
    pass


class AutenticacionFallida(ErrorServicio):
    pass


class OpcionInvalida(ErrorServicio):
    pass


class DiscrepanciaDetectada(ErrorServicio):
    pass


@dataclass
class Contexto:
    """Dependencias de los servicios: conexión, secretos del equipo, periféricos y operador.

    La conexión debe estar en modo autocommit: cada servicio delimita sus transacciones con
    ``with conn.transaction()``, de modo que cada paso se confirma o se revierte completo.
    """

    conn: psycopg.Connection
    llavero: Llavero
    lector: LectorHuella
    impresora: Impresora
    actor: str
    camara: Camara | None = None

    def tomar_foto(self) -> bytes:
        from votoseguro.hardware.camara import CamaraNoDisponible

        if self.camara is None:
            raise HardwareNoDisponible("no hay cámara configurada")
        try:
            return self.camara.capturar()
        except CamaraNoDisponible as e:
            raise HardwareNoDisponible(str(e)) from e

    def __post_init__(self):
        if not self.conn.autocommit:
            raise ValueError("el contexto requiere una conexión con autocommit=True")


def exigir_estado(ctx: Contexto, eleccion_id: str, *permitidos: Estado) -> Eleccion:
    eleccion = repo.obtener_eleccion(ctx.conn, eleccion_id)
    if eleccion.estado not in permitidos:
        nombres = ", ".join(p.value for p in permitidos)
        raise EstadoIncorrecto(f"la elección está en {eleccion.estado.value}; se requiere {nombres}")
    return eleccion
