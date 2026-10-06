"""Lector de huella dactilar.

La interfaz separa la lógica del sistema del dispositivo real. En producción se usa
``LectorZKTeco`` (Sprint 5, ZKFinger SDK para Linux); en desarrollo y pruebas, ``LectorSimulado``.

El sistema guarda la **plantilla** (no la imagen) cifrada y compara 1:1: la plantilla viva
contra la plantilla registrada del CI declarado. El resultado es un puntaje; se acepta si
supera ``umbral``.
"""

import hashlib
import os
import random
from abc import ABC, abstractmethod


class LectorNoDisponible(Exception):
    pass


class LectorHuella(ABC):
    umbral: int = 50

    @abstractmethod
    def disponible(self) -> bool: ...

    @abstractmethod
    def capturar(self) -> bytes:
        """Espera un dedo sobre el sensor y devuelve su plantilla."""

    @abstractmethod
    def comparar(self, registrada: bytes, viva: bytes) -> int:
        """Puntaje de similitud (0–100)."""

    def coincide(self, registrada: bytes, viva: bytes) -> bool:
        return self.comparar(registrada, viva) >= self.umbral


class LectorSimulado(LectorHuella):
    """Simula personas con huellas distintas.

    Antes de ``capturar`` se indica qué persona apoya el dedo con ``colocar_dedo(persona)``.
    Cada captura de la misma persona produce bytes distintos (ruido), como en un sensor real,
    pero el "núcleo" de la huella es estable, así que la comparación 1:1 funciona. Con
    ``tasa_rechazo`` se simulan lecturas fallidas (dedo húmedo, mal apoyado).
    """

    def __init__(self, tasa_rechazo: float = 0.0, conectado: bool = True,
                 azar: random.Random | None = None):
        self._persona: str | None = None
        self.tasa_rechazo = tasa_rechazo
        self.conectado = conectado
        # Generador para decidir lecturas fallidas: con semilla, la simulación es reproducible.
        self._azar = azar or random.Random()  # nosec B311 (simulación, no criptografía)

    def colocar_dedo(self, persona: str) -> None:
        self._persona = persona

    def disponible(self) -> bool:
        return self.conectado

    def capturar(self) -> bytes:
        if not self.conectado:
            raise LectorNoDisponible("lector de huella desconectado")
        if self._persona is None:
            raise LectorNoDisponible("no hay dedo sobre el sensor")
        nucleo = hashlib.sha3_256(f"huella:{self._persona}".encode()).digest()
        if self.tasa_rechazo and self._azar.random() < self.tasa_rechazo:
            nucleo = os.urandom(32)  # lectura de mala calidad
        return b"SIM1" + nucleo + os.urandom(16)

    def comparar(self, registrada: bytes, viva: bytes) -> int:
        return 100 if registrada[:36] == viva[:36] else 0
