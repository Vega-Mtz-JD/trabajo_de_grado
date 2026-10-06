"""Fase 1 — Configuración: crea la elección, sus opciones y las claves con custodia 3 de 5."""

from dataclasses import dataclass

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import hash_canonico
from votoseguro.cripto.shamir import Parte
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Opcion, TipoOpcion
from votoseguro.hardware.impresora import Documento
from votoseguro.servicios.base import Contexto


@dataclass(frozen=True)
class Candidatura:
    codigo: str
    nombre: str
    frente: str | None = None


@dataclass(frozen=True)
class EleccionCreada:
    eleccion_id: str
    partes: list[Parte]
    hash_configuracion: str


def crear_eleccion(ctx: Contexto, nombre: str, candidaturas: list[Candidatura], *,
                   umbral: int = 3, partes: int = 5, checkpoint_cada: int = 10,
                   custodios: list[str] | None = None,
                   bits: int = cv.BITS_CLAVE_ELECCION) -> EleccionCreada:
    """Crea la elección con las candidaturas más VOTO BLANCO y VOTO NULO.

    Imprime una hoja por custodio con su parte de la clave (texto + QR). La clave que
    reconstruyen las partes no se guarda en ningún lugar.
    """
    if not candidaturas:
        raise ValueError("se requiere al menos una candidatura")
    custodios = custodios or [f"Custodio {i}" for i in range(1, partes + 1)]
    if len(custodios) != partes:
        raise ValueError("debe haber un nombre por cada custodio")

    opciones = [Opcion(c.codigo, c.nombre, TipoOpcion.CANDIDATO, i, c.frente)
                for i, c in enumerate(candidaturas, 1)]
    opciones += [Opcion("BLANCO", "VOTO BLANCO", TipoOpcion.BLANCO, len(opciones) + 1),
                 Opcion("NULO", "VOTO NULO", TipoOpcion.NULO, len(opciones) + 2)]

    privada = cv.generar_clave_eleccion(bits)
    publica_pem = cv.publica_a_pem(privada.public_key())
    privada_cifrada, partes_shamir = cv.custodiar_clave(privada, umbral, partes)
    del privada  # a partir de aquí solo existe cifrada y repartida
    huella_clave = firmas.huella(cv.publica_desde_pem(publica_pem))
    configuracion = {
        "nombre": nombre,
        "opciones": [[o.codigo, o.nombre, o.tipo.value, o.orden] for o in opciones],
        "umbral": umbral, "partes": partes, "checkpoint_cada": checkpoint_cada,
        "huella_clave_eleccion": huella_clave,
    }
    hash_config = hash_canonico(configuracion)

    with ctx.conn.transaction():
        eid = repo.crear_eleccion(ctx.conn, nombre, publica_pem, privada_cifrada,
                                  umbral, partes, checkpoint_cada)
        for o in opciones:
            repo.insertar_opcion(ctx.conn, eid, o)
        bitacora.registrar(ctx.conn, ctx.actor, "ELECCION_CREADA", {
            "eleccion": eid, "hash_configuracion": hash_config, "huella_clave_eleccion": huella_clave,
            "umbral": umbral, "partes": partes,
        })
        outbox.encolar(ctx.conn, "RegistrarEleccion", {
            "eleccion_id": eid, "hash_configuracion": hash_config,
            "huella_clave_eleccion": huella_clave, "huella_dispositivo": ctx.llavero.huella_dispositivo,
        })

    for parte, custodio in zip(partes_shamir, custodios):
        ctx.impresora.imprimir_documento(Documento(
            f"PARTE DE CLAVE — {custodio.upper()}",
            [f"Elección: {nombre}", f"Identificador: {eid}",
             f"Parte {parte.x} de {partes} (se requieren {umbral} para el escrutinio)", "",
             parte.a_texto(), "",
             "Guarde esta hoja en un sobre sellado y firmado.",
             "Sin el número mínimo de partes los votos NO pueden contarse."],
            parte.a_texto(), f"parte_custodio_{parte.x}"))
    return EleccionCreada(eid, partes_shamir, hash_config)
