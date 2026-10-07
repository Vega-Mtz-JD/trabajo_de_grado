"""Cámara web real mediante Qt Multimedia (cámara integrada de la laptop o cámara USB).

Implementa la interfaz ``Camara`` (ADR-006): ``capturar()`` devuelve una foto JPEG reducida a
480 px de ancho. Además ofrece ``mostrar_en(vista)`` para ver la imagen en vivo dentro de la
interfaz (empadronamiento y mesa de identificación).

Requiere una ``QApplication`` en ejecución (la usa la interfaz gráfica).
"""

import time

from PySide6.QtCore import QBuffer, QByteArray, QEventLoop, QIODevice, Qt, QTimer
from PySide6.QtMultimedia import QCamera, QImageCapture, QMediaCaptureSession, QMediaDevices

from votoseguro.hardware.camara import Camara, CamaraNoDisponible

ANCHO_FOTO = 480
CALENTAMIENTO_S = 1.2     # la cámara recién encendida entrega imágenes oscuras


def hay_camara() -> bool:
    return bool(QMediaDevices.videoInputs())


class CamaraQt(Camara):
    def __init__(self, dispositivo=None):
        dispositivos = QMediaDevices.videoInputs()
        if not dispositivos and dispositivo is None:
            raise CamaraNoDisponible("no se encontró ninguna cámara")
        self._camara = QCamera(dispositivo or dispositivos[0])
        self._captura = QImageCapture()
        self._sesion = QMediaCaptureSession()
        self._sesion.setCamera(self._camara)
        self._sesion.setImageCapture(self._captura)
        self.descripcion = (dispositivo or dispositivos[0]).description()
        self._encendida_desde = 0.0

    def disponible(self) -> bool:
        return self._camara.isAvailable()

    def encender(self) -> None:
        if not self._camara.isActive():
            self._camara.start()
            self._encendida_desde = time.monotonic()

    def apagar(self) -> None:
        self._camara.stop()

    def mostrar_en(self, vista) -> None:
        """Muestra la imagen en vivo en un ``QVideoWidget`` (una vista a la vez)."""
        self._sesion.setVideoOutput(vista)
        self.encender()

    def capturar(self) -> bytes:
        self.encender()
        resultado: dict = {}
        lazo = QEventLoop()

        def lista(_id, imagen):
            resultado["imagen"] = imagen
            lazo.quit()

        def error(_id, _codigo, texto):
            resultado["error"] = texto
            lazo.quit()

        def intentar():
            if time.monotonic() - self._encendida_desde < CALENTAMIENTO_S:
                QTimer.singleShot(100, intentar)
            elif self._captura.isReadyForCapture():
                self._captura.capture()
            elif not resultado:
                QTimer.singleShot(100, intentar)

        self._captura.imageCaptured.connect(lista)
        self._captura.errorOccurred.connect(error)
        try:
            QTimer.singleShot(0, intentar)
            QTimer.singleShot(8000, lazo.quit)        # tiempo máximo de espera
            lazo.exec()
        finally:
            self._captura.imageCaptured.disconnect(lista)
            self._captura.errorOccurred.disconnect(error)
        imagen = resultado.get("imagen")
        if imagen is None or imagen.isNull():
            raise CamaraNoDisponible(resultado.get("error") or "la cámara no respondió a tiempo")
        reducida = imagen.scaledToWidth(ANCHO_FOTO, Qt.TransformationMode.SmoothTransformation)
        datos = QByteArray()
        bufer = QBuffer(datos)
        bufer.open(QIODevice.OpenModeFlag.WriteOnly)
        reducida.save(bufer, "JPEG", 85)
        return bytes(datos.data())
