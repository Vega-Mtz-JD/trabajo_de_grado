"""Vista de la cámara: imagen en vivo (cámara real) o aviso de cámara simulada."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from votoseguro.ui.comun import imagen


class VistaCamara(QWidget):
    """Muestra en vivo lo que ve la cámara real. Con la cámara simulada muestra un recuadro gris
    con el texto «cámara simulada». ``congelar(foto)`` deja ver la foto recién tomada."""

    def __init__(self, camara, lado: int = 220):
        super().__init__()
        self.camara, self.lado = camara, lado
        self.setFixedSize(lado, int(lado * 0.75))
        self.pila = QStackedLayout(self)
        self.en_vivo = None
        if hasattr(camara, "mostrar_en"):
            from PySide6.QtMultimediaWidgets import QVideoWidget

            self.en_vivo = QVideoWidget()
            self.pila.addWidget(self.en_vivo)
        else:
            aviso = QLabel("cámara simulada")
            aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)
            aviso.setStyleSheet("background:#eef0f3; color:#6b7280; border-radius:8px;")
            self.pila.addWidget(aviso)
        self.foto = QLabel()
        self.foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pila.addWidget(self.foto)

    def activar(self) -> None:
        """Conecta la cámara a esta vista (la cámara muestra en una sola vista a la vez)."""
        if self.en_vivo is not None:
            self.camara.mostrar_en(self.en_vivo)
        self.pila.setCurrentIndex(0)

    def congelar(self, foto: bytes | None) -> None:
        self.foto.setPixmap(imagen(foto, self.lado))
        self.pila.setCurrentIndex(1)
