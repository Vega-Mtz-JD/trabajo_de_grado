"""Panel de la cámara de la mesa: elegir el dispositivo, encender, tomar la foto y apagar.

La cámara solo está encendida mientras el operador la usa: se apaga sola al tomar la foto y al
salir de la página, para no consumir recursos. La imagen en vivo se dibuja en una etiqueta común
(sin ventanas nativas de video, que en Wayland pueden aparecer sueltas).
"""

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from votoseguro.hardware.camara import CamaraNoDisponible, CamaraSimulada
from votoseguro.ui.comun import ejecutar, etiqueta, imagen
from votoseguro.ui.estilo import VERDE

SIMULADA = "Cámara simulada (sin dispositivo)"
# Botones algo más chicos dentro de los paneles de dispositivos (caben tres en una fila).
COMPACTO = "QPushButton { padding: 7px 10px; } QComboBox { padding: 5px 8px; }"


def _es_real(camara) -> bool:
    return hasattr(camara, "al_recibir")


class PanelCamara(QGroupBox):
    """``antes_de_tomar`` se llama justo antes de la foto (con hardware simulado indica quién
    está frente a la cámara). La última foto queda en ``foto``; se emite ``foto_tomada``."""

    foto_tomada = Signal()

    def __init__(self, app, titulo: str = "Cámara", lado: int = 240,
                 antes_de_tomar: Callable[[], None] | None = None):
        super().__init__(titulo)
        self.setStyleSheet(COMPACTO)
        self.app, self.lado = app, lado
        self._permitido = True
        self.antes_de_tomar = antes_de_tomar or (lambda: None)
        self.foto: bytes | None = None
        self._encendida = False
        self._dispositivos: list = []
        capa = QVBoxLayout(self)

        linea = QHBoxLayout()
        self.selector = QComboBox()
        self.selector.setToolTip("Cámara integrada o cámara USB externa")
        self.selector.activated.connect(self._elegir)
        self.boton_buscar = QPushButton("↻")
        self.boton_buscar.setObjectName("secundario")
        self.boton_buscar.setFixedWidth(42)
        self.boton_buscar.setToolTip("Volver a buscar cámaras (después de conectar una cámara USB)")
        self.boton_buscar.clicked.connect(self.buscar_dispositivos)
        linea.addWidget(self.selector, 1)
        linea.addWidget(self.boton_buscar)
        capa.addLayout(linea)

        self.vista = QLabel()
        self.vista.setFixedSize(lado, int(lado * 0.75))
        self.vista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vista.setWordWrap(True)
        capa.addWidget(self.vista, alignment=Qt.AlignmentFlag.AlignCenter)

        botones = QHBoxLayout()
        self.boton_encender = QPushButton("Encender")
        self.boton_foto = QPushButton("Tomar foto")
        self.boton_apagar = QPushButton("Apagar")
        for b, accion in ((self.boton_encender, self.encender), (self.boton_foto, self.tomar_foto),
                          (self.boton_apagar, self.apagar)):
            if b is not self.boton_foto:
                b.setObjectName("secundario")
            b.clicked.connect(accion)
            botones.addWidget(b)
        capa.addLayout(botones)
        self.estado = etiqueta("", "ayuda")
        self.estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(self.estado)

        self.buscar_dispositivos()
        self._botones(False)
        self._mostrar_apagada()

    # --- Dispositivos --------------------------------------------------------------------------

    def buscar_dispositivos(self) -> None:
        """Lista las cámaras conectadas y marca la que usa el sistema."""
        from votoseguro.hardware.camara_qt import dispositivos

        self._dispositivos = dispositivos()
        actual = self.app.camara
        self.selector.blockSignals(True)
        self.selector.clear()
        for d in self._dispositivos:
            self.selector.addItem(d.description())
        self.selector.addItem(SIMULADA)
        if _es_real(actual):
            ids = [d.id() for d in self._dispositivos]
            fila = ids.index(actual.dispositivo.id()) if actual.dispositivo.id() in ids else 0
        else:
            fila = len(self._dispositivos)
        self.selector.setCurrentIndex(fila)
        self.selector.blockSignals(False)

    def _elegir(self, fila: int) -> None:
        self.apagar()
        if fila >= len(self._dispositivos):
            nueva = CamaraSimulada()
        else:
            from votoseguro.hardware.camara_qt import CamaraQt

            try:
                nueva = CamaraQt(self._dispositivos[fila])
            except CamaraNoDisponible as e:
                self.estado.setText(f"✘ {e}")
                self.buscar_dispositivos()
                return
        self.app.cambiar_camara(nueva)
        self.estado.setText(f"Cámara elegida: {self.selector.currentText()}")

    # --- Encender, foto, apagar ----------------------------------------------------------------

    def encendida(self) -> bool:
        return self._encendida

    def encender(self) -> None:
        camara = self.app.camara
        if _es_real(camara):
            camara.al_recibir(self._mostrar_cuadro)
            camara.encender()
            self.vista.setText("Encendiendo la cámara…")
        else:
            self.vista.setText("Cámara simulada encendida\n(la foto se genera por software)")
        self.vista.setStyleSheet("background:#111827; color:#e5e7eb; border-radius:8px;")
        self._botones(True)
        self.estado.setText("Pida a la persona que mire a la cámara y presione «Tomar foto».")

    def tomar_foto(self) -> None:
        self.antes_de_tomar()
        foto = ejecutar(self, lambda: self.app.ctx().tomar_foto())
        if not isinstance(foto, bytes):
            return
        self.foto = foto
        self.apagar()
        self.vista.setPixmap(imagen(foto, self.lado))
        self.estado.setText(f"<span style='color:{VERDE}'>✔ Foto tomada</span> · cámara apagada")
        self.foto_tomada.emit()

    def apagar(self) -> None:
        camara = self.app.camara
        if _es_real(camara):
            camara.al_recibir(None)
            camara.apagar()
        self._botones(False)
        if self.foto is None:
            self._mostrar_apagada()

    def limpiar(self) -> None:
        """Nueva persona: descarta la foto anterior."""
        self.foto = None
        self.apagar()
        self.estado.setText("")

    def permitir(self, permitido: bool) -> None:
        """Habilita o no los controles (la foto tomada se sigue viendo con sus colores)."""
        self._permitido = permitido
        if not permitido and self._encendida:
            self.apagar()
        self._botones(self._encendida)

    def _botones(self, encendida: bool) -> None:
        self._encendida = encendida
        libre = self._permitido
        self.boton_encender.setEnabled(libre and not encendida)
        self.boton_foto.setEnabled(libre and encendida)
        self.boton_apagar.setEnabled(libre and encendida)
        self.selector.setEnabled(libre and not encendida)
        self.boton_buscar.setEnabled(libre and not encendida)

    def _mostrar_apagada(self) -> None:
        self.vista.setPixmap(QPixmap())
        self.vista.setText("Cámara apagada\nPresione «Encender»")
        self.vista.setStyleSheet("background:#eef0f3; color:#6b7280; border-radius:8px;")

    def _mostrar_cuadro(self, cuadro) -> None:
        if not self.encendida():
            return
        self.vista.setPixmap(QPixmap.fromImage(cuadro).scaled(
            self.vista.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def hideEvent(self, evento) -> None:      # al salir de la página la cámara se apaga
        if self.encendida():
            self.apagar()
        super().hideEvent(evento)

    def showEvent(self, evento) -> None:
        self.buscar_dispositivos()
        super().showEvent(evento)
