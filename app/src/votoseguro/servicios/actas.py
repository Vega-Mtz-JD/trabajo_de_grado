"""Emisión de actas firmadas (zerésima, cierre, escrutinio): hash, firma, BD e impresión."""

import json
from dataclasses import dataclass
from typing import Any

from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import canonico, hash_canonico
from votoseguro.datos import repositorio as repo
from votoseguro.hardware.impresora import Documento
from votoseguro.servicios.base import Contexto

TITULOS = {
    "ZERESIMA": "ZERÉSIMA — REPORTE DE URNA VACÍA",
    "CIERRE": "ACTA DE CIERRE DE VOTACIÓN",
    "ESCRUTINIO": "ACTA DE ESCRUTINIO",
}
# Campos voluminosos que se guardan en el acta digital pero no se imprimen.
_NO_IMPRIMIR = {"boletas"}


@dataclass(frozen=True)
class ActaFirmada:
    id: str
    tipo: str
    contenido: dict[str, Any]
    hash: str
    firma: bytes


def _lineas(contenido: dict[str, Any], sangria: int = 0) -> list[str]:
    lineas = []
    for clave, valor in contenido.items():
        if clave in _NO_IMPRIMIR:
            lineas.append(" " * sangria + f"{clave}: {len(valor)} registros (en el acta digital)")
        elif isinstance(valor, dict):
            lineas.append(" " * sangria + f"{clave}:")
            lineas += _lineas(valor, sangria + 2)
        else:
            texto = str(valor)
            if len(texto) > 64:  # hashes largos en dos líneas
                lineas += [" " * sangria + f"{clave}:", " " * (sangria + 2) + texto]
            else:
                lineas.append(" " * sangria + f"{clave}: {texto}")
    return lineas


def emitir(ctx: Contexto, eleccion_id: str, tipo: str, contenido: dict[str, Any]) -> ActaFirmada:
    """Firma el acta con la clave del dispositivo y la guarda (en la transacción en curso).

    No imprime: se llama a ``imprimir`` después del commit, para no producir papeles de
    actas que luego no existan en la base de datos.
    """
    hash_acta = hash_canonico(contenido)
    firma = firmas.firmar(ctx.llavero.clave_firma, canonico(contenido))
    acta_id = repo.insertar_acta(ctx.conn, eleccion_id, tipo, contenido, hash_acta, firma)
    return ActaFirmada(acta_id, tipo, contenido, hash_acta, firma)


def imprimir(ctx: Contexto, eleccion_id: str, acta: ActaFirmada) -> None:
    """Imprime el acta. Al pie van el hash y la huella del dispositivo, en texto y en QR: es el
    **anclaje externo** que firman a mano los delegados (ADR-001)."""
    pie = [
        "",
        f"HASH DEL ACTA (SHA3-256): {acta.hash}",
        f"HUELLA DEL DISPOSITIVO:   {ctx.llavero.huella_dispositivo}",
        "",
        "Firmas de delegados: ______________   ______________   ______________",
    ]
    qr = json.dumps({"t": acta.tipo, "e": eleccion_id, "h": acta.hash}, separators=(",", ":"))
    ctx.impresora.imprimir_documento(
        Documento(TITULOS[acta.tipo], _lineas(acta.contenido) + pie, qr, f"acta_{acta.tipo.lower()}")
    )
