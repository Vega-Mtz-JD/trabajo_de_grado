"""Impresora térmica: VVPAT, zerésima, actas y partes de custodios.

Implementaciones:
  * ``ImpresoraMemoria``: guarda lo impreso en listas (pruebas automáticas).
  * ``ImpresoraPDF``: simula la impresora generando PDF (desarrollo y demostraciones).
  * ``ImpresoraEscPos``: impresora térmica USB real (Sprint 5).

Secreto del voto en la simulación: los VVPAT no se guardan como archivos sueltos (su orden o
fecha de creación revelaría el orden de votación). Se acumulan y, al vaciar la urna, se
escriben en un solo PDF con las páginas **mezcladas**, igual que las papeletas en una urna.
"""

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from votoseguro.dominio.modelos import Comprobante


class ImpresoraNoDisponible(Exception):
    pass


@dataclass(frozen=True)
class Documento:
    titulo: str
    lineas: list[str]
    qr: str | None = None          # texto a codificar en QR (hashes, parte de custodio)
    nombre_archivo: str = "documento"
    imagen: bytes | None = None    # foto (PNG/JPEG), p. ej. en la constancia de empadronamiento


class Impresora(ABC):
    @abstractmethod
    def disponible(self) -> bool: ...

    @abstractmethod
    def imprimir_vvpat(self, comprobante: Comprobante) -> None: ...

    @abstractmethod
    def imprimir_documento(self, documento: Documento) -> None: ...

    def vaciar_urna(self) -> None:
        """Al cierre: deja disponibles los VVPAT acumulados (en orden aleatorio)."""


def lineas_vvpat(c: Comprobante) -> list[str]:
    lineas = [
        "VOTO SEGURO",
        c.eleccion,
        f"Mesa: {c.mesa}",
        "-" * 24,
        f"OPCIÓN: {c.opcion.nombre}",
    ]
    if c.opcion.frente:
        lineas.append(c.opcion.frente)
    lineas += ["-" * 24, f"Código: {c.codigo}"]
    if c.reimpresion:
        lineas.append("** REIMPRESIÓN **")
    return lineas


@dataclass
class ImpresoraMemoria(Impresora):
    conectada: bool = True
    vvpat: list[Comprobante] = field(default_factory=list)
    documentos: list[Documento] = field(default_factory=list)

    def disponible(self) -> bool:
        return self.conectada

    def imprimir_vvpat(self, comprobante: Comprobante) -> None:
        if not self.conectada:
            raise ImpresoraNoDisponible("impresora sin papel o desconectada")
        self.vvpat.append(comprobante)

    def imprimir_documento(self, documento: Documento) -> None:
        if not self.conectada:
            raise ImpresoraNoDisponible("impresora sin papel o desconectada")
        self.documentos.append(documento)


class ImpresoraPDF(Impresora):
    """Genera un PDF por documento y un PDF con el contenido mezclado de la urna."""

    def __init__(self, carpeta: Path):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self._urna: list[Comprobante] = []
        self._contador = 0

    def disponible(self) -> bool:
        return True

    def imprimir_vvpat(self, comprobante: Comprobante) -> None:
        self._urna.append(comprobante)

    def imprimir_documento(self, documento: Documento) -> None:
        self._contador += 1
        ruta = self.carpeta / f"{self._contador:02d}_{documento.nombre_archivo}.pdf"
        pdf_documento(ruta, documento)

    def vaciar_urna(self) -> None:
        if not self._urna:
            return
        mezcladas = list(self._urna)
        # Fisher–Yates con aleatoriedad criptográfica
        for i in range(len(mezcladas) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            mezcladas[i], mezcladas[j] = mezcladas[j], mezcladas[i]
        _pdf_rollo_vvpat(self.carpeta / "urna_vvpat.pdf", mezcladas)
        self._urna.clear()


# --- Renderizado PDF (reportlab) -----------------------------------------------------------

def _dibujar_qr(canvas, texto: str, x: float, y: float, lado: float) -> None:
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing

    widget = QrCodeWidget(texto)
    x0, y0, x1, y1 = widget.getBounds()
    dibujo = Drawing(lado, lado, transform=[lado / (x1 - x0), 0, 0, lado / (y1 - y0), 0, 0])
    dibujo.add(widget)
    renderPDF.draw(dibujo, canvas, x, y)


def pdf_documento(ruta: Path, doc: Documento) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.pdfgen.canvas import Canvas

    c = Canvas(str(ruta), pagesize=letter)
    ancho, alto = letter
    y = alto - 2.5 * cm
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(ancho / 2, y, doc.titulo)
    if doc.imagen:
        import io

        from reportlab.lib.utils import ImageReader

        foto = ImageReader(io.BytesIO(doc.imagen))
        fw, fh = foto.getSize()
        w = 4.5 * cm
        c.drawImage(foto, ancho - 2.5 * cm - w, y - 0.6 * cm - w * fh / fw, w, w * fh / fw)
    y -= 1 * cm
    c.setFont("Courier", 9)
    for linea in doc.lineas:
        if y < 2.5 * cm:
            c.showPage()
            c.setFont("Courier", 9)
            y = alto - 2.5 * cm
        c.drawString(2.5 * cm, y, linea)
        y -= 0.45 * cm
    if doc.qr:
        if y < 7 * cm:
            c.showPage()
            y = alto - 2.5 * cm
        _dibujar_qr(c, doc.qr, 2.5 * cm, y - 5 * cm, 4.5 * cm)
    c.save()


def _pdf_rollo_vvpat(ruta: Path, comprobantes: list[Comprobante]) -> None:
    from reportlab.lib.units import mm
    from reportlab.pdfgen.canvas import Canvas

    tam = (58 * mm, 75 * mm)  # papel térmico de 58 mm
    c = Canvas(str(ruta), pagesize=tam)
    for comp in comprobantes:
        y = tam[1] - 8 * mm
        for i, linea in enumerate(lineas_vvpat(comp)):
            c.setFont("Helvetica-Bold" if i in (0, 4) else "Helvetica", 7)
            c.drawString(4 * mm, y, linea[:38])
            y -= 4 * mm
        _dibujar_qr(c, comp.codigo, 18 * mm, 2 * mm, 20 * mm)
        c.showPage()
    c.save()
