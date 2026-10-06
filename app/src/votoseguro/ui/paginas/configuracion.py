"""Configuración de la elección (administrador): definir, instalar la mesa en este equipo y
exportar/importar la definición para otras urnas (ADR-009)."""

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem,
)

from votoseguro.dominio.modelos import Definicion, Rol
from votoseguro.servicios import configuracion
from votoseguro.servicios.configuracion import Candidatura
from votoseguro.ui.comun import ejecutar, etiqueta, mensaje
from votoseguro.ui.paginas.base import Pagina, pedir_frase, pedir_texto


class PaginaConfiguracion(Pagina):
    titulo = "Configuración de la elección"
    menu = "Configuración"
    roles = {Rol.ADMIN}

    def __init__(self, sesion_app, ventana):
        super().__init__(sesion_app, ventana)
        self.definicion: Definicion | None = None

        nueva = QGroupBox("1. Nueva elección")
        f = QFormLayout(nueva)
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("p. ej. Elección de Directorio 2026")
        self.candidaturas = QTableWidget(2, 3)
        self.candidaturas.setHorizontalHeaderLabels(["Código", "Nombre", "Frente / agrupación"])
        self.candidaturas.horizontalHeader().setStretchLastSection(True)
        self.candidaturas.setMinimumHeight(160)
        botones = QHBoxLayout()
        agregar, quitar = QPushButton("+ Candidatura"), QPushButton("− Quitar fila")
        agregar.setObjectName("secundario")
        quitar.setObjectName("secundario")
        agregar.clicked.connect(lambda: self.candidaturas.insertRow(self.candidaturas.rowCount()))
        quitar.clicked.connect(lambda: self.candidaturas.removeRow(max(0, self.candidaturas.currentRow())))
        botones.addWidget(agregar)
        botones.addWidget(quitar)
        botones.addStretch()
        self.mesas = QLineEdit("01")
        self.mesas.setToolTip("Códigos de mesa separados por comas, p. ej. 01, 02, 03")
        self.umbral, self.partes, self.cada = QSpinBox(), QSpinBox(), QSpinBox()
        for campo, minimo, maximo, valor in ((self.umbral, 2, 9, 3), (self.partes, 2, 9, 5), (self.cada, 10, 100, 10)):
            campo.setRange(minimo, maximo)
            campo.setValue(valor)
            campo.setMaximumWidth(120)
        f.addRow("Nombre", self.nombre)
        f.addRow("Candidaturas", self.candidaturas)
        f.addRow("", botones)
        f.addRow("Mesas (urnas)", self.mesas)
        f.addRow("Custodios necesarios", self.umbral)
        f.addRow("Custodios totales", self.partes)
        f.addRow("Checkpoint cada N votos", self.cada)
        f.addRow(etiqueta("VOTO BLANCO y VOTO NULO se agregan automáticamente.", "ayuda"))
        self.boton_definir = QPushButton("Crear la elección")
        self.boton_definir.clicked.connect(self.definir)
        f.addRow(self.boton_definir)
        self.capa.addWidget(nueva)

        instalar = QGroupBox("2. Instalar una mesa en este equipo")
        g = QFormLayout(instalar)
        self.texto_definicion = etiqueta("Primero cree la elección o importe su definición.", "ayuda")
        self.mesa = QComboBox()
        self.boton_instalar = QPushButton("Instalar mesa (genera la clave y las partes de los custodios)")
        self.boton_instalar.clicked.connect(self.instalar)
        botones2 = QHBoxLayout()
        self.boton_exportar = QPushButton("Exportar definición para otras urnas…")
        self.boton_exportar.setObjectName("secundario")
        self.boton_exportar.clicked.connect(self.exportar)
        importar = QPushButton("Importar definición de otra urna…")
        importar.setObjectName("secundario")
        importar.clicked.connect(self.importar)
        botones2.addWidget(self.boton_exportar)
        botones2.addWidget(importar)
        g.addRow(self.texto_definicion)
        g.addRow("Mesa de este equipo", self.mesa)
        g.addRow(self.boton_instalar)
        g.addRow(botones2)
        self.capa.addWidget(instalar)
        self.capa.addStretch()
        self._actualizar_definicion()

    # --- Acciones ------------------------------------------------------------------------------

    def _leer_candidaturas(self) -> list[Candidatura]:
        candidaturas = []
        for fila in range(self.candidaturas.rowCount()):
            celdas = [self.candidaturas.item(fila, c) for c in range(3)]
            codigo, nombre, frente = (c.text().strip() if c else "" for c in celdas)
            if codigo or nombre:
                if not (codigo and nombre):
                    raise ValueError(f"la fila {fila + 1} necesita código y nombre")
                candidaturas.append(Candidatura(codigo.upper(), nombre, frente or None))
        return candidaturas

    def definir(self) -> None:
        def accion():
            if len(self.nombre.text().strip()) < 3:
                raise ValueError("escriba el nombre de la elección")
            return configuracion.definir_eleccion(
                self.nombre.text().strip(), self._leer_candidaturas(),
                mesas=[m.strip().upper() for m in self.mesas.text().split(",") if m.strip()],
                umbral=self.umbral.value(), partes=self.partes.value(), checkpoint_cada=self.cada.value())
        definicion = ejecutar(self, accion)
        if definicion:
            self.definicion = definicion
            self._actualizar_definicion()

    def _actualizar_definicion(self) -> None:
        d = self.definicion
        self.mesa.clear()
        self.boton_instalar.setEnabled(d is not None)
        self.boton_exportar.setEnabled(d is not None)
        if d is None:
            return
        self.texto_definicion.setText(
            f"<b>{d.nombre}</b> · opciones: {', '.join(o.codigo for o in d.opciones)} · "
            f"mesas: {', '.join(d.mesas)} · custodios {d.umbral} de {d.partes}<br>"
            f"Hash de la definición: {configuracion.hash_definicion(d)}")
        self.mesa.addItems(list(d.mesas))

    def instalar(self) -> None:
        if not self.definicion:
            return
        mesa = self.mesa.currentText()
        creada = ejecutar(self, lambda: configuracion.instalar_mesa(self.app.ctx(), self.definicion, mesa))
        if creada:
            mensaje(self, "Mesa instalada",
                    f"Se instaló la mesa {mesa}.\nSe imprimieron {self.definicion.partes} hojas con las partes de la "
                    f"clave: entregue una a cada custodio en sobre sellado. Se necesitan {self.definicion.umbral} "
                    "para el escrutinio.")
            self.ventana.seleccionar_eleccion(creada.eleccion_id)

    def exportar(self) -> None:
        if not self.definicion:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar definición", "definicion.vsd", "Definición (*.vsd)")
        frase = ruta and pedir_frase(self, "Proteger la definición", confirmar=True)
        if ruta and frase:
            h = ejecutar(self, lambda: configuracion.exportar_definicion(self.app.ctx(), self.definicion,
                                                                         Path(ruta), frase))
            if h:
                mensaje(self, "Definición exportada",
                        f"Guardada en {ruta}.\nSe imprimió la hoja de control con el hash y la huella del equipo:\n"
                        f"{self.app.llavero.huella_dispositivo}")

    def importar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir definición", "", "Definición (*.vsd)")
        frase = ruta and pedir_frase(self, "Abrir la definición")
        if not (ruta and frase):
            return
        huella = pedir_texto(self, "Huella del equipo creador",
                             "Huella impresa en la hoja de control (recomendado; vacío para omitir):")
        definicion = ejecutar(self, lambda: configuracion.importar_definicion(Path(ruta), frase, huella))
        if definicion:
            self.definicion = definicion
            self._actualizar_definicion()
