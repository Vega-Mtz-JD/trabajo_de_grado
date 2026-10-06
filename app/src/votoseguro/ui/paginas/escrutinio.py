"""Escrutinio con las partes de los custodios y exportación del paquete de auditoría."""

from pathlib import Path

from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QLineEdit, QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
)

from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Estado, Rol
from votoseguro.servicios import escrutinio, exportacion
from votoseguro.ui.comun import ejecutar, etiqueta, mensaje
from votoseguro.ui.paginas.base import Pagina, elegir_carpeta, pedir_frase


class PaginaEscrutinio(Pagina):
    titulo = "Escrutinio y exportación"
    roles = {Rol.ADMIN, Rol.OPERADOR}
    estados = {Estado.CERRADA, Estado.ESCRUTADA, Estado.EXPORTADA}

    def __init__(self, sesion_app, ventana):
        super().__init__(sesion_app, ventana)
        self.caja_partes = QGroupBox("Partes de la clave de los custodios")
        f = QFormLayout(self.caja_partes)
        f.addRow(etiqueta("Cada custodio escribe (o lee con el lector de QR) el texto de su hoja: VS1-…", "ayuda"))
        self.partes = []
        for i in range(1, 10):
            campo = QLineEdit()
            campo.setEchoMode(QLineEdit.EchoMode.Password)
            campo.setPlaceholderText("VS1-00X-…")
            self.partes.append(campo)
            f.addRow(f"Custodio {i}", campo)
        self.boton_escrutar = QPushButton("Reconstruir la clave y contar los votos")
        self.boton_escrutar.clicked.connect(self.escrutar)
        f.addRow(self.boton_escrutar)
        self.capa.addWidget(self.caja_partes)

        self.caja_resultados = QGroupBox("Resultados de la mesa")
        r = QFormLayout(self.caja_resultados)
        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Opción", "Votos", "%"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.hash_acta = etiqueta("", "ayuda")
        r.addRow(self.tabla)
        r.addRow(self.hash_acta)
        self.boton_exportar = QPushButton("Exportar el paquete de auditoría (USB)…")
        self.boton_exportar.clicked.connect(self.exportar)
        r.addRow(self.boton_exportar)
        self.capa.addWidget(self.caja_resultados)
        self.capa.addStretch()

    def refrescar(self) -> None:
        e = self.app.eleccion()
        if e is None:
            return
        self.caja_partes.setVisible(e.estado == Estado.CERRADA)
        for i, campo in enumerate(self.partes):
            campo.setVisible(i < e.partes)
            self.caja_partes.layout().labelForField(campo).setVisible(i < e.partes)
        acta = repo.actas(self.app.conn, e.id).get("ESCRUTINIO")
        self.caja_resultados.setVisible(acta is not None)
        self.boton_exportar.setEnabled(e.estado == Estado.ESCRUTADA)
        if acta is None:
            return
        opciones = repo.opciones(self.app.conn, e.id)          # orden de la boleta
        resultados = acta["contenido"]["resultados"]
        total = sum(resultados.values()) or 1
        self.tabla.setRowCount(len(opciones))
        for i, opcion in enumerate(opciones):
            votos = resultados.get(opcion.codigo, 0)
            self.tabla.setItem(i, 0, QTableWidgetItem(opcion.nombre))
            self.tabla.setItem(i, 1, QTableWidgetItem(str(votos)))
            barra = QProgressBar()
            barra.setRange(0, 1000)
            barra.setValue(round(1000 * votos / total))
            barra.setFormat(f"{100 * votos / total:.1f} %")
            self.tabla.setCellWidget(i, 2, barra)
        self.tabla.resizeColumnsToContents()
        self.hash_acta.setText(f"Total: {sum(resultados.values())} votos · hash del acta de escrutinio: {acta['hash']}")

    def escrutar(self) -> None:
        partes = [c.text().strip() for c in self.partes if c.isVisible() and c.text().strip()]
        e = self.app.eleccion()
        if len(partes) < e.umbral:
            mensaje(self, "Partes insuficientes", f"Se requieren al menos {e.umbral} partes de custodios.", error=True)
            return
        if ejecutar(self, lambda: escrutinio.escrutar(self.app.ctx(), e.id, partes),
                    exito="Escrutinio completado: se imprimió el acta de escrutinio."):
            for c in self.partes:
                c.clear()
            self.avisar_cambio()

    def exportar(self) -> None:
        carpeta = elegir_carpeta(self, "Carpeta (USB) para el paquete de auditoría")
        frase = carpeta and pedir_frase(self, "Proteger el paquete de auditoría", confirmar=True)
        if carpeta and frase:
            paquete = ejecutar(self, lambda: exportacion.exportar(self.app.ctx(), self.app.eleccion_id,
                                                                  Path(carpeta), frase))
            if paquete:
                mensaje(self, "Paquete exportado", f"Guardado en {paquete.ruta}\n"
                                                   f"Hash del manifiesto: {paquete.hash_manifiesto}")
                self.avisar_cambio()
