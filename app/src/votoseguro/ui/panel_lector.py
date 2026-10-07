"""Panel del lector de huella: elegir el dispositivo, conectar, capturar o verificar y desconectar.

El botón de acción (``boton_accion``) lo conecta cada página: en el empadronamiento captura la
huella (``capturar``); en la mesa de identificación la verifica contra la registrada.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout

from votoseguro.hardware.huella import LectorSimulado
from votoseguro.servicios import empadronamiento
from votoseguro.ui.comun import ejecutar, etiqueta
from votoseguro.ui.dialogo_huella import Huella, leer_huella
from votoseguro.ui.estilo import ACENTO, BORDE_FUERTE, ROJO, VERDE
from votoseguro.ui.vista_camara import COMPACTO

# Lectores que se pueden elegir. El ZKTeco aparecerá habilitado cuando se incorpore su
# controlador (ADR-006); mientras tanto se muestra como pendiente.
LECTORES = [(LectorSimulado.nombre, lambda: LectorSimulado(abierto=False))]
PENDIENTES = ["ZKTeco ZK9500 / SLK20R (pendiente de compra)"]


class PanelLector(QGroupBox):
    huella_capturada = Signal()

    def __init__(self, app, titulo: str = "Lector de huella", texto_accion: str = "Capturar huella"):
        super().__init__(titulo)
        self.setStyleSheet(COMPACTO)
        self.app = app
        self.plantilla: bytes | None = None
        self._accion_permitida = True
        capa = QVBoxLayout(self)
        self.selector = QComboBox()
        for nombre, _fabrica in LECTORES:
            self.selector.addItem(nombre)
        for nombre in PENDIENTES:
            self.selector.addItem(nombre)
            modelo = self.selector.model()
            if isinstance(modelo, QStandardItemModel):
                modelo.item(self.selector.count() - 1).setEnabled(False)
        self.selector.activated.connect(self._elegir)
        capa.addWidget(self.selector)

        fila = QHBoxLayout()
        self.dibujo = Huella(48, 60)
        fila.addWidget(self.dibujo)
        self.estado = etiqueta("", "subtitulo")
        fila.addWidget(self.estado, 1)
        capa.addLayout(fila)

        botones = QHBoxLayout()
        self.boton_conectar = QPushButton("Conectar")
        self.boton_accion = QPushButton(texto_accion)
        self.boton_desconectar = QPushButton("Desconectar")
        for b in (self.boton_conectar, self.boton_desconectar):
            b.setObjectName("secundario")
        self.boton_conectar.clicked.connect(self.conectar)
        self.boton_desconectar.clicked.connect(self.desconectar)
        for b in (self.boton_conectar, self.boton_accion, self.boton_desconectar):
            botones.addWidget(b)
        capa.addLayout(botones)
        self.sincronizar()

    # --- Dispositivo ---------------------------------------------------------------------------

    def _elegir(self, fila: int) -> None:
        if fila >= len(LECTORES):
            return
        self.app.lector.cerrar()
        self.app.cambiar_lector(LECTORES[fila][1]())
        self.sincronizar()

    def conectar(self) -> None:
        if ejecutar(self, lambda: self._abrir()):
            self.sincronizar()

    def _abrir(self) -> None:
        from votoseguro.hardware.huella import LectorNoDisponible
        from votoseguro.servicios.base import HardwareNoDisponible

        try:
            self.app.lector.abrir()
        except LectorNoDisponible as e:
            raise HardwareNoDisponible(str(e)) from e

    def desconectar(self) -> None:
        self.app.lector.cerrar()
        self.sincronizar()

    def conectado(self) -> bool:
        return self.app.lector.abierto

    def sincronizar(self) -> None:
        """Refleja el estado del lector (lo comparten el empadronamiento y la mesa)."""
        conectado = self.conectado()
        self.boton_conectar.setEnabled(not conectado)
        self.boton_desconectar.setEnabled(conectado)
        self.boton_accion.setEnabled(conectado and self._accion_permitida)
        self.selector.setEnabled(not conectado)
        if self.plantilla is not None:
            self.marcar(True, "Huella capturada")
        elif conectado:
            self._pintar(ACENTO, "Conectado · listo")
        else:
            self._pintar(BORDE_FUERTE, "Desconectado · presione «Conectar»")

    def marcar(self, ok: bool, texto: str) -> None:
        self._pintar(VERDE if ok else ROJO, ("✔ " if ok else "✘ ") + texto)

    def _pintar(self, color: str, texto: str) -> None:
        self.dibujo.color = QColor(color)
        self.dibujo.update()
        self.estado.setText(texto)

    # --- Captura (empadronamiento) -------------------------------------------------------------

    def capturar(self) -> None:
        plantilla = ejecutar(self, lambda: leer_huella(
            self, "Apoye el dedo índice en el lector…", lambda: empadronamiento.capturar_huella(self.app.ctx()),
            "Huella capturada", "No se pudo leer la huella"))
        if isinstance(plantilla, bytes):
            self.plantilla = plantilla
            self.marcar(True, "Huella capturada")
            self.huella_capturada.emit()
        else:
            self.marcar(False, "No se pudo leer la huella: intente de nuevo")

    def limpiar(self) -> None:
        self.plantilla = None
        self.sincronizar()

    def showEvent(self, evento) -> None:
        self.sincronizar()
        super().showEvent(evento)

    def permitir_accion(self, permitida: bool) -> None:
        """La página indica si la acción tiene sentido ahora (p. ej. hay un votante identificado)."""
        self._accion_permitida = permitida
        self.boton_accion.setEnabled(permitida and self.conectado())
