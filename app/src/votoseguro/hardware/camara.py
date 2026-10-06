"""Cámara de la mesa de identificación (foto de registro y foto de presencia, ADR-009).

En producción: cámara web USB (Sprint 6, vía Qt Multimedia u OpenCV). En desarrollo y
pruebas, ``CamaraSimulada`` genera una imagen PNG distinta por persona.

La cámara está en la **mesa de identificación**, nunca en la cabina de votación.
"""

import hashlib
import struct
import zlib
from abc import ABC, abstractmethod


class CamaraNoDisponible(Exception):
    pass


class Camara(ABC):
    @abstractmethod
    def disponible(self) -> bool: ...

    @abstractmethod
    def capturar(self) -> bytes:
        """Toma una foto y la devuelve codificada (PNG o JPEG)."""


def _png(ancho: int, alto: int, pixeles: bytes) -> bytes:
    """PNG RGB mínimo, sin dependencias externas."""
    def bloque(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))

    filas = b"".join(b"\x00" + pixeles[y * ancho * 3:(y + 1) * ancho * 3] for y in range(alto))
    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(filas)) + bloque(b"IEND", b""))


class CamaraSimulada(Camara):
    """Genera un "retrato" de 48×48 con colores derivados de la persona frente a la cámara."""

    def __init__(self, conectada: bool = True):
        self._persona = "nadie"
        self.conectada = conectada
        self._tomas = 0

    def colocar_persona(self, persona: str) -> None:
        self._persona = persona

    def disponible(self) -> bool:
        return self.conectada

    def capturar(self) -> bytes:
        if not self.conectada:
            raise CamaraNoDisponible("cámara desconectada")
        self._tomas += 1
        semilla = hashlib.sha3_256(f"rostro:{self._persona}".encode()).digest()
        fondo, piel = semilla[0:3], bytes(min(255, 150 + b % 100) for b in semilla[3:6])
        pixeles = bytearray()
        for y in range(48):
            for x in range(48):
                dentro = (x - 24) ** 2 / 15 ** 2 + (y - 22) ** 2 / 19 ** 2 <= 1
                pixeles += piel if dentro else fondo
        pixeles[0:3] = bytes([self._tomas % 256, 0, 0])  # cada toma es distinta (luz, momento)
        return _png(48, 48, bytes(pixeles))
