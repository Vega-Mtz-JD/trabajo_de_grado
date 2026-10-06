"""Utilidades compartidas por las ventanas: diálogos de error, cursor de espera, imágenes."""

from collections.abc import Callable
from typing import Any

import psycopg
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget

from votoseguro.datos.conexion import ErrorVotoSeguro
from votoseguro.servicios.base import ErrorServicio


def ejecutar(padre: QWidget, accion: Callable[[], Any], *, exito: str | None = None) -> Any:
    """Ejecuta una acción de negocio con cursor de espera. Muestra los errores de negocio al
    operador con un mensaje claro y devuelve ``None`` si la acción falló."""
    QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        resultado = accion()
    except (ErrorServicio, ErrorVotoSeguro, ValueError, LookupError) as e:
        QGuiApplication.restoreOverrideCursor()
        mensaje(padre, "No se pudo completar la operación", str(e), error=True)
        return None
    except psycopg.Error as e:
        QGuiApplication.restoreOverrideCursor()
        mensaje(padre, "Error de base de datos", e.diag.message_primary or str(e), error=True)
        return None
    QGuiApplication.restoreOverrideCursor()
    if exito:
        mensaje(padre, "Listo", exito)
    return resultado if resultado is not None else True


def mensaje(padre: QWidget, titulo: str, texto: str, *, error: bool = False) -> None:
    caja = QMessageBox(QMessageBox.Icon.Warning if error else QMessageBox.Icon.Information, titulo, texto,
                       parent=padre)
    caja.exec()


def confirmar(padre: QWidget, titulo: str, texto: str) -> bool:
    return QMessageBox.question(padre, titulo, texto) == QMessageBox.StandardButton.Yes


def etiqueta(texto: str, nombre: str = "", *, ajuste: bool = True) -> QLabel:
    e = QLabel(texto)
    if nombre:
        e.setObjectName(nombre)
    e.setWordWrap(ajuste)
    return e


def imagen(datos: bytes | None, lado: int = 160) -> QPixmap:
    """Convierte una foto (PNG/JPEG) en un QPixmap cuadrado; gris si no hay foto."""
    mapa = QPixmap()
    if not datos or not mapa.loadFromData(datos):
        mapa = QPixmap(lado, lado)
        mapa.fill(Qt.GlobalColor.lightGray)
        return mapa
    return mapa.scaled(lado, lado, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
