"""Fase 2 — Empadronamiento: registro de votantes con su plantilla de huella cifrada."""

from votoseguro.auditoria import bitacora
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado
from votoseguro.hardware.huella import LectorNoDisponible
from votoseguro.servicios.base import Contexto, HardwareNoDisponible, exigir_estado


def iniciar(ctx: Contexto, eleccion_id: str) -> None:
    exigir_estado(ctx, eleccion_id, Estado.CONFIGURACION)
    with ctx.conn.transaction():
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.EMPADRONAMIENTO)
        bitacora.registrar(ctx.conn, ctx.actor, "EMPADRONAMIENTO_INICIADO", {"eleccion": eleccion_id})


def registrar_votante(ctx: Contexto, eleccion_id: str, ci: str, nombres: str, apellidos: str) -> None:
    """Captura la huella del votante (que debe estar sobre el lector) y lo agrega al padrón."""
    exigir_estado(ctx, eleccion_id, Estado.EMPADRONAMIENTO)
    try:
        plantilla = ctx.lector.capturar()
    except LectorNoDisponible as e:
        raise HardwareNoDisponible(str(e)) from e
    cifrada = ctx.llavero.cifrar_plantilla(eleccion_id, ci, plantilla)
    with ctx.conn.transaction():
        repo.insertar_votante(ctx.conn, eleccion_id, ci, nombres.strip(), apellidos.strip(), cifrada)
        bitacora.registrar(ctx.conn, ctx.actor, "VOTANTE_REGISTRADO", {"eleccion": eleccion_id, "ci": ci})


def cerrar_padron(ctx: Contexto, eleccion_id: str) -> dict[str, int]:
    exigir_estado(ctx, eleccion_id, Estado.EMPADRONAMIENTO)
    conteos = repo.conteos_padron(ctx.conn, eleccion_id)
    if conteos["habilitados"] == 0:
        raise ValueError("el padrón no tiene votantes habilitados")
    with ctx.conn.transaction():
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.LISTA)
        bitacora.registrar(ctx.conn, ctx.actor, "PADRON_CERRADO", {"eleccion": eleccion_id, **conteos})
    return conteos
