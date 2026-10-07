"""Lienzo para dibujar las figuras del informe con PySide6 (QPainter): PNG a 300 ppp y SVG.

Cada figura es un script ``fig_*.py`` que crea un ``Lienzo``, dibuja con sus primitivas
(cajas, procesos y almacenes de DFD, entidades externas, flechas, marcos) y llama a
``guardar(nombre)``. Las figuras se regeneran con ``docs/diagramas/generar.sh``.

Unidades: el lienzo se diseña en unidades lógicas; 800 unidades = 16 cm (ancho útil de la hoja
carta con los márgenes del Reglamento, Art. 34), así que 14 unidades ≈ 8 pt impresos.
Fuente: Liberation Sans (mismas medidas que Arial, la fuente del informe).
"""

import math
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, QSize, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QBrush, QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPolygonF, QTextDocument,
)
from PySide6.QtSvg import QSvgGenerator  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "adjuntos" / "diagramas"
FUENTE = "Liberation Sans"
UNIDADES_POR_CM = 50          # 800 unidades = 16 cm
PIXELES_POR_UNIDAD = 3.0      # 300 ppp aprox.

# Paleta sobria: se lee bien en pantalla y en impresión en escala de grises.
TINTA = "#1f2937"
GRIS = "#6b7280"
LINEA = "#374151"
BLANCO = "#ffffff"
AZUL, AZUL_SUAVE, AZUL_MEDIO = "#1e40af", "#e8efff", "#c7d7fe"
VERDE, VERDE_SUAVE = "#166534", "#e7f6ec"
ROJO, ROJO_SUAVE = "#b91c1c", "#fdecec"
AMBAR, AMBAR_SUAVE = "#92400e", "#fdf3e1"
GRIS_SUAVE, GRIS_MEDIO = "#f3f4f6", "#d1d5db"

_app = QGuiApplication.instance() or QGuiApplication([])


@dataclass
class Rect:
    """Rectángulo con puntos de anclaje para conectar flechas."""
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def arriba(self):
        return (self.cx, self.y)

    @property
    def abajo(self):
        return (self.cx, self.y + self.h)

    @property
    def izq(self):
        return (self.x, self.cy)

    @property
    def der(self):
        return (self.x + self.w, self.cy)

    def en(self, lado: str, f: float = 0.5):
        """Punto sobre un lado a una fracción ``f`` (0 = inicio izquierdo/superior)."""
        if lado == "arriba":
            return (self.x + self.w * f, self.y)
        if lado == "abajo":
            return (self.x + self.w * f, self.y + self.h)
        if lado == "izq":
            return (self.x, self.y + self.h * f)
        return (self.x + self.w, self.y + self.h * f)


def _fuente(tam: float, negrita: bool = False, cursiva: bool = False) -> QFont:
    f = QFont(FUENTE)
    f.setPixelSize(max(1, round(tam)))
    f.setBold(negrita)
    f.setItalic(cursiva)
    return f


def _documento(html: str, ancho: float, tam: float, color: str, alinear: str) -> QTextDocument:
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    doc.setDefaultFont(_fuente(tam))
    doc.setDefaultStyleSheet(f"body {{ color: {color}; }} p {{ margin: 0; }} "
                             f"ul {{ margin: 0; -qt-list-indent: 0; }} li {{ margin-left: 12px; }}")
    doc.setHtml(f"<body><div align='{alinear}' style='color:{color}'>{html}</div></body>")
    doc.setTextWidth(ancho)
    return doc


