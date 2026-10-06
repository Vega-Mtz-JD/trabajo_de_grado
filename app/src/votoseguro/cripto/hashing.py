"""Funciones hash (SHA3-256) y serialización canónica para hashear estructuras."""

import hashlib
import json
from typing import Any


def sha3(datos: bytes) -> str:
    """SHA3-256 en hexadecimal (64 caracteres)."""
    return hashlib.sha3_256(datos).hexdigest()


def canonico(obj: Any) -> bytes:
    """Serializa a JSON canónico: claves ordenadas, sin espacios, UTF-8.

    Dos estructuras con el mismo contenido producen siempre los mismos bytes, lo que
    permite hashearlas y firmarlas de forma reproducible (actas, bitácora, manifiestos).
    No se admiten flotantes, porque su representación no es estable entre lenguajes.
    """
    def _sin_flotantes(valor: Any) -> Any:
        if isinstance(valor, float):
            raise TypeError("canonico() no admite flotantes; use enteros o cadenas")
        if isinstance(valor, dict):
            return {k: _sin_flotantes(v) for k, v in valor.items()}
        if isinstance(valor, (list, tuple)):
            return [_sin_flotantes(v) for v in valor]
        return valor

    return json.dumps(
        _sin_flotantes(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def hash_canonico(obj: Any) -> str:
    """SHA3-256 de la serialización canónica de ``obj``."""
    return sha3(canonico(obj))
