"""Gestión de usuarios del personal (solo administrador)."""

from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
)

from votoseguro.auditoria import bitacora
from votoseguro.dominio.modelos import Rol
from votoseguro.servicios import usuarios
from votoseguro.ui.comun import ejecutar
from votoseguro.ui.paginas.base import Pagina


class PaginaUsuarios(Pagina):
    titulo = "Usuarios del personal"
    menu = "Usuarios"
    roles = {Rol.ADMIN}

    def __init__(self, sesion_app, ventana):
        super().__init__(sesion_app, ventana)
        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Usuario", "Rol", "Activo"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.capa.addWidget(self.tabla)
        caja = QGroupBox("Nuevo usuario")
        f = QFormLayout(caja)
        self.nombre = QLineEdit()
        self.rol = QComboBox()
        self.rol.addItems([r.value for r in Rol])
        self.clave = QLineEdit()
        self.clave.setEchoMode(QLineEdit.EchoMode.Password)
        boton = QPushButton("Crear usuario")
        boton.clicked.connect(self.crear)
        f.addRow("Usuario", self.nombre)
        f.addRow("Rol", self.rol)
        f.addRow("Contraseña (mín. 10)", self.clave)
        f.addRow(boton)
        self.capa.addWidget(caja)

    def refrescar(self) -> None:
        filas = self.app.conn.execute("SELECT nombre, rol, activo FROM eleccion.usuario ORDER BY nombre").fetchall()
        self.tabla.setRowCount(len(filas))
        for i, (nombre, rol, activo) in enumerate(filas):
            for j, valor in enumerate((nombre, rol, "sí" if activo else "no")):
                self.tabla.setItem(i, j, QTableWidgetItem(valor))

    def crear(self) -> None:
        nombre, rol = self.nombre.text().strip(), Rol(self.rol.currentText())

        def accion():
            usuarios.crear_usuario(self.app.conn, nombre, rol, self.clave.text())
            bitacora.registrar(self.app.conn, self.app.usuario, "USUARIO_CREADO", {"usuario": nombre, "rol": rol.value})

        if ejecutar(self, accion, exito=f"Usuario {nombre} creado con rol {rol.value}."):
            self.nombre.clear()
            self.clave.clear()
            self.refrescar()
