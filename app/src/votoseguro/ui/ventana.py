"""Ventana principal del panel de mesa: cabecera con la elección activa, navegación por páginas
según el rol del usuario y el estado de la elección, y barra de estado."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

from votoseguro.auditoria import bitacora

from votoseguro.ui.comun import etiqueta, mensaje
from votoseguro.ui.estilo import HOJA, color_estado
from votoseguro.ui.login import Bloqueo, DialogoLogin
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
        # Sin botón de cerrar: se sale con «Salir», que pide contraseña (según el escritorio, la "X"
        # puede seguir visible, pero no cierra la ventana; en modo kiosco no hay decoraciones).
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self._salida_autorizada = False
        self.bloqueo_salida = Bloqueo()
        self.resize(1366, 768)

        cabecera = QHBoxLayout()
        cabecera.setContentsMargins(16, 10, 16, 4)
        cabecera.addWidget(etiqueta("VOTO SEGURO", "marca", ajuste=False))
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
        cabecera.addWidget(etiqueta(f"{self.app.usuario} · {self.app.rol.value.lower()}", "ayuda", ajuste=False))
        self.boton_salir = QPushButton("Salir")
        self.boton_salir.setObjectName("salir")
        self.boton_salir.setToolTip("Cerrar el programa (pide su contraseña)")
        self.boton_salir.clicked.connect(self.salir)
        cabecera.addWidget(self.boton_salir)

        self.navegacion = QListWidget()
        self.navegacion.setObjectName("navegacion")
        self.navegacion.setFixedWidth(230)
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
            self.navegacion.addItem(QListWidgetItem(pagina.menu or pagina.titulo))
        self.navegacion.currentRowChanged.connect(self._mostrar)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.addWidget(self.navegacion)
        contenido = QVBoxLayout()
        contenido.setContentsMargins(0, 0, 0, 0)
        contenido.addLayout(cabecera)
        contenido.addWidget(self.pila, 1)
        cuerpo.addLayout(contenido, 1)
        self.panel = QWidget()
        self.panel.setLayout(cuerpo)
        if kiosco.una_pantalla:
            # Un solo monitor: panel y cabina se turnan dentro de ESTA ventana (no hay que traer otra
            # ventana al frente, lo que algunos escritorios —p. ej. GNOME con Wayland— impiden).
            self.pantallas = QStackedWidget()
            self.pantallas.addWidget(self.panel)
            self.pantallas.addWidget(kiosco)
            kiosco.incrustar()
            self.setCentralWidget(self.pantallas)
        else:
            self.pantallas = None
            self.setCentralWidget(self.panel)
        self._cargar_elecciones()
        self.navegacion.setCurrentRow(0)
        kiosco.estado_cambiado.connect(self._cabina_libre)

    def _cabina_libre(self, estado: str) -> None:
        """Con un solo monitor: al habilitar, la ventana pasa a mostrar la cabina a pantalla completa;
        al terminar el votante, vuelve el panel de mesa."""
        if self.pantallas is None:
            return
        if estado == "VOTANDO":
            self.pantallas.setCurrentWidget(self.kiosco)
            self.showFullScreen()
            self.kiosco.traer_al_frente()
        else:
            self.pantallas.setCurrentWidget(self.panel)
            self.showMaximized()
            self.raise_()
            self.activateWindow()

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
        texto, fondo = color_estado(e.estado.value if e else "")
        self.estado.setStyleSheet(f"color: {texto}; background: {fondo};")
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

    def salir(self) -> None:
        """Salida del programa: exige la contraseña de un usuario del personal (bloqueo tras 3 intentos)."""
        if self.kiosco.ocupada:
            mensaje(self, "Cabina ocupada", "Hay un votante en la cabina. Espere a que termine para salir.", error=True)
            return
        dialogo = DialogoLogin(self.app.conn, self.bloqueo_salida, None, "Salir del sistema", self)
        dialogo.campo_usuario.setText(self.app.usuario)
        dialogo.campo_clave.setFocus()
        dialogo.boton.setText("Salir")
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        bitacora.registrar(self.app.conn, dialogo.usuario, "SALIDA_SISTEMA", {"sesion": self.app.usuario})
        self._salida_autorizada = True
        self.kiosco._cierre_autorizado = True
        self.kiosco.close()
        self.close()

    def closeEvent(self, evento) -> None:
        if self._salida_autorizada:
            evento.accept()
            return
        evento.ignore()   # "X", Alt+F4…: solo se sale con el botón «Salir»
        self.barra("Para cerrar el programa use el botón «Salir» (pide su contraseña).")
