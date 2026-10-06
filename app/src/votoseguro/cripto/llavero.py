"""Llavero del equipo y cifrado con frase de paso (Argon2id + AES-256-GCM).

El llavero guarda los secretos propios del equipo de votación:
  * la clave de firma del dispositivo (RSA-2048), con la que se firman zerésima, actas y
    el manifiesto del USB;
  * la clave AES-256 que cifra las plantillas biométricas del padrón.

Se almacena cifrado con una frase de paso que custodia el operador/administrador. La clave se
deriva con Argon2id (resistente a ataques con GPU). Si el equipo tiene TPM 2.0, en el
Sprint 5 se puede sellar el llavero al TPM.
"""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from votoseguro.cripto import firmas

_KDF = {"time_cost": 3, "memory_cost": 64 * 1024, "parallelism": 2, "hash_len": 32}


class FraseIncorrecta(Exception):
    """La frase de paso no corresponde o los datos fueron alterados."""


def _derivar(frase: str, sal: bytes) -> bytes:
    return hash_secret_raw(frase.encode("utf-8"), sal, type=Type.ID, **_KDF)


def cifrar_con_frase(datos: bytes, frase: str, contexto: bytes) -> bytes:
    """Formato: 'VSF1' ‖ sal (16) ‖ nonce (12) ‖ AES-256-GCM(datos, aad=contexto)."""
    if len(frase) < 12:
        raise ValueError("la frase de paso debe tener al menos 12 caracteres")
    sal, nonce = os.urandom(16), os.urandom(12)
    return b"VSF1" + sal + nonce + AESGCM(_derivar(frase, sal)).encrypt(nonce, datos, contexto)


def descifrar_con_frase(blob: bytes, frase: str, contexto: bytes) -> bytes:
    if blob[:4] != b"VSF1":
        raise FraseIncorrecta("formato desconocido")
    sal, nonce, cifrado = blob[4:20], blob[20:32], blob[32:]
    try:
        return AESGCM(_derivar(frase, sal)).decrypt(nonce, cifrado, contexto)
    except InvalidTag as e:
        raise FraseIncorrecta("frase incorrecta o archivo alterado") from e


@dataclass
class Llavero:
    clave_firma: rsa.RSAPrivateKey
    clave_plantillas: bytes

    @classmethod
    def nuevo(cls) -> "Llavero":
        return cls(firmas.generar_clave_firma(), AESGCM.generate_key(bit_length=256))

    @property
    def huella_dispositivo(self) -> str:
        return firmas.huella(self.clave_firma.public_key())

    def guardar(self, ruta: Path, frase: str) -> None:
        contenido = json.dumps({
            "clave_firma": self.clave_firma.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()).decode(),
            "clave_plantillas": self.clave_plantillas.hex(),
        }).encode()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(cifrar_con_frase(contenido, frase, b"votoseguro:llavero"))
        ruta.chmod(0o600)

    @classmethod
    def abrir(cls, ruta: Path, frase: str) -> "Llavero":
        datos = json.loads(descifrar_con_frase(ruta.read_bytes(), frase, b"votoseguro:llavero"))
        clave = serialization.load_pem_private_key(datos["clave_firma"].encode(), password=None)
        if not isinstance(clave, rsa.RSAPrivateKey):
            raise FraseIncorrecta("llavero inválido")
        return cls(clave, bytes.fromhex(datos["clave_plantillas"]))

    # --- Plantillas biométricas -----------------------------------------------------------

    def cifrar_plantilla(self, eleccion_id: str, ci: str, plantilla: bytes) -> bytes:
        nonce = os.urandom(12)
        aad = f"plantilla:{eleccion_id}:{ci}".encode()
        return nonce + AESGCM(self.clave_plantillas).encrypt(nonce, plantilla, aad)

    def descifrar_plantilla(self, eleccion_id: str, ci: str, blob: bytes) -> bytes:
        aad = f"plantilla:{eleccion_id}:{ci}".encode()
        try:
            return AESGCM(self.clave_plantillas).decrypt(blob[:12], blob[12:], aad)
        except InvalidTag as e:
            raise FraseIncorrecta("plantilla alterada o de otro votante") from e


def b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def desde_b64(texto: str) -> bytes:
    return base64.b64decode(texto.encode("ascii"), validate=True)
