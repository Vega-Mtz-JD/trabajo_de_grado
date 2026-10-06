"""Auditoría triple y consolidación (auditor): paquetes USB + conteo en papel + ledger de Fabric."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QListWidget, QPushButton,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
)

from votoseguro.dominio.modelos import Rol
from votoseguro.hardware.impresora import Documento, pdf_documento
from votoseguro.servicios import consolidacion, verificacion
from votoseguro.ui.comun import ejecutar, etiqueta, mensaje
from votoseguro.ui.estilo import GRIS, ROJO, VERDE
from votoseguro.ui.paginas.base import Pagina, elegir_archivos


class PaginaAuditoria(Pagina):
    titulo = "Auditoría y consolidación"
    roles = {Rol.ADMIN, Rol.AUDITOR}

    def __init__(self, sesion_app, ventana):
        super().__init__(sesion_app, ventana)
        self.paquetes: list[str] = []
        self.resultado: consolidacion.ResultadoConsolidacion | None = None

        entrada = QGroupBox("1. Paquetes de las mesas")
        f = QFormLayout(entrada)
        self.lista = QListWidget()
        self.lista.setMaximumHeight(80)
        botones = QHBoxLayout()
        agregar, limpiar = QPushButton("Agregar paquetes .vsx…"), QPushButton("Quitar todos")
        limpiar.setObjectName("secundario")
        agregar.clicked.connect(self.agregar)
        limpiar.clicked.connect(self.limpiar)
        botones.addWidget(agregar)
        botones.addWidget(limpiar)
        botones.addStretch()
        self.frase = QLineEdit()
        self.frase.setEchoMode(QLineEdit.EchoMode.Password)
        self.ledger = QCheckBox("Comparar con el ledger de Hyperledger Fabric")
        self.ledger.setEnabled(self.app.puente is not None)
        self.ledger.setChecked(self.app.puente is not None)
        cargar = QPushButton("Abrir los paquetes")
        cargar.clicked.connect(self.cargar)
        f.addRow(self.lista)
        f.addRow(botones)
        f.addRow("Frase de paso", self.frase)
        f.addRow(self.ledger)
        f.addRow(cargar)
        self.capa.addWidget(entrada)

        papel = QGroupBox("2. Datos en papel (opcional): conteo manual de VVPAT y huella impresa en la zerésima")
        p = QFormLayout(papel)
        self.tabla_papel = QTableWidget(0, 3)
        self.tabla_papel.setHorizontalHeaderLabels(["Mesa", "Opción", "Conteo manual de VVPAT"])
        self.tabla_huellas = QTableWidget(0, 2)
        self.tabla_huellas.setHorizontalHeaderLabels(["Mesa", "Huella del equipo (zerésima de papel)"])
        for t in (self.tabla_papel, self.tabla_huellas):
            t.horizontalHeader().setStretchLastSection(True)
            t.setMinimumHeight(150)
        p.addRow(self.tabla_papel)
        p.addRow(self.tabla_huellas)
        self.boton_verificar = QPushButton("3. Verificar y consolidar")
        self.boton_verificar.setEnabled(False)
        self.boton_verificar.clicked.connect(self.verificar)
        p.addRow(self.boton_verificar)
        self.capa.addWidget(papel)

        self.veredicto = etiqueta("", "titulo")
        self.capa.addWidget(self.veredicto)
        self.arbol = QTreeWidget()
        self.arbol.setHeaderLabels(["Comprobación", "Nivel", "Resultado", "Detalle"])
        self.arbol.setMinimumHeight(320)
        self.capa.addWidget(self.arbol, 1)
        self.boton_guardar = QPushButton("Guardar el informe de auditoría (PDF)…")
        self.boton_guardar.setObjectName("secundario")
        self.boton_guardar.setEnabled(False)
        self.boton_guardar.clicked.connect(self.guardar)
        self.capa.addWidget(self.boton_guardar)

    # --- Paso 1: paquetes ----------------------------------------------------------------------

    def agregar(self) -> None:
        for ruta in elegir_archivos(self, "Paquetes de auditoría", "Paquete VOTO SEGURO (*.vsx)"):
            if ruta not in self.paquetes:
                self.paquetes.append(ruta)
                self.lista.addItem(ruta)

    def limpiar(self) -> None:
        self.paquetes.clear()
        self.lista.clear()
        self.tabla_papel.setRowCount(0)
        self.tabla_huellas.setRowCount(0)
        self.boton_verificar.setEnabled(False)

    def cargar(self) -> None:
        """Abre cada paquete para conocer sus mesas y opciones y preparar las tablas de papel."""
        if not self.paquetes:
            mensaje(self, "Sin paquetes", "Agregue al menos un paquete .vsx.", error=True)
            return
        filas_papel, mesas = [], []
        for ruta in self.paquetes:
            informe = verificacion.Informe()
            exp = verificacion.abrir_paquete(Path(ruta), self.frase.text(), informe)
            if exp is None:
                mensaje(self, "No se pudo abrir", f"{ruta}: frase incorrecta o archivo alterado.", error=True)
                return
            mesa = exp["eleccion.json"]["mesa"]
            mesas.append(mesa)
            filas_papel += [(mesa, o["codigo"]) for o in exp["eleccion.json"]["opciones"]]
        self.tabla_papel.setRowCount(len(filas_papel))
        for i, (mesa, codigo) in enumerate(filas_papel):
            for j, valor in enumerate((mesa, codigo)):
                celda = QTableWidgetItem(valor)
                celda.setFlags(celda.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.tabla_papel.setItem(i, j, celda)
            self.tabla_papel.setItem(i, 2, QTableWidgetItem(""))
        self.tabla_huellas.setRowCount(len(mesas))
        for i, mesa in enumerate(mesas):
            celda = QTableWidgetItem(mesa)
            celda.setFlags(celda.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_huellas.setItem(i, 0, celda)
            self.tabla_huellas.setItem(i, 1, QTableWidgetItem(""))
        self.boton_verificar.setEnabled(True)

    # --- Paso 3: verificación ------------------------------------------------------------------

    def _datos_papel(self) -> tuple[dict, dict]:
        conteos: dict[str, dict[str, int]] = {}
        for i in range(self.tabla_papel.rowCount()):
            texto = self.tabla_papel.item(i, 2).text().strip() if self.tabla_papel.item(i, 2) else ""
            if texto:
                if not texto.isdigit():
                    raise ValueError(f"el conteo de la fila {i + 1} debe ser un número entero")
                mesa, codigo = self.tabla_papel.item(i, 0).text(), self.tabla_papel.item(i, 1).text()
                conteos.setdefault(mesa, {})[codigo] = int(texto)
        huellas = {self.tabla_huellas.item(i, 0).text(): self.tabla_huellas.item(i, 1).text().strip()
                   for i in range(self.tabla_huellas.rowCount())
                   if self.tabla_huellas.item(i, 1) and self.tabla_huellas.item(i, 1).text().strip()}
        return conteos, huellas

    def verificar(self) -> None:
        def accion():
            conteos, huellas = self._datos_papel()
            consultar = self.app.puente.consultar_mesa if self.ledger.isChecked() and self.app.puente else None
            return consolidacion.consolidar([Path(p) for p in self.paquetes], self.frase.text(),
                                            conteos_papel=conteos, huellas=huellas, consultar_ledger=consultar)
        resultado = ejecutar(self, accion)
        if not resultado:
            return
        self.resultado = resultado
        self._mostrar(resultado)
        self.boton_guardar.setEnabled(True)

    def _mostrar(self, r: consolidacion.ResultadoConsolidacion) -> None:
        simbolo = {True: ("✔", VERDE), False: ("✘", ROJO), None: ("—", GRIS)}
        self.arbol.clear()

        def agregar(padre, chequeos):
            for c in chequeos:
                texto, color = simbolo[c.ok]
                item = QTreeWidgetItem(padre, [c.nombre, c.nivel, texto, c.detalle])
                item.setForeground(2, QBrush(QColor(color)))

        for mesa, informe in sorted(r.informes_mesa.items()):
            resultados = " · ".join(f"{k}: {v}" for k, v in sorted(r.resultados_mesa.get(mesa, {}).items()))
            raiz = QTreeWidgetItem(self.arbol, [f"Mesa {mesa}", "", "CONFORME" if informe.conforme else "DISCREPANCIAS",
                                                resultados])
            raiz.setForeground(2, QBrush(QColor(VERDE if informe.conforme else ROJO)))
            agregar(raiz, informe.chequeos)
            raiz.setExpanded(not informe.conforme)
        consolidado = QTreeWidgetItem(self.arbol, ["Consolidación", "", "", ""])
        agregar(consolidado, r.global_.chequeos)
        consolidado.setExpanded(True)
        totales = QTreeWidgetItem(self.arbol, ["Total consolidado", "", "",
                                               " · ".join(f"{k}: {v}" for k, v in r.total.items())])
        totales.setExpanded(True)
        for i in range(4):
            self.arbol.resizeColumnToContents(i)
        self.veredicto.setText("RESULTADO: CONFORME" if r.conforme else "RESULTADO: CON DISCREPANCIAS")
        self.veredicto.setStyleSheet(f"color: {VERDE if r.conforme else ROJO};")

    def guardar(self) -> None:
        if not self.resultado:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar informe", "informe_auditoria.pdf", "PDF (*.pdf)")
        if ruta:
            texto = [self.resultado.texto(), ""]
            for mesa, informe in sorted(self.resultado.informes_mesa.items()):
                texto += [f"=== Mesa {mesa} ===", informe.texto(), ""]
            lineas = [linea for bloque in texto for linea in bloque.splitlines()]
            ejecutar(self, lambda: pdf_documento(Path(ruta), Documento("INFORME DE AUDITORÍA TRIPLE", lineas)),
                     exito=f"Informe guardado en {ruta}")
