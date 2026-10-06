"""Esquema de secreto compartido de Shamir (1979) sobre el cuerpo finito GF(2^8).

Se usa para repartir la clave que protege la clave privada de la elección entre los
custodios (ADR-003): con ``umbral`` partes se reconstruye el secreto; con menos, no se
obtiene ninguna información sobre él.

Cada byte del secreto se reparte de forma independiente: se elige un polinomio aleatorio
de grado ``umbral - 1`` cuyo término independiente es el byte secreto, y la parte del
custodio ``x`` es el valor del polinomio en ``x``. La reconstrucción usa interpolación de
Lagrange en ``x = 0``.

Aritmética de GF(2^8) con el polinomio irreducible de AES, x^8 + x^4 + x^3 + x + 1 (0x11B):
la suma es XOR y la multiplicación usa tablas de logaritmos con generador 3.
"""

import secrets
from dataclasses import dataclass

from votoseguro.cripto.hashing import sha3

_EXP = [0] * 512
_LOG = [0] * 256


def _iniciar_tablas() -> None:
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        # x * 3 = x * 2 XOR x, reduciendo por 0x11B cuando hay desborde
        doble = (x << 1) ^ (0x11B if x & 0x80 else 0)
        x = doble ^ x
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_iniciar_tablas()


def _mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("división por cero en GF(256)")
    if a == 0:
        return 0
    return _EXP[_LOG[a] - _LOG[b] + 255]


def _evaluar(coeficientes: list[int], x: int) -> int:
    """Evalúa el polinomio en ``x`` con el método de Horner."""
    resultado = 0
    for c in reversed(coeficientes):
        resultado = _mul(resultado, x) ^ c
    return resultado


@dataclass(frozen=True)
class Parte:
    """Parte de un custodio: abscisa ``x`` (1..255) y un byte ``y`` por cada byte del secreto."""

    x: int
    y: bytes

    def a_texto(self) -> str:
        """Representación imprimible (y para QR) con suma de verificación contra errores de tipeo.

        Formato: ``VS1-<x>-<y en hex>-<6 hex de verificación>``.
        """
        return f"VS1-{self.x:03d}-{self.y.hex()}-{_verificacion(self.x, self.y)}"

    @classmethod
    def desde_texto(cls, texto: str) -> "Parte":
        try:
            version, x, y_hex, chk = texto.strip().split("-")
            parte = cls(int(x), bytes.fromhex(y_hex))
        except ValueError as e:
            raise ValueError("formato de parte inválido") from e
        if version != "VS1" or not 1 <= parte.x <= 255:
            raise ValueError("formato de parte inválido")
        if chk != _verificacion(parte.x, parte.y):
            raise ValueError("la suma de verificación no coincide (¿error al transcribir?)")
        return parte


def _verificacion(x: int, y: bytes) -> str:
    return sha3(f"{x}:{y.hex()}".encode())[:6]


def dividir(secreto: bytes, umbral: int, partes: int) -> list[Parte]:
    """Divide ``secreto`` en ``partes`` partes, de las que bastan ``umbral`` para reconstruirlo."""
    if not secreto:
        raise ValueError("el secreto no puede estar vacío")
    if not 2 <= umbral <= partes <= 255:
        raise ValueError("se requiere 2 <= umbral <= partes <= 255")
    ys = [bytearray() for _ in range(partes)]
    for byte in secreto:
        coeficientes = [byte] + list(secrets.token_bytes(umbral - 1))
        for i in range(partes):
            ys[i].append(_evaluar(coeficientes, i + 1))
    return [Parte(i + 1, bytes(y)) for i, y in enumerate(ys)]


def combinar(partes: list[Parte]) -> bytes:
    """Reconstruye el secreto por interpolación de Lagrange en x = 0.

    Si se entregan menos partes que el umbral, el resultado es un valor aleatorio sin
    relación con el secreto (no hay forma de detectarlo aquí). Por eso el secreto
    reconstruido siempre se valida después, al descifrar con AES-GCM, que sí detecta una
    clave incorrecta.
    """
    if len(partes) < 2:
        raise ValueError("se requieren al menos 2 partes")
    xs = [p.x for p in partes]
    if len(set(xs)) != len(xs):
        raise ValueError("hay partes repetidas")
    largo = len(partes[0].y)
    if any(len(p.y) != largo for p in partes):
        raise ValueError("las partes tienen longitudes distintas")

    secreto = bytearray()
    for indice in range(largo):
        valor = 0
        for j, pj in enumerate(partes):
            # Coeficiente de Lagrange L_j(0) = prod_{m != j} x_m / (x_m - x_j); en GF(2^8) la resta es XOR
            numerador, denominador = 1, 1
            for m, pm in enumerate(partes):
                if m != j:
                    numerador = _mul(numerador, pm.x)
                    denominador = _mul(denominador, pm.x ^ pj.x)
            valor ^= _mul(pj.y[indice], _div(numerador, denominador))
        secreto.append(valor)
    return bytes(secreto)
