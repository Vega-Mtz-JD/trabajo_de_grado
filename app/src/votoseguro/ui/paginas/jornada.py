"""Jornada de votación: apertura (zerésima), mesa de identificación y cierre.

Flujo en la mesa de identificación: CI → se muestra la foto de registro para la verificación
visual → huella 1:1 (o excepción manual con motivo) → foto de presencia → "Habilitar cabina".
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from votoseguro.datos import repositorio as repo
from votoseguro.datos.conexion import VotanteNoHabilitado
from votoseguro.dominio.modelos import Estado, Rol
from votoseguro.servicios import apertura, cierre, votacion
from votoseguro.ui.comun import confirmar, ejecutar, etiqueta, imagen, mensaje
from votoseguro.ui.estilo import ROJO, VERDE
from votoseguro.ui.paginas.base import Pagina, pedir_texto


class PaginaJornada(Pagina):
    titulo = "Jornada de votación"
    menu = "Jornada de votación"
    roles = {Rol.ADMIN, Rol.OPERADOR}
    estados = {Estado.LISTA, Estado.ABIERTA}

    def __init__(self, sesion_app, ventana, kiosco):
        super().__init__(sesion_app, ventana)
        self.kiosco = kiosco
        self.sesion = None
        self.ultimo_sin_imprimir = None
        kiosco.estado_cambiado.connect(self._estado_cabina)
        kiosco.voto_emitido.connect(lambda _c: self.refrescar())
        kiosco.falla_impresora.connect(self._falla_impresora)

        # Apertura
        self.caja_apertura = QGroupBox("Apertura de la mesa")
        a = QVBoxLayout(self.caja_apertura)
        self.diagnostico = etiqueta("")
        a.addWidget(self.diagnostico)
        self.boton_abrir = QPushButton("Abrir la mesa e imprimir la zerésima")
        self.boton_abrir.clicked.connect(self.abrir)
        a.addWidget(self.boton_abrir)
        self.capa.addWidget(self.caja_apertura)

        # Identificación
        self.caja_identificacion = QGroupBox("Mesa de identificación")
        fila = QHBoxLayout(self.caja_identificacion)
        izquierda = QFormLayout()
        self.ci = QLineEdit()
        self.ci.setPlaceholderText("CI del votante")
        self.ci.returnPressed.connect(self.buscar)
        buscar = QPushButton("Buscar")
        buscar.clicked.connect(self.buscar)
        linea = QHBoxLayout()
        linea.addWidget(self.ci)
        linea.addWidget(buscar)
        izquierda.addRow("CI", linea)
        self.datos_votante = etiqueta("", "subtitulo")
        izquierda.addRow(self.datos_votante)
        self.boton_huella = QPushButton("Verificar huella (máx. 3 intentos)")
        self.boton_huella.clicked.connect(self.verificar_huella)
        self.boton_excepcion = QPushButton("Excepción: huella ilegible…")
        self.boton_excepcion.setObjectName("secundario")
        self.boton_excepcion.clicked.connect(self.excepcion)
        self.simular_falla = QCheckBox("Simulación: la huella NO coincide")
        self.simular_falla.setVisible(self.app.simulado)
        izquierda.addRow(self.boton_huella)
        izquierda.addRow(self.boton_excepcion)
        izquierda.addRow(self.simular_falla)
        self.boton_cabina = QPushButton("Habilitar la cabina ▶")
        self.boton_cabina.clicked.connect(self.habilitar_cabina)
        izquierda.addRow(self.boton_cabina)
        self.estado_cabina = etiqueta("Cabina: libre", "subtitulo")
        izquierda.addRow(self.estado_cabina)
        fila.addLayout(izquierda, 3)
        fotos = QHBoxLayout()
        self.foto_registro, self.foto_presencia = QLabel(), QLabel()
        for foto, texto in ((self.foto_registro, "Foto de registro"), (self.foto_presencia, "Foto de hoy")):
            columna = QVBoxLayout()
            foto.setPixmap(imagen(None, 170))
            foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
            columna.addWidget(foto)
            columna.addWidget(etiqueta(texto, "ayuda"), alignment=Qt.AlignmentFlag.AlignCenter)
            columna.addStretch()
            fotos.addLayout(columna)
        fila.addLayout(fotos, 2)
        self.capa.addWidget(self.caja_identificacion)

        # Avance y cierre
        pie = QHBoxLayout()
        self.avance = etiqueta("", "subtitulo")
        self.boton_reimprimir = QPushButton("Reimprimir comprobante pendiente")
        self.boton_reimprimir.setObjectName("secundario")
        self.boton_reimprimir.clicked.connect(self.reimprimir)
        self.boton_cerrar = QPushButton("Cerrar la votación")
        self.boton_cerrar.setObjectName("peligro")
        self.boton_cerrar.clicked.connect(self.cerrar)
        pie.addWidget(self.avance, 1)
        pie.addWidget(self.boton_reimprimir)
        pie.addWidget(self.boton_cerrar)
        self.capa.addLayout(pie)
        self.capa.addStretch()
        self._limpiar_votante()

    # --- Estado ------------------------------------------------------------------------------

    def refrescar(self) -> None:
        e = self.app.eleccion()
        if e is None:
            return
        lista, abierta = e.estado == Estado.LISTA, e.estado == Estado.ABIERTA
        self.caja_apertura.setVisible(lista)
        self.caja_identificacion.setVisible(abierta)
        self.boton_cerrar.setVisible(abierta)
        self.boton_reimprimir.setVisible(self.ultimo_sin_imprimir is not None)
        if lista:
            ctx = self.app.ctx()
            filas = [("Lector de huella", ctx.lector.disponible()), ("Cámara", ctx.camara.disponible()),
                     ("Impresora", ctx.impresora.disponible()),
                     ("Hyperledger Fabric (opcional)", self.app.puente is not None and self.app.puente.disponible())]
            self.diagnostico.setText("<br>".join(
                f"<span style='color:{VERDE if ok else ROJO}'>{'✔' if ok else '✘'}</span> {n}" for n, ok in filas))
        padron = repo.conteos_padron(self.app.conn, e.id)
        self.avance.setText(f"Votaron {padron['votaron']} de {padron['habilitados']} habilitados")

    def _limpiar_votante(self) -> None:
        self.sesion, self.ci_actual = None, None
        self.datos_votante.setText("")
        self.foto_registro.setPixmap(imagen(None, 170))
        self.foto_presencia.setPixmap(imagen(None, 170))
        self.boton_huella.setEnabled(False)
        self.boton_excepcion.setEnabled(False)
        self.boton_cabina.setEnabled(False)

    def _estado_cabina(self, estado: str) -> None:
        self.estado_cabina.setText("Cabina: OCUPADA (votando)" if estado == "VOTANDO" else "Cabina: libre")
        if estado == "ESPERA":
            self.ci.setFocus()

    def _falla_impresora(self, comprobante) -> None:
        self.ultimo_sin_imprimir = comprobante
        self.boton_reimprimir.setVisible(True)
        mensaje(self, "Impresora", "El voto quedó registrado pero el comprobante NO se imprimió.\n"
                                   "Revise el papel de la impresora y presione «Reimprimir comprobante pendiente».",
                error=True)

    # --- Acciones ------------------------------------------------------------------------------

    def abrir(self) -> None:
        if confirmar(self, "Abrir la mesa", "Se imprimirá la zerésima (urna vacía) para la firma de los delegados. "
                                            "¿Abrir la mesa?"):
            if ejecutar(self, lambda: apertura.abrir(self.app.ctx(), self.app.eleccion_id)):
                self.avisar_cambio()

    def buscar(self) -> None:
        self._limpiar_votante()
        ci = self.ci.text().strip().upper()
        if not ci:
            return
        try:
            datos = votacion.identificar(self.app.ctx(), self.app.eleccion_id, ci)
        except VotanteNoHabilitado as e:
            self.datos_votante.setText(f"<span style='color:{ROJO}'>✘ {e}</span>")
            return
        self.ci_actual = ci
        self.datos_votante.setText(f"{datos['apellidos']}, {datos['nombres']}<br>"
                                   "<span style='font-weight:400'>Compare la foto con la persona presente.</span>")
        self.foto_registro.setPixmap(imagen(votacion.foto_registro(self.app.ctx(), self.app.eleccion_id, ci), 170))
        self.boton_huella.setEnabled(True)
        self.boton_excepcion.setEnabled(True)

    def _tras_autenticar(self, sesion) -> None:
        self.sesion = sesion
        foto = self.app.conn.execute("SELECT foto_cifrada FROM padron.presencia WHERE eleccion_id = %s AND ci = %s",
                                     (self.app.eleccion_id, self.ci_actual)).fetchone()
        if foto:
            self.foto_presencia.setPixmap(imagen(self.app.llavero.descifrar_personal(
                "foto_presencia", self.app.eleccion_id, self.ci_actual, bytes(foto[0])), 170))
        self.boton_huella.setEnabled(False)
        self.boton_excepcion.setEnabled(False)
        self.boton_cabina.setEnabled(not self.kiosco.ocupada)
        self.datos_votante.setText(self.datos_votante.text().split("<br>")[0]
                                   + f"<br><span style='color:{VERDE}'>✔ Identificado ({sesion.metodo.lower()})</span>")

    def verificar_huella(self) -> None:
        self.app.preparar_simulacion(self.ci_actual, huella_coincide=not self.simular_falla.isChecked())
        # Si la huella falla 3 veces, «ejecutar» muestra el motivo y devuelve None.
        sesion = ejecutar(self, lambda: votacion.autenticar_huella(self.app.ctx(), self.app.eleccion_id,
                                                                   self.ci_actual))
        if sesion:
            self._tras_autenticar(sesion)
        else:
            self.datos_votante.setText(self.datos_votante.text().split("<br>")[0] + "<br>"
                                       f"<span style='color:{ROJO}'>✘ La huella no coincide. Verifique el CI en "
                                       "persona y use la excepción si corresponde.</span>")

    def excepcion(self) -> None:
        motivo = pedir_texto(self, "Excepción manual",
                             "Motivo (p. ej. «huella ilegible; CI y foto verificados en persona»):")
        if motivo:
            self.app.preparar_simulacion(self.ci_actual)
            sesion = ejecutar(self, lambda: votacion.autorizar_excepcion(self.app.ctx(), self.app.eleccion_id,
                                                                         self.ci_actual, motivo))
            if sesion:
                self._tras_autenticar(sesion)

    def habilitar_cabina(self) -> None:
        if self.sesion is None or self.kiosco.ocupada:
            return
        self.kiosco.habilitar(self.sesion)
        self.ci.clear()
        self._limpiar_votante()

    def reimprimir(self) -> None:
        if self.ultimo_sin_imprimir and ejecutar(self, lambda: votacion.reimprimir(self.app.ctx(),
                                                                                  self.ultimo_sin_imprimir)):
            self.ultimo_sin_imprimir = None
            self.refrescar()

    def cerrar(self) -> None:
        if self.kiosco.ocupada:
            mensaje(self, "Cabina ocupada", "Espere a que el votante termine antes de cerrar.", error=True)
            return
        if confirmar(self, "Cerrar la votación", "Se imprimirán el acta de cierre y la lista de quienes no votaron. "
                                                 "Después no se podrá votar. ¿Cerrar la votación?"):
            if ejecutar(self, lambda: cierre.cerrar(self.app.ctx(), self.app.eleccion_id)):
                self.avisar_cambio()
