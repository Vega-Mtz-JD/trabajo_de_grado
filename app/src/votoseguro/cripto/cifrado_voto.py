"""Cifrado híbrido de votos y custodia de la clave de la elección (ADR-003).

Esquema por voto:
    1. Se rellena el contenido a un tamaño fijo (``TAMANIO_CONTENIDO``), para que la longitud
       del texto cifrado no revele la opción elegida.
    2. Se cifra con AES-256-GCM usando una clave aleatoria de un solo uso. El identificador
       de la elección va como dato asociado (AAD), así un voto no puede trasladarse a otra
       elección sin que se detecte.
    3. La clave AES se envuelve con RSA-OAEP(SHA-256) usando la clave pública de la elección.

Formato del voto cifrado (todos los votos de una elección tienen la misma longitud):
    versión (1) ‖ clave AES envuelta (tamaño de la clave RSA) ‖ nonce (12) ‖ texto cifrado + etiqueta (TAMANIO_CONTENIDO + 16)

Custodia de la clave privada:
    La clave privada se serializa (PKCS#8 DER) y se cifra con AES-256-GCM usando una KEK
    aleatoria. La KEK se reparte con Shamir entre los custodios y se descarta. Sin
    ``umbral`` partes no hay forma de descifrar ningún voto.
"""

import os
import struct

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from votoseguro.cripto import shamir

VERSION = 1
TAMANIO_CONTENIDO = 64          # bytes de texto plano tras el relleno
BITS_CLAVE_ELECCION = 3072
_NONCE = 12

_OAEP = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


class ErrorDescifrado(Exception):
    """El voto o la clave fueron alterados, o la clave/partes son incorrectas."""


# --- Claves de la elección -------------------------------------------------------------

def generar_clave_eleccion(bits: int = BITS_CLAVE_ELECCION) -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def publica_a_pem(clave: rsa.RSAPublicKey) -> bytes:
    return clave.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def publica_desde_pem(pem: bytes) -> rsa.RSAPublicKey:
    clave = serialization.load_pem_public_key(pem)
    if not isinstance(clave, rsa.RSAPublicKey):
        raise ValueError("se esperaba una clave pública RSA")
    return clave


# --- Votos -------------------------------------------------------------------------------

def _rellenar(contenido: bytes) -> bytes:
    """Prefijo de longitud (2 bytes) + contenido + ceros hasta TAMANIO_CONTENIDO."""
    if len(contenido) > TAMANIO_CONTENIDO - 2:
        raise ValueError(f"el contenido del voto excede {TAMANIO_CONTENIDO - 2} bytes")
    return struct.pack(">H", len(contenido)) + contenido.ljust(TAMANIO_CONTENIDO - 2, b"\x00")


def _quitar_relleno(bloque: bytes) -> bytes:
    (largo,) = struct.unpack(">H", bloque[:2])
    if largo > TAMANIO_CONTENIDO - 2 or any(bloque[2 + largo:]):
        raise ErrorDescifrado("relleno inválido")
    return bloque[2:2 + largo]


def cifrar_voto(publica: rsa.RSAPublicKey, eleccion_id: str, contenido: bytes) -> bytes:
    """Cifra el contenido de un voto (p. ej. el código de la opción) para la elección dada."""
    clave_aes = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(_NONCE)
    cifrado = AESGCM(clave_aes).encrypt(nonce, _rellenar(contenido), eleccion_id.encode())
    envuelta = publica.encrypt(clave_aes, _OAEP)
    return bytes([VERSION]) + envuelta + nonce + cifrado


def descifrar_voto(privada: rsa.RSAPrivateKey, eleccion_id: str, voto: bytes) -> bytes:
    tam_rsa = privada.key_size // 8
    if len(voto) != 1 + tam_rsa + _NONCE + TAMANIO_CONTENIDO + 16 or voto[0] != VERSION:
        raise ErrorDescifrado("formato o longitud de voto inválidos")
    envuelta = voto[1:1 + tam_rsa]
    nonce = voto[1 + tam_rsa:1 + tam_rsa + _NONCE]
    cifrado = voto[1 + tam_rsa + _NONCE:]
    try:
        clave_aes = privada.decrypt(envuelta, _OAEP)
        bloque = AESGCM(clave_aes).decrypt(nonce, cifrado, eleccion_id.encode())
    except (ValueError, InvalidTag) as e:
        raise ErrorDescifrado("no se pudo descifrar el voto") from e
    return _quitar_relleno(bloque)


# --- Custodia con Shamir -----------------------------------------------------------------

def custodiar_clave(
    privada: rsa.RSAPrivateKey, umbral: int, partes: int
) -> tuple[bytes, list[shamir.Parte]]:
    """Cifra la clave privada con una KEK aleatoria y reparte la KEK con Shamir.

    Devuelve ``(clave_privada_cifrada, partes)``. La KEK no se conserva en ningún lugar.
    """
    kek = AESGCM.generate_key(bit_length=256)
    der = privada.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    nonce = os.urandom(_NONCE)
    cifrada = nonce + AESGCM(kek).encrypt(nonce, der, b"votoseguro:clave-eleccion")
    return cifrada, shamir.dividir(kek, umbral, partes)


def recuperar_clave(cifrada: bytes, partes: list[shamir.Parte]) -> rsa.RSAPrivateKey:
    """Reconstruye la KEK con las partes de los custodios y descifra la clave privada.

    Si las partes son insuficientes o incorrectas, AES-GCM lo detecta y se lanza
    ``ErrorDescifrado``.
    """
    kek = shamir.combinar(partes)
    nonce, resto = cifrada[:_NONCE], cifrada[_NONCE:]
    try:
        der = AESGCM(kek).decrypt(nonce, resto, b"votoseguro:clave-eleccion")
    except InvalidTag as e:
        raise ErrorDescifrado("partes insuficientes o incorrectas") from e
    clave = serialization.load_der_private_key(der, password=None)
    if not isinstance(clave, rsa.RSAPrivateKey):
        raise ErrorDescifrado("la clave recuperada no es RSA")
    return clave
