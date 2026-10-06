"""Fase 9 — Escrutinio: los custodios reconstruyen la clave, se descifran y cuentan los votos."""

from collections import Counter
from datetime import UTC, datetime

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto.merkle import raiz_merkle
from votoseguro.cripto.shamir import Parte
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado, codigo_vvpat
from votoseguro.servicios import actas
from votoseguro.servicios.base import anclar, Contexto, DiscrepanciaDetectada, ErrorServicio, exigir_estado


class PartesInsuficientes(ErrorServicio):
    pass


def escrutar(ctx: Contexto, eleccion_id: str, partes: list[Parte | str]) -> actas.ActaFirmada:
    """Cuenta los votos. La clave privada existe solo en memoria durante esta función."""
    eleccion = exigir_estado(ctx, eleccion_id, Estado.CERRADA)
    partes = [p if isinstance(p, Parte) else Parte.desde_texto(p) for p in partes]
    custodios = sorted(p.x for p in partes)
    try:
        privada = cv.recuperar_clave(repo.clave_privada_cifrada(ctx.conn, eleccion_id), partes)
    except cv.ErrorDescifrado as e:
        bitacora.registrar(ctx.conn, ctx.actor, "ESCRUTINIO_FALLIDO",
                           {"eleccion": eleccion_id, "custodios": custodios})
        raise PartesInsuficientes(
            f"no se pudo reconstruir la clave: se requieren {eleccion.umbral} partes válidas") from e
    if cv.publica_a_pem(privada.public_key()) != eleccion.clave_publica_pem:
        raise DiscrepanciaDetectada("la clave reconstruida no corresponde a la elección")

    acta_cierre = repo.actas(ctx.conn, eleccion_id)["CIERRE"]
    votos = repo.votos(ctx.conn, eleccion_id)
    raiz = raiz_merkle([h for _, h in votos])
    if raiz != acta_cierre["contenido"]["raiz_merkle"]:
        raise DiscrepanciaDetectada("la urna no coincide con la raíz de Merkle del acta de cierre")

    codigos_validos = {o.codigo for o in repo.opciones(ctx.conn, eleccion_id)}
    boletas = []
    for cifrado, hash_voto in votos:
        codigo = cv.descifrar_voto(privada, eleccion_id, cifrado).decode()
        if codigo not in codigos_validos:
            raise DiscrepanciaDetectada("se encontró un voto con una opción inexistente")
        boletas.append([codigo_vvpat(hash_voto), codigo])
    del privada

    conteo = Counter(c for _, c in boletas)
    contenido = {
        "eleccion_id": eleccion_id,
        "eleccion_global": eleccion.eleccion_global,
        "eleccion": eleccion.nombre,
        "mesa": eleccion.mesa,
        "resultados": {o.codigo: conteo.get(o.codigo, 0) for o in repo.opciones(ctx.conn, eleccion_id)},
        "total": len(boletas),
        "raiz_merkle": raiz,
        "hash_acta_cierre": acta_cierre["hash"],
        "custodios_presentes": custodios,
        "boletas": sorted(boletas),   # código VVPAT → opción, para cotejar con el papel
        "momento": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    with ctx.conn.transaction():
        acta = actas.emitir(ctx, eleccion_id, "ESCRUTINIO", contenido)
        repo.cambiar_estado(ctx.conn, eleccion_id, Estado.ESCRUTADA)
        bitacora.registrar(ctx.conn, ctx.actor, "ESCRUTINIO",
                           {"eleccion": eleccion_id, "hash_acta": acta.hash, "custodios": custodios})
        outbox.encolar(ctx.conn, "RegistrarEscrutinio", {
            **eleccion.ancla, "resultados": contenido["resultados"],
            "total": len(boletas), "hash_acta": acta.hash,
        })
    anclar(ctx)
    actas.imprimir(ctx, eleccion_id, acta)
    return acta
