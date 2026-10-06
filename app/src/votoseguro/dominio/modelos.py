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
class Definicion:
    """Definición de una elección, común a todas sus mesas (ADR-009). No contiene datos personales.

    ``sal_padron`` es secreta (no va al ledger): permite comparar CI entre mesas mediante hashes.
    """

    eleccion_global: str
    nombre: str
    opciones: tuple[Opcion, ...]
    mesas: tuple[str, ...]
    umbral: int
    partes: int
    checkpoint_cada: int
    sal_padron: str

    def a_dict(self) -> dict:
        return {
            "eleccion_global": self.eleccion_global, "nombre": self.nombre,
            "opciones": [[o.codigo, o.nombre, o.tipo.value, o.orden, o.frente] for o in self.opciones],
            "mesas": list(self.mesas), "umbral": self.umbral, "partes": self.partes,
            "checkpoint_cada": self.checkpoint_cada, "sal_padron": self.sal_padron,
        }

    @classmethod
    def desde_dict(cls, d: dict) -> "Definicion":
        return cls(d["eleccion_global"], d["nombre"],
                   tuple(Opcion(c, n, TipoOpcion(t), o, f) for c, n, t, o, f in d["opciones"]),
                   tuple(d["mesas"]), d["umbral"], d["partes"], d["checkpoint_cada"], d["sal_padron"])


@dataclass(frozen=True)
class Eleccion:
    """Una mesa de una elección, tal como está instalada en este equipo."""

    id: str
    nombre: str
    estado: Estado
    clave_publica_pem: bytes
    umbral: int
    partes: int
    checkpoint_cada: int
    eleccion_global: str = ""
    mesa: str = "01"
    sal_padron: str = ""
    hash_configuracion: str = ""

    @property
    def ancla(self) -> dict:
        """Identificación de la mesa en el ledger (sin datos personales)."""
        return {"eleccion_global": self.eleccion_global, "mesa": self.mesa}


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
