"""Ventana breve del lector de huella: «Coloque el dedo…» → «✔ Huella capturada» / «✘ No coincide».

Con el lector simulado hace visible el paso de la huella en las demostraciones; con el lector real
acompaña la espera mientras la persona apoya el dedo.
"""

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QWidget

from votoseguro.ui.estilo import ACENTO, ROJO, VERDE

DURACION_MS = 1200   # duración de la lectura simulada (las pruebas la reducen)


class _Huella(QWidget):
    """Dibujo simple de una huella dactilar (arcos concéntricos)."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(96, 120)
        self.color = QColor(ACENTO)

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(self.color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for i in range(7):
            m = 6 + i * 6
            p.drawArc(QRectF(m, m, 96 - 2 * m, 120 - 2 * m), 290 * 16, 320 * 16)   # abertura abajo


class DialogoHuella(QDialog):
    def __init__(self, mensaje: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lector de huella")
        self.setModal(True)
        self.setMinimumWidth(360)
        capa = QVBoxLayout(self)
        self.dibujo = _Huella()
        capa.addWidget(self.dibujo, alignment=Qt.AlignmentFlag.AlignCenter)
        self.texto = QLabel(mensaje)
        self.texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texto.setStyleSheet("font-size: 17px; font-weight: 600;")
        capa.addWidget(self.texto)
        self.barra = QProgressBar()
        self.barra.setRange(0, 0)       # animación de espera
        self.barra.setTextVisible(False)
        capa.addWidget(self.barra)

    def resultado(self, ok: bool, texto: str) -> None:
        self.barra.setRange(0, 1)
        self.barra.setValue(1)
        self.dibujo.color = QColor(VERDE if ok else ROJO)
        self.dibujo.update()
        self.texto.setText(("✔ " if ok else "✘ ") + texto)
        self.texto.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {VERDE if ok else ROJO};")
        QTimer.singleShot(max(300, DURACION_MS // 2), self.accept)


def leer_huella(padre, mensaje: str, accion, texto_ok: str, texto_error: str):
    """Muestra el lector mientras se ejecuta ``accion`` (captura o verificación). Devuelve el
    resultado de ``accion`` o ``None`` si falló; la excepción se vuelve a lanzar después de mostrar
    el resultado, para que la página muestre el detalle."""
    dialogo = DialogoHuella(mensaje, padre)
    estado: dict = {}

    def ejecutar():
        try:
            estado["valor"] = accion()
            dialogo.resultado(True, texto_ok)
        except Exception as e:  # se informa en la ventana y se relanza al cerrar
            estado["error"] = e
            dialogo.resultado(False, texto_error)

    QTimer.singleShot(DURACION_MS, ejecutar)
    dialogo.exec()
    if "error" in estado:
        raise estado["error"]
    return estado.get("valor")
