"""Empadronamiento en la propia urna: datos, foto y huella; cruce de padrones entre mesas."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado, Rol
from votoseguro.servicios import empadronamiento, votacion
from votoseguro.ui.comun import confirmar, ejecutar, etiqueta, imagen, mensaje
from votoseguro.ui.paginas.base import Pagina, elegir_archivos, elegir_carpeta, pedir_frase, pedir_texto


class PaginaEmpadronamiento(Pagina):
    titulo = "Empadronamiento"
    menu = "Empadronamiento"
    roles = {Rol.ADMIN, Rol.OPERADOR}
    estados = {Estado.CONFIGURACION, Estado.EMPADRONAMIENTO, Estado.LISTA}

    def __init__(self, sesion_app, ventana):
        super().__init__(sesion_app, ventana)
        self.boton_iniciar = QPushButton("Iniciar el empadronamiento")
        self.boton_iniciar.clicked.connect(self.iniciar)
        self.capa.addWidget(self.boton_iniciar)

        fila = QHBoxLayout()
        self.caja_registro = QGroupBox("Registrar votante")
        f = QFormLayout(self.caja_registro)
        self.ci, self.nombres, self.apellidos = QLineEdit(), QLineEdit(), QLineEdit()
        self.ci.setPlaceholderText("Número de CI (con complemento si tiene, p. ej. 4567890-1A)")
        f.addRow("CI", self.ci)
        f.addRow("Nombres", self.nombres)
        f.addRow("Apellidos", self.apellidos)
        f.addRow(etiqueta("La persona debe estar frente a la cámara y apoyar el dedo índice en el lector.", "ayuda"))
        self.boton_registrar = QPushButton("Tomar foto, capturar huella y registrar")
        self.boton_registrar.clicked.connect(self.registrar)
        f.addRow(self.boton_registrar)
        fila.addWidget(self.caja_registro, 3)
        foto = QVBoxLayout()
        self.foto = QLabel()
        self.foto.setPixmap(imagen(None, 180))
        self.foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pie_foto = etiqueta("Última foto registrada", "ayuda")
        self.pie_foto.setFixedWidth(190)
        self.pie_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foto.addWidget(self.foto)
        foto.addWidget(self.pie_foto)
        foto.addStretch()
        fila.addLayout(foto, 1)
        self.capa.addLayout(fila)

        self.resumen = etiqueta("", "subtitulo")
        self.capa.addWidget(self.resumen)
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["CI", "Apellidos", "Nombres", "Habilitado"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.itemSelectionChanged.connect(self.mostrar_foto_seleccionada)
        self.capa.addWidget(self.tabla)

        botones = QHBoxLayout()
        self.boton_inhabilitar = QPushButton("Inhabilitar…")
        self.boton_resumen = QPushButton("Exportar resumen…")
        self.boton_cruzar = QPushButton("Cruzar padrones…")
        self.boton_inhabilitar.setToolTip("Inhabilita al votante seleccionado (p. ej. empadronado en otra mesa)")
        self.boton_resumen.setToolTip("Resumen cifrado del padrón de esta mesa, para el cruce entre mesas")
        self.boton_cruzar.setToolTip("Detecta personas empadronadas en más de una mesa")
        self.boton_cerrar = QPushButton("Cerrar el padrón")
        for b, accion in ((self.boton_inhabilitar, self.inhabilitar), (self.boton_resumen, self.exportar_resumen),
                          (self.boton_cruzar, self.cruzar), (self.boton_cerrar, self.cerrar)):
            b.setObjectName("secundario" if b is not self.boton_cerrar else "")
            b.clicked.connect(accion)
            botones.addWidget(b)
        self.capa.addLayout(botones)

    def refrescar(self) -> None:
        e = self.app.eleccion()
        if e is None:
            return
        en_registro = e.estado == Estado.EMPADRONAMIENTO
        self.boton_iniciar.setVisible(e.estado == Estado.CONFIGURACION)
        for w in (self.caja_registro, self.boton_inhabilitar, self.boton_cerrar):
            w.setEnabled(en_registro)
        self.boton_resumen.setEnabled(e.estado in (Estado.EMPADRONAMIENTO, Estado.LISTA))
        padron = repo.padron_completo(self.app.conn, e.id)
        habilitados = sum(v["habilitado"] for v in padron)
        estado = "abierto" if en_registro else ("cerrado" if e.estado == Estado.LISTA else "sin iniciar")
        self.resumen.setText(f"Padrón de la mesa {e.mesa}: {len(padron)} registrados · {habilitados} habilitados "
                             f"· padrón {estado}")
        self.tabla.setRowCount(len(padron))
        for i, v in enumerate(padron):
            for j, valor in enumerate((v["ci"], v["apellidos"], v["nombres"], "sí" if v["habilitado"] else "NO")):
                self.tabla.setItem(i, j, QTableWidgetItem(valor))
        self.tabla.resizeColumnsToContents()

    # --- Acciones ------------------------------------------------------------------------------

    def iniciar(self) -> None:
        if ejecutar(self, lambda: empadronamiento.iniciar(self.app.ctx(), self.app.eleccion_id)):
            self.avisar_cambio()

    def registrar(self) -> None:
        ci = self.ci.text().strip().upper()
        nombres, apellidos = self.nombres.text().strip(), self.apellidos.text().strip()
        if not (ci and nombres and apellidos):
            mensaje(self, "Datos incompletos", "Complete CI, nombres y apellidos.", error=True)
            return
        self.app.preparar_simulacion(ci)
        if ejecutar(self, lambda: empadronamiento.registrar_votante(self.app.ctx(), self.app.eleccion_id, ci,
                                                                     nombres, apellidos)):
            self.foto.setPixmap(imagen(votacion.foto_registro(self.app.ctx(), self.app.eleccion_id, ci), 180))
            self.pie_foto.setText(f"{apellidos}, {nombres} — CI {ci}")
            self.ventana.barra(f"Votante {ci} registrado")
            for campo in (self.ci, self.nombres, self.apellidos):
                campo.clear()
            self.ci.setFocus()
            self.refrescar()

    def _ci_seleccionado(self) -> str | None:
        fila = self.tabla.currentRow()
        return self.tabla.item(fila, 0).text() if fila >= 0 and self.tabla.item(fila, 0) else None

    def mostrar_foto_seleccionada(self) -> None:
        ci = self._ci_seleccionado()
        if ci:
            self.foto.setPixmap(imagen(votacion.foto_registro(self.app.ctx(), self.app.eleccion_id, ci), 180))
            self.pie_foto.setText(f"CI {ci}")

    def inhabilitar(self) -> None:
        ci = self._ci_seleccionado()
        if not ci:
            mensaje(self, "Seleccione un votante", "Seleccione una fila del padrón.", error=True)
            return
        motivo = pedir_texto(self, "Inhabilitar votante", f"Motivo para inhabilitar al CI {ci}:")
        if motivo and ejecutar(self, lambda: empadronamiento.inhabilitar_votante(
                self.app.ctx(), self.app.eleccion_id, ci, motivo)):
            self.refrescar()

    def exportar_resumen(self) -> None:
        carpeta = elegir_carpeta(self, "Carpeta (USB) para el resumen del padrón")
        frase = carpeta and pedir_frase(self, "Proteger el resumen del padrón", confirmar=True)
        if carpeta and frase:
            ruta = ejecutar(self, lambda: empadronamiento.exportar_resumen_padron(
                self.app.ctx(), self.app.eleccion_id, Path(carpeta), frase))
            if ruta:
                mensaje(self, "Resumen exportado", f"Guardado en {ruta}")

    def cruzar(self) -> None:
        rutas = elegir_archivos(self, "Resúmenes de padrón de todas las mesas", "Resumen de padrón (*.vsp)")
        frase = rutas and pedir_frase(self, "Abrir los resúmenes")
        if not (rutas and frase):
            return
        r = ejecutar(self, lambda: empadronamiento.cruzar_padrones([Path(x) for x in rutas], frase))
        if not r:
            return
        if r.limpio:
            mensaje(self, "Cruce de padrones", f"Sin duplicados: {r.total_votantes} votantes en las mesas "
                                               f"{', '.join(r.mesas)}.")
        else:
            lineas = [f"CI {ci}: mesas {', '.join(m)}" for ci, m in r.duplicados.items()]
            lineas += [f"Firma inválida: {x}" for x in r.firmas_invalidas]
            mensaje(self, "Duplicados detectados",
                    "Inhabilite a cada persona duplicada en todas las mesas menos una:\n\n" + "\n".join(lineas),
                    error=True)

    def cerrar(self) -> None:
        if confirmar(self, "Cerrar el padrón", "Después de cerrarlo no se podrán registrar más votantes. ¿Continuar?"):
            if ejecutar(self, lambda: empadronamiento.cerrar_padron(self.app.ctx(), self.app.eleccion_id)):
                self.avisar_cambio()
