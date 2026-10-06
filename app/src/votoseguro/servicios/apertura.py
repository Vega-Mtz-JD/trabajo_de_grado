"""Fase 4 — Apertura: autodiagnóstico, zerésima firmada y paso a ABIERTA."""

from datetime import UTC, datetime

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import sha3
from votoseguro.cripto.merkle import raiz_merkle
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado
from votoseguro.servicios import actas
from votoseguro.servicios.base import (
    anclar, VERSION_SOFTWARE, Contexto, DiscrepanciaDetectada, HardwareNoDisponible, exigir_estado,
)


def compromiso_padron(cis: list[str], sal: str) -> str:
    """Raíz de Merkle de los CI con sal: compromete el padrón sin publicar datos personales.

    La sal (de la definición de la elección) evita que alguien con acceso solo al ledger pruebe
    CI por fuerza bruta (el espacio de CI es pequeño). No se publica en el ledger.
    """
    return raiz_merkle([sha3(f"{sal}:{ci}".encode()) for ci in cis])


def abrir(ctx: Contexto, eleccion_id: str) -> actas.ActaFirmada:
    eleccion = exigir_estado(ctx, eleccion_id, Estado.LISTA)
    fallas = [n for n, ok in (("lector de huella", ctx.lector.disponible()),
                              ("impresora", ctx.impresora.disponible()),
                              ("cámara", ctx.camara is not None and ctx.camara.disponible())) if not ok]
    if fallas:
        raise HardwareNoDisponible("no disponible: " + ", ".join(fallas))
    if repo.contar_votos(ctx.conn, eleccion_id) != 0 or repo.conteos_padron(ctx.conn, eleccion_id)["votaron"]:
        raise DiscrepanciaDetectada("la urna no está vacía: no se puede abrir")

    padron = repo.conteos_padron(ctx.conn, eleccion_id)
    habilitados = [v["ci"] for v in repo.padron_completo(ctx.conn, eleccion_id) if v["habilitado"]]
    contenido = {
        "eleccion_id": eleccion_id,
        "eleccion_global": eleccion.eleccion_global,
        "eleccion": eleccion.nombre,
        "mesa": eleccion.mesa,
        "votos_por_opcion": {o.codigo: 0 for o in repo.opciones(ctx.conn, eleccion_id)},
        "votos_en_urna": 0,
        "padron": {"total": padron["total"], "habilitados": padron["habilitados"],
                   "compromiso": compromiso_padron(habilitados, eleccion.sal_padron)},
        "hash_configuracion": eleccion.hash_configuracion,
        "huella_clave_eleccion": firmas.huella(cv.publica_desde_pem(eleccion.clave_publica_pem)),
        "huella_dispositivo": ctx.llavero.huella_dispositivo,
        "software": VERSION_SOFTWARE,
        "momento": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    with ctx.conn.transaction():
        acta = actas.emitir(ctx, eleccion_id, "ZERESIMA", contenido)
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.ABIERTA)
        bitacora.registrar(ctx.conn, ctx.actor, "APERTURA", {"eleccion": eleccion_id, "hash_zeresima": acta.hash})
        outbox.encolar(ctx.conn, "RegistrarApertura", {
            **eleccion.ancla, "hash_zeresima": acta.hash,
            "compromiso_padron": contenido["padron"]["compromiso"], "habilitados": padron["habilitados"],
        })
    anclar(ctx)
    actas.imprimir(ctx, eleccion_id, acta)
    return acta
