"""Firmas digitales RSA-PSS para zerésima, actas y manifiestos de exportación.

Cada firmante (el equipo, el operador, el auditor) tiene un par RSA-2048. La clave privada
se guarda cifrada con una frase de paso (PKCS#8 con cifrado del mejor algoritmo
disponible). La firma usa RSA-PSS con SHA-256.
"""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from votoseguro.cripto.hashing import sha3

BITS_CLAVE_FIRMA = 2048

_PSS = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)


def generar_clave_firma(bits: int = BITS_CLAVE_FIRMA) -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def firmar(privada: rsa.RSAPrivateKey, datos: bytes) -> bytes:
    return privada.sign(datos, _PSS, hashes.SHA256())


def verificar(publica: rsa.RSAPublicKey, datos: bytes, firma: bytes) -> bool:
    try:
        publica.verify(firma, datos, _PSS, hashes.SHA256())
        return True
    except InvalidSignature:
        return False


def privada_a_pem(privada: rsa.RSAPrivateKey, frase: bytes) -> bytes:
    """Serializa la clave privada cifrada con ``frase`` (nunca se guarda en claro)."""
    if len(frase) < 12:
        raise ValueError("la frase de paso debe tener al menos 12 caracteres")
    return privada.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(frase),
    )


def privada_desde_pem(pem: bytes, frase: bytes) -> rsa.RSAPrivateKey:
    clave = serialization.load_pem_private_key(pem, password=frase)
    if not isinstance(clave, rsa.RSAPrivateKey):
        raise ValueError("se esperaba una clave privada RSA")
    return clave


def huella(publica: rsa.RSAPublicKey) -> str:
    """Huella SHA3-256 de la clave pública (DER), para identificarla en actas y en el ledger."""
    return sha3(
        publica.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
