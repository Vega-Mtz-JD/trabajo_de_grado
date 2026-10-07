"""Cámara web real mediante Qt Multimedia (cámara integrada de la laptop o cámara USB externa).

Implementa la interfaz ``Camara`` (ADR-006): ``capturar()`` devuelve una foto JPEG reducida a
480 px de ancho.

La imagen en vivo se entrega como ``QImage`` a una función receptora (``al_recibir``), a pocos
cuadros por segundo, y la interfaz la dibuja en una etiqueta común. No se usa ``QVideoWidget``:
crea una ventana nativa que en Wayland puede aparecer como una ventana suelta. La cámara solo
se enciende cuando el operador lo pide y se apaga después de tomar la foto, para no consumir
recursos del equipo. Apagada, el dispositivo queda **liberado** (``/dev/videoN`` cerrado): Qt lo
mantiene abierto mientras exista el ``QCamera``, así que este se crea al encender y se destruye
al apagar.

Requiere una ``QApplication`` en ejecución (la usa la interfaz gráfica).
"""

import time
from collections.abc import Callable

import shiboken6

from PySide6.QtCore import QBuffer, QByteArray, QEventLoop, QIODevice, Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaCaptureSession, QMediaDevices, QVideoSink

from votoseguro.hardware.camara import Camara, CamaraNoDisponible

ANCHO_FOTO = 480
CALENTAMIENTO_S = 1.2     # la cámara recién encendida entrega imágenes oscuras
CUADROS_VISTA = 12        # cuadros por segundo de la vista en vivo (ahorra CPU)
ESPERA_MAXIMA_MS = 8000


def hay_camara() -> bool:
    return bool(QMediaDevices.videoInputs())


def dispositivos() -> list[QCameraDevice]:
    """Cámaras conectadas (integrada y externas USB)."""
    return list(QMediaDevices.videoInputs())


def _formato_liviano(dispositivo: QCameraDevice):
    """Formato de video más cercano a 640 px de ancho: suficiente para la foto y liviano."""
    formatos = [f for f in dispositivo.videoFormats() if f.resolution().width() >= 640]
    if not formatos:
        return None
    return min(formatos, key=lambda f: (f.resolution().width(), -f.maxFrameRate()))


class CamaraQt(Camara):
    def __init__(self, dispositivo: QCameraDevice | None = None):
        if dispositivo is None:
            disponibles = dispositivos()
            if not disponibles:
                raise CamaraNoDisponible("no se encontró ninguna cámara")
            dispositivo = disponibles[0]
        self.dispositivo = dispositivo
        self.descripcion = dispositivo.description()
        self._camara: QCamera | None = None
        self._sumidero = QVideoSink()
        self._sesion = QMediaCaptureSession()
        self._sesion.setVideoSink(self._sumidero)
        self._sumidero.videoFrameChanged.connect(self._nuevo_cuadro)
        self._cuadro = None
        self._receptor: Callable[[QImage], None] | None = None
        self._ultimo_envio = 0.0
        self._encendida_desde = 0.0
        self.ultimo_error = ""

    # --- Estado --------------------------------------------------------------------------------

    def disponible(self) -> bool:
        return any(d.id() == self.dispositivo.id() for d in dispositivos())

    def encendida(self) -> bool:
        return self._camara is not None

    def encender(self) -> None:
        if self._camara is not None:
            return
        self.ultimo_error = ""
        self._cuadro = None
        self._camara = QCamera(self.dispositivo)
        formato = _formato_liviano(self.dispositivo)
        if formato is not None:
            self._camara.setCameraFormat(formato)
        self._camara.errorOccurred.connect(self._error)
        self._sesion.setCamera(self._camara)
        self._camara.start()
        self._encendida_desde = time.monotonic()

    def apagar(self) -> None:
        """Detiene la cámara y libera el dispositivo (se apaga la luz de la cámara)."""
        if self._camara is not None:
            self._camara.stop()
            self._sesion.setCamera(None)
            shiboken6.delete(self._camara)      # libera el dispositivo ya, no al volver al lazo de eventos
            self._camara = None
        self._cuadro = None

    def al_recibir(self, receptor: Callable[[QImage], None] | None) -> None:
        """Función que recibe la imagen en vivo (``None`` para dejar de recibirla)."""
        self._receptor = receptor

    def _error(self, _codigo, texto: str) -> None:
        self.ultimo_error = texto

    def _nuevo_cuadro(self, cuadro) -> None:
        if self._camara is None or not cuadro.isValid():
            return
        self._cuadro = cuadro
        ahora = time.monotonic()
        if self._receptor is not None and ahora - self._ultimo_envio >= 1 / CUADROS_VISTA:
            self._ultimo_envio = ahora
            self._receptor(cuadro.toImage())

    # --- Foto ----------------------------------------------------------------------------------

    def _lista(self) -> bool:
        return self._cuadro is not None and time.monotonic() - self._encendida_desde >= CALENTAMIENTO_S

    def _esperar_cuadro(self) -> None:
        """Espera (sin bloquear la interfaz) a que la cámara entregue imágenes ya estabilizadas."""
        if self._lista():
            return
        lazo = QEventLoop()
        limite = time.monotonic() + ESPERA_MAXIMA_MS / 1000

        def revisar():
            if self._lista() or self.ultimo_error or time.monotonic() > limite:
                lazo.quit()
            else:
                QTimer.singleShot(50, revisar)

        QTimer.singleShot(0, revisar)
        lazo.exec()

    def capturar(self) -> bytes:
        """Foto del cuadro actual. Si la cámara estaba apagada, la enciende, toma la foto y la
        vuelve a apagar."""
        estaba_apagada = not self.encendida()
        self.encender()
        try:
            self._esperar_cuadro()
            if self._cuadro is None:
                raise CamaraNoDisponible(self.ultimo_error or "la cámara no entregó imagen "
                                         "(¿está en uso por otro programa o desconectada?)")
            imagen = self._cuadro.toImage()
        finally:
            if estaba_apagada:
                self.apagar()
        if imagen.isNull():
            raise CamaraNoDisponible("la cámara entregó una imagen vacía")
        reducida = imagen.scaledToWidth(ANCHO_FOTO, Qt.TransformationMode.SmoothTransformation)
        datos = QByteArray()
        bufer = QBuffer(datos)
        bufer.open(QIODevice.OpenModeFlag.WriteOnly)
        reducida.save(bufer, "JPEG", 85)
        return bytes(datos.data())
