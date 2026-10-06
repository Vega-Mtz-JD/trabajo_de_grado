"""Entidades y reglas del dominio electoral."""

from dataclasses import dataclass
from enum import StrEnum


class Estado(StrEnum):
    """Máquina de estados de la elección (propuesta §10.2). La BD aplica las mismas reglas."""

    CONFIGURACION = "CONFIGURACION"
    EMPADRONAMIENTO = "EMPADRONAMIENTO"
    LISTA = "LISTA"
    ABIERTA = "ABIERTA"
    CERRADA = "CERRADA"
    ESCRUTADA = "ESCRUTADA"
    EXPORTADA = "EXPORTADA"


SIGUIENTE = {
    Estado.CONFIGURACION: Estado.EMPADRONAMIENTO,
    Estado.EMPADRONAMIENTO: Estado.LISTA,
    Estado.LISTA: Estado.ABIERTA,
    Estado.ABIERTA: Estado.CERRADA,
    Estado.CERRADA: Estado.ESCRUTADA,
    Estado.ESCRUTADA: Estado.EXPORTADA,
}


class TipoOpcion(StrEnum):
    CANDIDATO = "CANDIDATO"
    BLANCO = "BLANCO"
    NULO = "NULO"


class Rol(StrEnum):
    ADMIN = "ADMIN"
    OPERADOR = "OPERADOR"
    AUDITOR = "AUDITOR"


@dataclass(frozen=True)
class Opcion:
    codigo: str
    nombre: str
    tipo: TipoOpcion
    orden: int
    frente: str | None = None


@dataclass(frozen=True)
class Eleccion:
    id: str
    nombre: str
    estado: Estado
    clave_publica_pem: bytes
    umbral: int
    partes: int
    checkpoint_cada: int


@dataclass(frozen=True)
class Comprobante:
    """Contenido del VVPAT: sin hora ni datos del votante (ADR-004)."""

    eleccion: str
    mesa: str
    opcion: Opcion
    codigo: str          # 8 hex del hash del voto cifrado, formato XXXX-XXXX
    reimpresion: bool = False


def codigo_vvpat(hash_voto: str) -> str:
    """Código impreso en el VVPAT: primeros 8 hex del hash del voto, en mayúsculas."""
    return f"{hash_voto[:4]}-{hash_voto[4:8]}".upper()
