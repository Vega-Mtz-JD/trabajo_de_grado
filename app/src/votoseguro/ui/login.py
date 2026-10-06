"""Inicio de sesión del personal (Argon2id), con bloqueo tras intentos fallidos (propuesta §8.3).

Cada intento queda en la bitácora: permite responder quién intentó entrar y cuándo (ISO/IEC 27001,
control de registro de eventos).
"""

import time

from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

from votoseguro.auditoria import bitacora
from votoseguro.dominio.modelos import Rol
from votoseguro.servicios import usuarios
from votoseguro.ui.comun import etiqueta, mensaje

MAX_INTENTOS = 3
BLOQUEO_SEGUNDOS = 5 * 60


class Bloqueo:
    """Cuenta intentos fallidos; tras ``MAX_INTENTOS`` bloquea durante ``BLOQUEO_SEGUNDOS``."""

    def __init__(self, reloj=time.monotonic):
        self._reloj = reloj
        self.fallidos = 0
        self.hasta = 0.0

    def restante(self) -> int:
        return max(0, int(self.hasta - self._reloj() + 0.999))

    def fallo(self) -> None:
        self.fallidos += 1
        if self.fallidos >= MAX_INTENTOS:
            self.hasta = self._reloj() + BLOQUEO_SEGUNDOS
            self.fallidos = 0

    def exito(self) -> None:
        self.fallidos = 0


class DialogoLogin(QDialog):
    def __init__(self, conn, bloqueo: Bloqueo | None = None, roles: set[Rol] | None = None,
                 titulo: str = "Ingreso del personal", parent=None):
        super().__init__(parent)
        self.conn, self.bloqueo, self.roles = conn, bloqueo or Bloqueo(), roles
        self.usuario: str = ""
        self.rol: Rol | None = None
        self.setWindowTitle("VOTO SEGURO — " + titulo)
        self.setMinimumWidth(420)
        self.campo_usuario = QLineEdit()
        self.campo_clave = QLineEdit()
        self.campo_clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.boton = QPushButton("Ingresar")
        self.boton.setDefault(True)
        self.boton.clicked.connect(self.intentar)
        self.aviso = etiqueta("", "ayuda")
        formulario = QFormLayout()
        formulario.addRow("Usuario", self.campo_usuario)
        formulario.addRow("Contraseña", self.campo_clave)
        capa = QVBoxLayout(self)
        capa.addWidget(etiqueta(titulo, "titulo"))
        capa.addLayout(formulario)
        capa.addWidget(self.aviso)
        capa.addWidget(self.boton)

    def intentar(self) -> None:
        if self.bloqueo.restante():
            self.aviso.setText(f"Acceso bloqueado por intentos fallidos. Espere {self.bloqueo.restante()} s.")
            return
        nombre = self.campo_usuario.text().strip()
        try:
            rol = usuarios.autenticar(self.conn, nombre, self.campo_clave.text())
            if self.roles and rol not in self.roles:
                raise usuarios.CredencialesInvalidas("el usuario no tiene el rol requerido")
        except usuarios.CredencialesInvalidas as e:
            self.bloqueo.fallo()
            bitacora.registrar(self.conn, nombre or "(vacío)", "LOGIN_FALLIDO", {"motivo": str(e)})
            self.campo_clave.clear()
            self.aviso.setText(str(e).capitalize()
                               + (f". Bloqueado {BLOQUEO_SEGUNDOS // 60} minutos." if self.bloqueo.restante() else "."))
            return
        self.bloqueo.exito()
        bitacora.registrar(self.conn, nombre, "LOGIN_EXITOSO", {"rol": rol.value})
        self.usuario, self.rol = nombre, rol
        self.accept()


class DialogoPrimerUso(QDialog):
    """Primer uso del equipo: no hay usuarios, se crea el administrador."""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("VOTO SEGURO — Primer uso")
        self.setMinimumWidth(480)
        self.campo_usuario = QLineEdit("admin")
        self.campo_clave = QLineEdit()
        self.campo_repetir = QLineEdit()
        for c in (self.campo_clave, self.campo_repetir):
            c.setEchoMode(QLineEdit.EchoMode.Password)
        boton = QPushButton("Crear administrador")
        boton.clicked.connect(self.crear)
        formulario = QFormLayout()
        formulario.addRow("Usuario", self.campo_usuario)
        formulario.addRow("Contraseña (mín. 10)", self.campo_clave)
        formulario.addRow("Repetir contraseña", self.campo_repetir)
        capa = QVBoxLayout(self)
        capa.addWidget(etiqueta("Configuración inicial", "titulo"))
        capa.addWidget(etiqueta("Este equipo aún no tiene usuarios. Cree la cuenta del administrador.", "ayuda"))
        capa.addLayout(formulario)
        capa.addWidget(boton)

    def crear(self) -> None:
        if self.campo_clave.text() != self.campo_repetir.text():
            mensaje(self, "Contraseñas distintas", "Las contraseñas no coinciden.", error=True)
            return
        try:
            usuarios.crear_usuario(self.conn, self.campo_usuario.text().strip(), Rol.ADMIN, self.campo_clave.text())
        except Exception as e:  # validación de longitud o nombre de usuario inválido (CHECK de la BD)
            mensaje(self, "No se pudo crear", str(e), error=True)
            return
        bitacora.registrar(self.conn, self.campo_usuario.text().strip(), "USUARIO_CREADO", {"rol": "ADMIN"})
        self.accept()


def hay_usuarios(conn) -> bool:
    return conn.execute("SELECT EXISTS (SELECT FROM eleccion.usuario)").fetchone()[0]
