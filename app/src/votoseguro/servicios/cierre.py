"""Fase 8 — Cierre de la votación: checkpoint final, cuadre y acta de cierre firmada."""

from datetime import UTC, datetime

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado
from votoseguro.hardware.impresora import Documento
from votoseguro.servicios import actas
from votoseguro.servicios.base import Contexto, DiscrepanciaDetectada, exigir_estado
from votoseguro.servicios.votacion import checkpoint


def cerrar(ctx: Contexto, eleccion_id: str) -> actas.ActaFirmada:
    eleccion = exigir_estado(ctx, eleccion_id, Estado.ABIERTA)
    total_votos = repo.contar_votos(ctx.conn, eleccion_id)
    previos = repo.checkpoints(ctx.conn, eleccion_id)
    if not previos or previos[-1]["conteo"] != total_votos:
        checkpoint(ctx, eleccion_id)
    ultimo = repo.checkpoints(ctx.conn, eleccion_id)[-1]

    padron = repo.conteos_padron(ctx.conn, eleccion_id)
    if padron["votaron"] != total_votos:
        bitacora.registrar(ctx.conn, ctx.actor, "DISCREPANCIA_CIERRE",
                           {"eleccion": eleccion_id, "votos": total_votos, "votaron": padron["votaron"]})
        raise DiscrepanciaDetectada(
            f"votos en urna ({total_votos}) ≠ votantes marcados ({padron['votaron']})")

    lista = repo.padron_completo(ctx.conn, eleccion_id)
    ausentes = [v for v in lista if v["habilitado"] and not v["ya_voto"]]
    presentes_sin_voto = [v["ci"] for v in lista if v["presente"] and not v["ya_voto"]]
    contenido = {
        "eleccion_id": eleccion_id,
        "eleccion_global": eleccion.eleccion_global,
        "eleccion": eleccion.nombre,
        "mesa": eleccion.mesa,
        "total_votos": total_votos,
        "votantes_que_votaron": padron["votaron"],
        "padron_habilitado": padron["habilitados"],
        "ausentes": len(ausentes),
        "presentes_sin_votar": len(presentes_sin_voto),
        "participacion_pct": f"{100 * total_votos / padron['habilitados']:.2f}",
        "habilitados_por_excepcion": repo.contar_eventos(ctx.conn, eleccion_id, "EXCEPCION_MANUAL"),
        "autenticaciones_fallidas": repo.contar_eventos(ctx.conn, eleccion_id, "AUTENTICACION_FALLIDA"),
        "checkpoints": ultimo["seq"],
        "raiz_merkle": ultimo["raiz_merkle"],
        "ultimo_hash_bitacora": repo.ultimo_hash_bitacora(ctx.conn),
        "momento": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    with ctx.conn.transaction():
        acta = actas.emitir(ctx, eleccion_id, "CIERRE", contenido)
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.CERRADA)
        bitacora.registrar(ctx.conn, ctx.actor, "CIERRE", {"eleccion": eleccion_id, "hash_acta": acta.hash})
        outbox.encolar(ctx.conn, "RegistrarCierre", {
            **eleccion.ancla, "total_votos": total_votos,
            "total_votantes": padron["votaron"], "raiz_merkle": ultimo["raiz_merkle"], "hash_acta": acta.hash,
        })
    actas.imprimir(ctx, eleccion_id, acta)
    ctx.impresora.imprimir_documento(Documento(
        f"LISTA DE VOTANTES QUE NO VOTARON — MESA {eleccion.mesa}",
        [f"Elección: {eleccion.nombre}", f"Habilitados: {padron['habilitados']} · votaron: {padron['votaron']}"
         f" · no votaron: {len(ausentes)}", ""]
        + [f"{v['ci']:>12}  {v['apellidos']}, {v['nombres']}" for v in ausentes]
        + ([""] + [f"Se identificaron pero NO votaron: {', '.join(presentes_sin_voto)}"] if presentes_sin_voto else []),
        None, f"ausentes_mesa{eleccion.mesa}"))
    ctx.impresora.vaciar_urna()
    return acta
