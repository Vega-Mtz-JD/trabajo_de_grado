"""Usuarios del sistema (administrador, operador, auditor) con contraseñas Argon2id."""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from votoseguro.dominio.modelos import Rol

_hasher = PasswordHasher()  # Argon2id con parámetros recomendados por la librería


class CredencialesInvalidas(Exception):
    pass


def crear_usuario(conn, nombre: str, rol: Rol, password: str) -> None:
    if len(password) < 10:
        raise ValueError("la contraseña debe tener al menos 10 caracteres")
    conn.execute(
        "INSERT INTO eleccion.usuario (nombre, rol, hash_password) VALUES (%s, %s, %s)",
        (nombre, rol.value, _hasher.hash(password)),
    )


def autenticar(conn, nombre: str, password: str) -> Rol:
    fila = conn.execute(
        "SELECT rol, hash_password FROM eleccion.usuario WHERE nombre = %s AND activo", (nombre,)
    ).fetchone()
    if fila is None:
        _hasher.hash(password)  # tiempo similar exista o no el usuario
        raise CredencialesInvalidas("usuario o contraseña incorrectos")
    try:
        _hasher.verify(fila[1], password)
    except VerificationError as e:
        raise CredencialesInvalidas("usuario o contraseña incorrectos") from e
    return Rol(fila[0])
