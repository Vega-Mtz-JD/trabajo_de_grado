"""Clase base de las páginas del panel y diálogos auxiliares."""

from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QVBoxLayout, QWidget

from votoseguro.dominio.modelos import Estado, Rol
from votoseguro.ui.comun import etiqueta, mensaje


class Pagina(QWidget):
    titulo = ""
    menu = ""          # texto corto en el menú lateral (si está vacío, se usa el título)
    roles: set[Rol] = {Rol.ADMIN, Rol.OPERADOR, Rol.AUDITOR}
    estados: set[Estado] | None = None   # None = disponible siempre (no depende de la elección)

    def __init__(self, sesion_app, ventana):
        super().__init__()
        self.app, self.ventana = sesion_app, ventana
        self.capa = QVBoxLayout(self)
        self.capa.setContentsMargins(28, 12, 28, 28)
        self.capa.setSpacing(14)
        self.capa.addWidget(etiqueta(self.titulo, "titulo"))

    def disponible(self) -> bool:
        if self.app.rol not in self.roles:
            return False
        if self.estados is None:
            return True
        eleccion = self.app.eleccion()
        return eleccion is not None and eleccion.estado in self.estados

    def refrescar(self) -> None:
        """Vuelve a leer los datos al mostrarse la página o cambiar la elección."""

    def avisar_cambio(self) -> None:
        """La página cambió el estado de la elección: se actualizan cabecera y navegación."""
        self.ventana.actualizar()


def pedir_frase(padre: QWidget, titulo: str, *, confirmar: bool = False) -> str | None:
    """Pide una frase de paso (mín. 12 caracteres). Con ``confirmar`` la pide dos veces."""
    frase, ok = QInputDialog.getText(padre, titulo, "Frase de paso (mínimo 12 caracteres):",
                                     QLineEdit.EchoMode.Password)
    if not ok:
        return None
    if len(frase) < 12:
        mensaje(padre, "Frase muy corta", "La frase de paso debe tener al menos 12 caracteres.", error=True)
        return None
    if confirmar:
        repetida, ok = QInputDialog.getText(padre, titulo, "Repita la frase de paso:", QLineEdit.EchoMode.Password)
        if not ok or repetida != frase:
            mensaje(padre, "Frases distintas", "Las frases de paso no coinciden.", error=True)
            return None
    return frase


def pedir_texto(padre: QWidget, titulo: str, etiqueta_: str) -> str | None:
    texto, ok = QInputDialog.getText(padre, titulo, etiqueta_)
    return texto.strip() if ok and texto.strip() else None


def elegir_carpeta(padre: QWidget, titulo: str) -> str | None:
    return QFileDialog.getExistingDirectory(padre, titulo) or None


def elegir_archivos(padre: QWidget, titulo: str, filtro: str) -> list[str]:
    archivos, _ = QFileDialog.getOpenFileNames(padre, titulo, "", filtro)
    return archivos
