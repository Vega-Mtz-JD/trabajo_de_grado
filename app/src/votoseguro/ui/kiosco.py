"""Kiosco del votante (cabina): pantalla completa, botones grandes y confirmación explícita.

Estados:  ESPERA → (el operador habilita la cabina) → SELECCIÓN → CONFIRMACIÓN → COMPROBANTE → ESPERA

* La cabina solo se activa con una ``SesionVoto`` entregada por la mesa de identificación, y cada
  sesión sirve para un único voto.
* Accesibilidad: letras grandes, alto contraste, teclas 1–9 para elegir, Enter para confirmar y
  Escape para corregir.
* No muestra datos del votante ni la hora. No se puede cerrar: la salida exige la contraseña de un
  operador, con bloqueo tras 3 intentos (ADR-005).
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Opcion, Rol, TipoOpcion
from votoseguro.servicios import votacion
from votoseguro.servicios.votacion import ErrorImpresionVVPAT, SesionVoto
from votoseguro.ui.comun import ejecutar, etiqueta
from votoseguro.ui.estilo import HOJA_KIOSCO
from votoseguro.ui.login import Bloqueo, DialogoLogin

SEGUNDOS_COMPROBANTE = 7   # como el VVPAT de la India: el votante lo ve y luego cae a la urna


class VentanaKiosco(QWidget):
    voto_emitido = Signal(object)        # Comprobante
    falla_impresora = Signal(object)     # Comprobante sin imprimir: el operador debe reimprimirlo
    estado_cambiado = Signal(str)        # ESPERA | VOTANDO
    salida_autorizada = Signal()

    def __init__(self, sesion_app, *, pantalla_completa: bool = False):
        super().__init__()
        self.app = sesion_app
        self.sesion: SesionVoto | None = None
        self.opciones: list[Opcion] = []
        self.elegida: Opcion | None = None
        self.bloqueo = Bloqueo()
        self.setWindowTitle("VOTO SEGURO — Cabina de votación")
        self.setStyleSheet(HOJA_KIOSCO)
        if pantalla_completa:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self.pila = QStackedWidget()
        self.pila.addWidget(self._pantalla_espera())
        self.pila.addWidget(QWidget())               # selección (se arma al habilitar)
        self.pila.addWidget(self._pantalla_confirmacion())
        self.pila.addWidget(self._pantalla_comprobante())
        capa = QVBoxLayout(self)
        capa.addWidget(self.pila)
        salida = QPushButton("Salir del modo cabina (personal autorizado)")
        salida.setObjectName("salida")
        salida.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        salida.clicked.connect(self.pedir_salida)
        capa.addWidget(salida, alignment=Qt.AlignmentFlag.AlignRight)
        self._temporizador = QTimer(self, singleShot=True, interval=SEGUNDOS_COMPROBANTE * 1000)
        self._temporizador.timeout.connect(self.volver_a_espera)

    # --- Pantallas -------------------------------------------------------------------------

    def _pantalla_espera(self) -> QWidget:
        w = QWidget()
        capa = QVBoxLayout(w)
        capa.addStretch()
        capa.addWidget(etiqueta("VOTO SEGURO", "titulo"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.texto_espera = etiqueta("Por favor, espere a que el personal de mesa habilite la cabina.", "grande")
        self.texto_espera.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(self.texto_espera)
        capa.addStretch()
        return w

    def _pantalla_seleccion(self) -> QWidget:
        w = QWidget()
        capa = QVBoxLayout(w)
        eleccion = repo.obtener_eleccion(self.app.conn, self.sesion.eleccion_id)
        capa.addWidget(etiqueta(eleccion.nombre, "titulo"))
        capa.addWidget(etiqueta("Toque su opción o presione su número en el teclado.", "ayuda"))
        capa.addSpacing(12)
        for i, opcion in enumerate(self.opciones, 1):
            texto = f"  {i}.  {opcion.nombre}" + (f"\n        {opcion.frente}" if opcion.frente else "")
            boton = QPushButton(texto)
            boton.setObjectName("opcion" if opcion.tipo == TipoOpcion.CANDIDATO else "opcion_especial")
            boton.setAccessibleName(f"Opción {i}: {opcion.nombre}")
            boton.clicked.connect(lambda _=False, o=opcion: self.elegir(o))
            capa.addWidget(boton)
        capa.addStretch()
        return w

    def _pantalla_confirmacion(self) -> QWidget:
        w = QWidget()
        capa = QVBoxLayout(w)
        capa.addStretch()
        capa.addWidget(etiqueta("¿Confirma su voto?", "titulo"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.texto_eleccion = etiqueta("", "grande")
        self.texto_eleccion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(self.texto_eleccion)
        capa.addStretch()
        teclas = etiqueta("Presione  ENTER  para confirmar   ·   ESC  o  0  para corregir", "teclas")
        teclas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(teclas)
        botones = QHBoxLayout()
        botones.setSpacing(24)
        self.boton_corregir = QPushButton("Corregir   (Esc / 0)")
        self.boton_corregir.setObjectName("corregir")
        self.boton_corregir.clicked.connect(self.corregir)
        self.boton_confirmar = QPushButton("Confirmar voto   (Enter)")
        self.boton_confirmar.setObjectName("confirmar")
        self.boton_confirmar.clicked.connect(self.confirmar)
        botones.addWidget(self.boton_corregir)
        botones.addWidget(self.boton_confirmar)
        capa.addLayout(botones)
        return w

    def _pantalla_comprobante(self) -> QWidget:
        w = QWidget()
        capa = QVBoxLayout(w)
        capa.addStretch()
        capa.addWidget(etiqueta("¡Su voto fue registrado!", "titulo"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.texto_comprobante = etiqueta("", "grande")
        self.texto_comprobante.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(self.texto_comprobante)
        indicacion = etiqueta("Verifique su comprobante impreso y deposítelo en la urna.\n"
                              "No se lleve el comprobante.", "ayuda")
        indicacion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capa.addWidget(indicacion)
        capa.addStretch()
        return w

    # --- Flujo -----------------------------------------------------------------------------

    @property
    def ocupada(self) -> bool:
        return self.sesion is not None

    def habilitar(self, sesion: SesionVoto) -> None:
        """La mesa de identificación entrega una sesión de un solo uso."""
        if self.ocupada:
            raise RuntimeError("la cabina ya está ocupada")
        self.sesion, self.elegida = sesion, None
        self.opciones = repo.opciones(self.app.conn, sesion.eleccion_id)
        anterior = self.pila.widget(1)
        self.pila.insertWidget(1, self._pantalla_seleccion())
        self.pila.removeWidget(anterior)
        anterior.deleteLater()
        self.pila.setCurrentIndex(1)
        self.estado_cambiado.emit("VOTANDO")

    def elegir(self, opcion: Opcion) -> None:
        self.elegida = opcion
        detalle = f"\n{opcion.frente}" if opcion.frente else ""
        self.texto_eleccion.setText(f"{opcion.nombre}{detalle}")
        self.pila.setCurrentIndex(2)
        self.boton_confirmar.setFocus()

    def corregir(self) -> None:
        self.elegida = None
        self.pila.setCurrentIndex(1)

    def confirmar(self) -> None:
        if not self.sesion or not self.elegida:
            return
        sin_imprimir = []

        def emitir():
            try:
                return votacion.emitir(self.app.ctx(), self.sesion, self.elegida.codigo)
            except ErrorImpresionVVPAT as e:
                # El voto YA quedó registrado: no se repite; el operador revisa la impresora y reimprime.
                sin_imprimir.append(e.comprobante)
                return e.comprobante

        comprobante = ejecutar(self, emitir)
        if not comprobante:
            return
        if sin_imprimir:
            self.falla_impresora.emit(comprobante)
        self.sesion = None
        self.texto_comprobante.setText(f"{comprobante.opcion.nombre}\nCódigo del comprobante: {comprobante.codigo}")
        self.pila.setCurrentIndex(3)
        self.voto_emitido.emit(comprobante)
        self._temporizador.start()

    def volver_a_espera(self) -> None:
        self._temporizador.stop()
        self.elegida = None
        self.pila.setCurrentIndex(0)
        self.estado_cambiado.emit("ESPERA")

    # --- Teclado y cierre ------------------------------------------------------------------

    def keyPressEvent(self, evento) -> None:
        tecla, actual = evento.key(), self.pila.currentIndex()
        if actual == 1 and Qt.Key.Key_1 <= tecla <= Qt.Key.Key_9:
            indice = tecla - Qt.Key.Key_1
            if indice < len(self.opciones):
                self.elegir(self.opciones[indice])
        elif actual == 2 and tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirmar()
        elif actual == 2 and tecla in (Qt.Key.Key_Escape, Qt.Key.Key_0):
            self.corregir()
        # Cualquier otra tecla (Alt+F4, Escape en otras pantallas…) se ignora.

    def closeEvent(self, evento) -> None:
        if getattr(self, "_cierre_autorizado", False):
            evento.accept()
        else:
            evento.ignore()

    def pedir_salida(self) -> None:
        dialogo = DialogoLogin(self.app.conn, self.bloqueo, {Rol.OPERADOR, Rol.ADMIN},
                               "Salir del modo cabina", self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self._cierre_autorizado = True
            self.salida_autorizada.emit()
            self.close()