class Lienzo:
    def __init__(self, ancho: float, alto: float):
        self.ancho, self.alto = ancho, alto
        self._ops = []

    # --- Primitivas ----------------------------------------------------------------------------

    def texto(self, x, y, ancho, html, *, tam=14, color=TINTA, alinear="left", alto=None) -> Rect:
        """Bloque de texto (HTML sencillo: <b>, <i>, <br>, <ul>). Con ``alto`` se centra en vertical."""
        doc = _documento(html, ancho, tam, color, alinear)
        h = doc.size().height()
        dy = (alto - h) / 2 if alto else 0

        def op(p: QPainter):
            p.save()
            p.translate(x, y + dy)
            doc.drawContents(p)
            p.restore()
        self._ops.append(op)
        return Rect(x, y, ancho, alto or h)

    def caja(self, x, y, w, h, html="", *, relleno=BLANCO, borde=LINEA, grosor=1.4, radio=6, tam=14,
             color=TINTA, alinear="center", discontinua=False, sombra=False, relleno_texto=8) -> Rect:
        def op(p: QPainter):
            if sombra:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 0, 0, 45))
                p.drawRoundedRect(QRectF(x + 4, y + 4, w, h), radio, radio)
            p.setPen(self._pluma(borde, grosor, discontinua))
            p.setBrush(QColor(relleno) if relleno else Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(x, y, w, h), radio, radio)
        self._ops.append(op)
        if html:
            self.texto(x + relleno_texto, y, w - 2 * relleno_texto, html, tam=tam, color=color, alinear=alinear,
                       alto=h)
        return Rect(x, y, w, h)

    def marco(self, x, y, w, h, titulo="", *, borde=GRIS, relleno=None, tam=13, color=GRIS, radio=10,
              discontinua=True) -> Rect:
        """Agrupación con borde (por defecto discontinuo) y un título arriba a la izquierda."""
        self.caja(x, y, w, h, relleno=relleno, borde=borde, grosor=1.2, radio=radio, discontinua=discontinua)
        if titulo:
            self.texto(x + 10, y + 6, w - 20, f"<b>{titulo}</b>", tam=tam, color=color)
        return Rect(x, y, w, h)

    def proceso_dfd(self, x, y, w, h, numero, html, *, relleno=AZUL_SUAVE, borde=AZUL, tam=14) -> Rect:
        """Proceso al estilo Gane-Sarson: rectángulo redondeado con el número en una franja superior."""
        franja = 22

        def op(p: QPainter):
            p.setPen(self._pluma(borde, 1.5))
            p.setBrush(QColor(relleno))
            p.drawRoundedRect(QRectF(x, y, w, h), 10, 10)
            p.drawLine(QPointF(x, y + franja), QPointF(x + w, y + franja))
        self._ops.append(op)
        self.texto(x, y + 3, w, f"<b>{numero}</b>", tam=tam - 1, color=borde, alinear="center")
        self.texto(x + 8, y + franja, w - 16, html, tam=tam, alinear="center", alto=h - franja)
        return Rect(x, y, w, h)

    def almacen(self, x, y, w, h, ident, html, *, relleno=GRIS_SUAVE, borde=LINEA, tam=14) -> Rect:
        """Almacén de datos (Gane-Sarson): rectángulo abierto a la derecha con el identificador."""
        celda = 34

        def op(p: QPainter):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(relleno))
            p.drawRect(QRectF(x, y, w, h))
            p.setPen(self._pluma(borde, 1.5))
            p.drawLine(QPointF(x + w, y), QPointF(x, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + h))
            p.drawLine(QPointF(x, y + h), QPointF(x + w, y + h))
            p.drawLine(QPointF(x + celda, y), QPointF(x + celda, y + h))
        self._ops.append(op)
        self.texto(x, y, celda, f"<b>{ident}</b>", tam=tam - 1, alinear="center", alto=h)
        self.texto(x + celda + 6, y, w - celda - 10, html, tam=tam, alinear="left", alto=h)
        return Rect(x, y, w, h)

    def entidad(self, x, y, w, h, html, *, relleno=GRIS_SUAVE, borde=LINEA, tam=14) -> Rect:
        """Entidad externa: rectángulo con sombra."""
        return self.caja(x, y, w, h, f"<b>{html}</b>", relleno=relleno, borde=borde, grosor=1.6, radio=2,
                         tam=tam, sombra=True)

    def cilindro(self, x, y, w, h, html, *, relleno=AZUL_SUAVE, borde=AZUL, tam=14) -> Rect:
        elipse = min(16, h / 4)

        def op(p: QPainter):
            p.setPen(self._pluma(borde, 1.5))
            p.setBrush(QColor(relleno))
            cuerpo = QPainterPath()
            cuerpo.moveTo(x, y + elipse / 2)
            cuerpo.lineTo(x, y + h - elipse / 2)
            cuerpo.arcTo(QRectF(x, y + h - elipse, w, elipse), 180, 180)
            cuerpo.lineTo(x + w, y + elipse / 2)
            cuerpo.arcTo(QRectF(x, y, w, elipse), 0, -180)
            p.drawPath(cuerpo)
            p.drawEllipse(QRectF(x, y, w, elipse))
        self._ops.append(op)
        self.texto(x + 6, y + elipse, w - 12, html, tam=tam, alinear="center", alto=h - elipse)
        return Rect(x, y, w, h)

    def circulo(self, cx, cy, r, html, *, relleno=AZUL_SUAVE, borde=AZUL, tam=15, grosor=2) -> Rect:
        def op(p: QPainter):
            p.setPen(self._pluma(borde, grosor))
            p.setBrush(QColor(relleno))
            p.drawEllipse(QPointF(cx, cy), r, r)
        self._ops.append(op)
        self.texto(cx - r * 0.8, cy - r, r * 1.6, html, tam=tam, alinear="center", alto=2 * r)
        return Rect(cx - r, cy - r, 2 * r, 2 * r)

    def insignia(self, cx, cy, texto, *, relleno=ROJO, color=BLANCO, r=11, tam=11) -> None:
        """Marca circular pequeña (p. ej. «P1» para señalar un problema)."""
        def op(p: QPainter):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(relleno))
            p.drawEllipse(QPointF(cx, cy), r, r)
            p.setPen(QColor(color))
            p.setFont(_fuente(tam, negrita=True))
            p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter, texto)
        self._ops.append(op)

    def rotulo_vertical(self, x, y, w, h, texto, *, relleno=None, color=None, tam=12) -> None:
        """Rótulo girado 90° (lectura de abajo arriba), centrado en el rectángulo dado."""
        color = color or GRIS

        def op(p: QPainter):
            if relleno:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(relleno))
                p.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
            p.save()
            p.translate(x + w / 2, y + h / 2)
            p.rotate(-90)
            p.setPen(QColor(color))
            p.setFont(_fuente(tam, negrita=True))
            p.drawText(QRectF(-h / 2, -w / 2, h, w), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, texto)
            p.restore()
        self._ops.append(op)

    def flecha_gruesa(self, x, y, w, h, *, relleno=GRIS_MEDIO) -> None:
        """Flecha ancha hacia la derecha (para esquemas de entrada → proceso → salida)."""
        def op(p: QPainter):
            punta = min(w * 0.45, h * 0.6)
            cuerpo = h * 0.5
            poli = QPolygonF([QPointF(x, y + (h - cuerpo) / 2), QPointF(x + w - punta, y + (h - cuerpo) / 2),
                              QPointF(x + w - punta, y), QPointF(x + w, y + h / 2), QPointF(x + w - punta, y + h),
                              QPointF(x + w - punta, y + (h + cuerpo) / 2), QPointF(x, y + (h + cuerpo) / 2)])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(relleno))
            p.drawPolygon(poli)
        self._ops.append(op)

    def linea(self, *puntos, color=LINEA, grosor=1.5, discontinua=False) -> None:
        def op(p: QPainter):
            p.setPen(self._pluma(color, grosor, discontinua))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(*q) for q in puntos]))
        self._ops.append(op)

    def flecha(self, *puntos, texto="", color=LINEA, grosor=1.5, discontinua=False, doble=False, tramo=None,
               tam=12, ancho_texto=150, desplazar=(0, 0), fondo_texto=BLANCO) -> None:
        """Flecha poligonal entre ``puntos``. La etiqueta va en el tramo ``tramo`` (por defecto el
        más largo), centrada y con fondo blanco."""
        puntos = [tuple(q) for q in puntos]

        def punta(p: QPainter, a, b):
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            largo, abertura = 10, 0.42
            poli = QPolygonF([QPointF(*b),
                              QPointF(b[0] - largo * math.cos(ang - abertura), b[1] - largo * math.sin(ang - abertura)),
                              QPointF(b[0] - largo * math.cos(ang + abertura), b[1] - largo * math.sin(ang + abertura))])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawPolygon(poli)

        def op(p: QPainter):
            p.setPen(self._pluma(color, grosor, discontinua))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(*q) for q in puntos]))
            punta(p, puntos[-2], puntos[-1])
            if doble:
                punta(p, puntos[1], puntos[0])
        self._ops.append(op)
        if texto:
            if tramo is None:
                tramo = max(range(len(puntos) - 1), key=lambda i: math.dist(puntos[i], puntos[i + 1]))
            a, b = puntos[tramo], puntos[tramo + 1]
            mx, my = (a[0] + b[0]) / 2 + desplazar[0], (a[1] + b[1]) / 2 + desplazar[1]
            self.etiqueta(mx, my, texto, tam=tam, ancho=ancho_texto, fondo=fondo_texto)

    def etiqueta(self, cx, cy, html, *, tam=12, ancho=150, color=TINTA, fondo=BLANCO) -> None:
        """Texto pequeño centrado en (cx, cy) con fondo, para rotular flechas."""
        doc = _documento(html, ancho, tam, color, "center")
        real = doc.idealWidth()
        doc.setTextWidth(real + 1)
        w, h = doc.size().width(), doc.size().height()

        def op(p: QPainter):
            if fondo:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(fondo))
                p.drawRoundedRect(QRectF(cx - w / 2 - 3, cy - h / 2 - 1, w + 6, h + 2), 3, 3)
            p.save()
            p.translate(cx - w / 2, cy - h / 2)
            doc.drawContents(p)
            p.restore()
        self._ops.append(op)

    # --- Salida --------------------------------------------------------------------------------

    @staticmethod
    def _pluma(color, grosor, discontinua=False) -> QPen:
        pluma = QPen(QColor(color), grosor)
        pluma.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
        if discontinua:
            pluma.setStyle(Qt.PenStyle.DashLine)
        return pluma

    def _pintar(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(QRectF(0, 0, self.ancho, self.alto), QBrush(QColor(BLANCO)))
        for op in self._ops:
            op(p)

    def guardar(self, nombre: str) -> Path:
        """Escribe ``<nombre>.png`` (300 ppp, ancho físico proporcional) y ``<nombre>.svg``."""
        SALIDA.mkdir(parents=True, exist_ok=True)
        imagen = QImage(round(self.ancho * PIXELES_POR_UNIDAD), round(self.alto * PIXELES_POR_UNIDAD),
                        QImage.Format.Format_ARGB32)
        puntos_por_metro = round(PIXELES_POR_UNIDAD * UNIDADES_POR_CM * 100)
        imagen.setDotsPerMeterX(puntos_por_metro)
        imagen.setDotsPerMeterY(puntos_por_metro)
        p = QPainter(imagen)
        p.scale(PIXELES_POR_UNIDAD, PIXELES_POR_UNIDAD)
        self._pintar(p)
        p.end()
        png = SALIDA / f"{nombre}.png"
        imagen.save(str(png))

        svg = QSvgGenerator()
        svg.setFileName(str(SALIDA / f"{nombre}.svg"))
        svg.setSize(QSize(round(self.ancho), round(self.alto)))
        svg.setViewBox(QRectF(0, 0, self.ancho, self.alto))
        svg.setTitle(nombre)
        p = QPainter(svg)
        self._pintar(p)
        p.end()
        return png
