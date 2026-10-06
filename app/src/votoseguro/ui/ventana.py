"""Ventana principal del panel de mesa: cabecera con la elección activa, navegación por páginas
según el rol del usuario y el estado de la elección, y barra de estado."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QScrollArea, QStackedWidget, QVBoxLayout,
    QWidget,
)

from votoseguro.ui.comun import etiqueta
from votoseguro.ui.estilo import HOJA, color_estado
from votoseguro.ui.paginas.auditoria import PaginaAuditoria
from votoseguro.ui.paginas.configuracion import PaginaConfiguracion
from votoseguro.ui.paginas.empadronamiento import PaginaEmpadronamiento
from votoseguro.ui.paginas.escrutinio import PaginaEscrutinio
from votoseguro.ui.paginas.inicio import PaginaInicio
from votoseguro.ui.paginas.jornada import PaginaJornada
from votoseguro.ui.paginas.usuarios import PaginaUsuarios


class VentanaPrincipal(QMainWindow):
    def __init__(self, sesion_app, kiosco):
        super().__init__()
        self.app, self.kiosco = sesion_app, kiosco
        self.setWindowTitle("VOTO SEGURO — Panel de mesa")
        self.setStyleSheet(HOJA)
        self.resize(1366, 768)

        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("VOTO SEGURO", "titulo", ajuste=False))
        self.selector = QComboBox()
        self.selector.setMinimumWidth(340)
        self.selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.selector.currentIndexChanged.connect(self._cambio_eleccion)
        self.estado = etiqueta("", "estado", ajuste=False)
        self.estado.setMinimumWidth(self.estado.fontMetrics().horizontalAdvance("EMPADRONAMIENTO") + 48)
        self.estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cabecera.addStretch()
        cabecera.addWidget(self.selector)
        cabecera.addWidget(self.estado)
        cabecera.addWidget(etiqueta(f"👤 {self.app.usuario} ({self.app.rol.value.lower()})", "ayuda", ajuste=False))

        self.navegacion = QListWidget()
        self.navegacion.setObjectName("navegacion")
        self.navegacion.setFixedWidth(270)
        self.navegacion.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pila = QStackedWidget()
        self.paginas = [PaginaInicio(self.app, self), PaginaConfiguracion(self.app, self),
                        PaginaEmpadronamiento(self.app, self), PaginaJornada(self.app, self, kiosco),
                        PaginaEscrutinio(self.app, self), PaginaAuditoria(self.app, self),
                        PaginaUsuarios(self.app, self)]
        for pagina in self.paginas:
            desplazable = QScrollArea()      # pantallas de laptop (1366×768): las páginas largas se desplazan
            desplazable.setWidgetResizable(True)
            desplazable.setWidget(pagina)
            self.pila.addWidget(desplazable)
            self.navegacion.addItem(QListWidgetItem(pagina.titulo))
        self.navegacion.currentRowChanged.connect(self._mostrar)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.addWidget(self.navegacion)
        contenido = QVBoxLayout()
        contenido.addLayout(cabecera)
        contenido.addWidget(self.pila, 1)
        cuerpo.addLayout(contenido, 1)
        central = QWidget()
        central.setLayout(cuerpo)
        self.setCentralWidget(central)
        self._cargar_elecciones()
        self.navegacion.setCurrentRow(0)

    # --- Elección activa -------------------------------------------------------------------

    def _cargar_elecciones(self, seleccionar: str | None = None) -> None:
        self.selector.blockSignals(True)
        self.selector.clear()
        for eid, descripcion in self.app.elecciones():
            self.selector.addItem(descripcion, eid)
        indice = self.selector.findData(seleccionar or self.app.eleccion_id)
        self.selector.setCurrentIndex(max(0, indice))
        self.selector.blockSignals(False)
        self.app.eleccion_id = self.selector.currentData()
        self.actualizar()

    def seleccionar_eleccion(self, eleccion_id: str) -> None:
        self._cargar_elecciones(eleccion_id)

    def _cambio_eleccion(self) -> None:
        if self.kiosco.ocupada:
            self.barra("No se puede cambiar de elección con la cabina ocupada")
            self.selector.blockSignals(True)
            self.selector.setCurrentIndex(max(0, self.selector.findData(self.app.eleccion_id)))
            self.selector.blockSignals(False)
            return
        self.app.eleccion_id = self.selector.currentData()
        self.actualizar()

    def actualizar(self) -> None:
        """Refresca cabecera, navegación y página visible (tras un cambio de estado)."""
        actual = self.app.eleccion_id
        if actual:
            indice = self.selector.findData(actual)
            descripciones = dict(self.app.elecciones())
            if indice >= 0 and actual in descripciones:
                self.selector.setItemText(indice, descripciones[actual])
        e = self.app.eleccion()
        self.estado.setText(e.estado.value if e else "SIN ELECCIÓN")
        self.estado.setStyleSheet(f"background: {color_estado(e.estado.value if e else '')};")
        for i, pagina in enumerate(self.paginas):
            self.navegacion.item(i).setHidden(self.app.rol not in pagina.roles)
            item = self.navegacion.item(i)
            if pagina.disponible():
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self._mostrar(self.navegacion.currentRow())

    def _mostrar(self, fila: int) -> None:
        if fila < 0:
            return
        pagina = self.paginas[fila]
        if not pagina.disponible():
            fila = 0
            pagina = self.paginas[0]
            self.navegacion.blockSignals(True)
            self.navegacion.setCurrentRow(0)
            self.navegacion.blockSignals(False)
        self.pila.setCurrentIndex(fila)
        pagina.refrescar()

    def ir_a(self, clase) -> None:
        for i, pagina in enumerate(self.paginas):
            if isinstance(pagina, clase):
                self.navegacion.setCurrentRow(i)

    def pagina_actual(self):
        return self.paginas[self.pila.currentIndex()]

    def barra(self, texto: str) -> None:
        self.statusBar().showMessage(texto, 8000)

    def closeEvent(self, evento) -> None:
        if self.kiosco.ocupada:
            self.barra("Hay un votante en la cabina: no se puede cerrar el panel")
            evento.ignore()
            return
        self.kiosco._cierre_autorizado = True
        self.kiosco.close()
        evento.accept()
