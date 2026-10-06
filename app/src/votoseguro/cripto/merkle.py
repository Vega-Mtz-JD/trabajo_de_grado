"""Árbol de Merkle sobre los hashes de los votos cifrados.

La raíz resume el conjunto completo de votos en 32 bytes: si se altera, agrega o elimina
cualquier voto, la raíz cambia. Se ancla en los checkpoints, en el acta y en Fabric.

Decisiones:
- Las hojas se **ordenan lexicográficamente** antes de construir el árbol. Así la raíz
  depende del *conjunto* de votos y no del orden de emisión (secreto del voto, ADR-004).
- Se usan prefijos de dominio distintos para hojas (0x00) y nodos internos (0x01), como en
  RFC 6962, para evitar ataques de segunda preimagen.
- Con un número impar de nodos en un nivel, el último sube sin emparejarse.
"""

import hashlib
from collections.abc import Iterable

_PREFIJO_HOJA = b"\x00"
_PREFIJO_NODO = b"\x01"


def _h(datos: bytes) -> bytes:
    return hashlib.sha3_256(datos).digest()


def raiz_merkle(hashes_hex: Iterable[str]) -> str:
    """Raíz de Merkle (hex) de una colección de hashes SHA3-256 hexadecimales.

    El conjunto vacío tiene como raíz SHA3-256 de la cadena vacía. Un hash repetido es un
    error: cada voto cifrado es único, así que un duplicado indica datos corruptos.
    """
    hojas = sorted(hashes_hex)
    if len(set(hojas)) != len(hojas):
        raise ValueError("hay hashes duplicados en el conjunto")
    if not hojas:
        return _h(b"").hex()
    nivel = [_h(_PREFIJO_HOJA + bytes.fromhex(h)) for h in hojas]
    while len(nivel) > 1:
        siguiente = [
            _h(_PREFIJO_NODO + nivel[i] + nivel[i + 1]) for i in range(0, len(nivel) - 1, 2)
        ]
        if len(nivel) % 2:
            siguiente.append(nivel[-1])
        nivel = siguiente
    return nivel[0].hex()
