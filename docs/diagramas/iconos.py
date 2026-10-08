"""Iconos vectoriales para las figuras ilustradas (estilo plano de dos tonos).

Cada icono se dibuja en una caja de 100 × 100 unidades con un color principal (trazo y
detalles) y un tono claro de relleno; ``dibujar`` lo escala a la posición y tamaño pedidos.
Se dibujan con QPainter, así que se exportan igual a PNG y a SVG y no dependen de fuentes.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

BLANCO = QColor("#ffffff")


def _pluma(c: QColor, g: float = 6) -> QPen:
    pluma = QPen(c, g)
    pluma.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pluma


def _trazo(p, c, s=None, g=6):
    p.setPen(_pluma(c, g))
    p.setBrush(s if s is not None else Qt.BrushStyle.NoBrush)


def _lineas(p, c, filas, x0, x1, g=5):
    p.setPen(_pluma(c, g))
    for y, largo in filas:
        p.drawLine(QPointF(x0, y), QPointF(x0 + (x1 - x0) * largo, y))


# --- Personas ----------------------------------------------------------------------------------

def persona(p, c, s):
    _trazo(p, c, s)
    p.drawEllipse(QPointF(50, 30), 17, 17)
    cuerpo = QPainterPath()
    cuerpo.moveTo(16, 92)
    cuerpo.cubicTo(16, 56, 84, 56, 84, 92)
    cuerpo.closeSubpath()
    p.drawPath(cuerpo)


def grupo(p, c, s):
    for dx in (-24, 24):
        p.save()
        p.translate(50 + dx, 18)
        p.scale(0.62, 0.62)
        p.translate(-50, 0)
        persona(p, c, s)
        p.restore()
    p.save()
    p.translate(50, 22)
    p.scale(0.8, 0.8)
    p.translate(-50, 0)
    persona(p, c, BLANCO)
    persona(p, c, s)
    p.restore()


def operador(p, c, s):
    persona(p, c, s)
    _trazo(p, c, BLANCO, 5)                       # credencial colgada
    p.drawRoundedRect(QRectF(56, 66, 18, 22), 3, 3)
    p.drawLine(QPointF(65, 66), QPointF(58, 52))


def custodio(p, c, s):
    p.save()
    p.translate(-8, 0)
    persona(p, c, s)
    p.restore()
    p.save()
    p.translate(52, 52)
    p.scale(0.48, 0.48)
    _circulo_fondo(p, c)
    llave(p, BLANCO, c)
    p.restore()


def observador(p, c, s):
    p.save()
    p.translate(-8, 0)
    persona(p, c, s)
    p.restore()
    p.save()
    p.translate(50, 50)
    p.scale(0.5, 0.5)
    _circulo_fondo(p, c)
    lupa(p, BLANCO, c)
    p.restore()


def _circulo_fondo(p, c):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QRectF(0, 0, 100, 100))


# --- Documentos --------------------------------------------------------------------------------

def _hoja(p, c, s):
    _trazo(p, c, s)
    hoja = QPolygonF([QPointF(20, 8), QPointF(64, 8), QPointF(82, 26), QPointF(82, 92), QPointF(20, 92)])
    p.drawPolygon(hoja)
    p.drawPolyline(QPolygonF([QPointF(64, 8), QPointF(64, 26), QPointF(82, 26)]))


def documento(p, c, s):
    _hoja(p, c, s)
    _lineas(p, c, [(42, 1), (56, 1), (70, 0.7)], 32, 70)


def papeleta(p, c, s):
    _hoja(p, c, s)
    _trazo(p, c, BLANCO, 5)
    p.drawRect(QRectF(30, 36, 14, 14))
    p.drawRect(QRectF(30, 62, 14, 14))
    p.setPen(_pluma(c, 6))
    p.drawPolyline(QPolygonF([QPointF(32, 43), QPointF(37, 48), QPointF(46, 34)]))
    _lineas(p, c, [(43, 1), (69, 0.8)], 52, 72)


def acta(p, c, s):
    _hoja(p, c, s)
    _lineas(p, c, [(36, 1), (48, 1), (60, 0.5)], 32, 70)
    _trazo(p, c, c, 3)                            # sello
    p.drawEllipse(QPointF(64, 74), 12, 12)
    p.setPen(_pluma(BLANCO, 3))
    p.drawEllipse(QPointF(64, 74), 6, 6)


def firma(p, c, s):
    _hoja(p, c, s)
    _lineas(p, c, [(36, 1), (48, 0.8)], 32, 70)
    p.setPen(_pluma(c, 4))
    trazo = QPainterPath()
    trazo.moveTo(30, 74)
    trazo.cubicTo(36, 60, 42, 84, 48, 70)
    trazo.cubicTo(52, 62, 56, 80, 70, 70)
    p.drawPath(trazo)


def lista(p, c, s):
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(18, 14, 64, 80), 6, 6)
    _trazo(p, c, c)
    p.drawRoundedRect(QRectF(36, 6, 28, 16), 4, 4)
    for y in (38, 56, 74):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QPointF(32, y), 4, 4)
    _lineas(p, c, [(38, 1), (56, 1), (74, 0.7)], 42, 70)


def cedula(p, c, s):
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(6, 22, 88, 58), 8, 8)
    _trazo(p, c, BLANCO, 4)
    p.drawRoundedRect(QRectF(14, 32, 28, 36), 4, 4)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(28, 45), 6, 6)
    p.drawChord(QRectF(18, 52, 20, 20), 0, 180 * 16)
    _lineas(p, c, [(40, 1), (52, 0.8), (64, 0.6)], 50, 86)


def conteo(p, c, s):
    _hoja(p, c, s)
    p.setPen(_pluma(c, 5))
    for x in (32, 41, 50, 59):
        p.drawLine(QPointF(x, 40), QPointF(x, 70))
    p.drawLine(QPointF(27, 66), QPointF(66, 44))


def bitacora(p, c, s):
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(18, 8, 62, 84), 5, 5)
    p.drawLine(QPointF(30, 8), QPointF(30, 92))
    _lineas(p, c, [(28, 1), (42, 1), (56, 0.7)], 40, 70)
    p.save()
    p.translate(46, 62)
    p.scale(0.42, 0.42)
    cadena(p, c, BLANCO)
    p.restore()


# --- Votación ----------------------------------------------------------------------------------

def urna(p, c, s):
    _trazo(p, c, BLANCO, 5)                       # papeleta entrando
    p.drawRect(QRectF(38, 8, 24, 34))
    p.setPen(_pluma(c, 5))
    p.drawPolyline(QPolygonF([QPointF(43, 22), QPointF(48, 28), QPointF(57, 16)]))
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(12, 40, 76, 52), 6, 6)
    p.setPen(_pluma(c, 8))
    p.drawLine(QPointF(32, 40), QPointF(68, 40))
    _lineas(p, c, [(66, 1)], 34, 66)


def cabina(p, c, s):
    monitor(p, c, s)
    p.setPen(_pluma(c, 7))
    p.drawPolyline(QPolygonF([QPointF(36, 40), QPointF(46, 50), QPointF(64, 30)]))


def monitor(p, c, s):
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(8, 12, 84, 56), 6, 6)
    p.setPen(_pluma(c, 6))
    p.drawLine(QPointF(50, 68), QPointF(50, 82))
    p.drawLine(QPointF(30, 86), QPointF(70, 86))


def huella(p, c, s):
    _trazo(p, c, s, 0.1)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(s)
    p.drawEllipse(QRectF(10, 4, 80, 92))
    p.setPen(_pluma(c, 5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(6):
        m = 14 + i * 7
        p.drawArc(QRectF(m, m - 6, 100 - 2 * m, 104 - 2 * m), 290 * 16, 320 * 16)


def camara(p, c, s):
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(8, 30, 84, 56), 8, 8)
    p.drawRoundedRect(QRectF(32, 18, 30, 16), 4, 4)
    _trazo(p, c, BLANCO)
    p.drawEllipse(QPointF(50, 58), 18, 18)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(50, 58), 8, 8)
    p.drawEllipse(QPointF(78, 42), 4, 4)


def impresora(p, c, s):
    _trazo(p, c, BLANCO, 5)
    p.drawRect(QRectF(28, 8, 44, 26))
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(8, 32, 84, 38), 8, 8)
    _trazo(p, c, BLANCO, 5)
    p.drawRect(QRectF(26, 56, 48, 36))
    _lineas(p, c, [(68, 1), (80, 0.6)], 34, 66)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(80, 44), 4, 4)


def comprobante(p, c, s):
    _trazo(p, c, s)
    tira = QPainterPath()
    tira.moveTo(26, 8)
    tira.lineTo(74, 8)
    tira.lineTo(74, 86)
    for i in range(6):                            # borde cortado en zigzag
        tira.lineTo(74 - 8 * i - 4, 92)
        tira.lineTo(74 - 8 * (i + 1), 86)
    tira.closeSubpath()
    p.drawPath(tira)
    _lineas(p, c, [(24, 1), (36, 0.7)], 34, 66)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    for i in range(4):                            # código QR esquemático
        for j in range(4):
            if (i + j) % 2 == 0 or i == j:
                p.drawRect(QRectF(36 + i * 7, 50 + j * 7, 6, 6))


def resultados(p, c, s):
    _trazo(p, c, s)
    for x, h in ((14, 34), (40, 60), (66, 46)):
        p.drawRoundedRect(QRectF(x, 88 - h, 20, h), 3, 3)
    p.setPen(_pluma(c, 6))
    p.drawLine(QPointF(8, 90), QPointF(92, 90))


# --- Seguridad y datos -------------------------------------------------------------------------

def candado(p, c, s):
    _trazo(p, c, None, 8)
    p.drawArc(QRectF(28, 10, 44, 50), 0, 180 * 16)
    p.drawLine(QPointF(28, 35), QPointF(28, 46))
    p.drawLine(QPointF(72, 35), QPointF(72, 46))
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(16, 44, 68, 48), 8, 8)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(50, 62), 7, 7)
    p.drawRect(QRectF(47, 62, 6, 16))


def llave(p, c, s):
    _trazo(p, c, s, 7)
    p.drawEllipse(QPointF(30, 50), 18, 18)
    p.setPen(_pluma(c, 9))
    p.drawLine(QPointF(48, 50), QPointF(90, 50))
    p.drawLine(QPointF(78, 50), QPointF(78, 64))
    p.drawLine(QPointF(88, 50), QPointF(88, 60))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(30, 50), 6, 6)


def escudo(p, c, s):
    _trazo(p, c, s)
    forma = QPainterPath()
    forma.moveTo(50, 6)
    forma.lineTo(86, 20)
    forma.cubicTo(86, 60, 70, 82, 50, 94)
    forma.cubicTo(30, 82, 14, 60, 14, 20)
    forma.closeSubpath()
    p.drawPath(forma)
    p.setPen(_pluma(c, 8))
    p.drawPolyline(QPolygonF([QPointF(34, 50), QPointF(46, 62), QPointF(68, 38)]))


def base_datos(p, c, s):
    _trazo(p, c, s)
    cuerpo = QPainterPath()
    cuerpo.moveTo(16, 20)
    cuerpo.lineTo(16, 80)
    cuerpo.arcTo(QRectF(16, 70, 68, 20), 180, 180)
    cuerpo.lineTo(84, 20)
    cuerpo.closeSubpath()
    p.drawPath(cuerpo)
    _trazo(p, c)
    for y in (38, 56):
        p.drawArc(QRectF(16, y, 68, 20), 180 * 16, 180 * 16)
    _trazo(p, c, BLANCO)
    p.drawEllipse(QRectF(16, 10, 68, 20))


def cadena(p, c, s):
    """Bloques encadenados (cadena de bloques)."""
    for i, x in enumerate((4, 38, 72)):
        _trazo(p, c, s if i != 1 else BLANCO, 5)
        p.drawRoundedRect(QRectF(x, 36, 24, 28), 4, 4)
    p.setPen(_pluma(c, 5))
    p.drawLine(QPointF(28, 50), QPointF(38, 50))
    p.drawLine(QPointF(62, 50), QPointF(72, 50))


def usb(p, c, s):
    _trazo(p, c, BLANCO, 5)
    p.drawRect(QRectF(38, 8, 24, 22))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawRect(QRectF(43, 14, 5, 6))
    p.drawRect(QRectF(52, 14, 5, 6))
    _trazo(p, c, s)
    p.drawRoundedRect(QRectF(30, 30, 40, 62), 8, 8)
    candado_mini = QRectF(42, 58, 16, 14)
    p.setPen(_pluma(c, 4))
    p.setBrush(c)
    p.drawRoundedRect(candado_mini, 2, 2)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(44, 48, 12, 16), 0, 180 * 16)


def lupa(p, c, s):
    _trazo(p, c, s, 8)
    p.drawEllipse(QPointF(42, 42), 26, 26)
    p.setPen(_pluma(c, 12))
    p.drawLine(QPointF(62, 62), QPointF(88, 88))


def engranaje(p, c, s):
    _trazo(p, c, s, 5)
    contorno = QPolygonF()
    dientes = 8
    for i in range(dientes * 4):
        ang = 2 * math.pi * i / (dientes * 4)
        r = 44 if (i % 4) in (0, 1) else 34
        contorno.append(QPointF(50 + r * math.cos(ang), 50 + r * math.sin(ang)))
    p.drawPolygon(contorno)
    _trazo(p, c, BLANCO, 5)
    p.drawEllipse(QPointF(50, 50), 13, 13)


def reloj(p, c, s):
    _trazo(p, c, s)
    p.drawEllipse(QPointF(50, 52), 38, 38)
    p.setPen(_pluma(c, 7))
    p.drawLine(QPointF(50, 52), QPointF(50, 28))
    p.drawLine(QPointF(50, 52), QPointF(68, 62))


def alerta(p, c, s):
    _trazo(p, c, s)
    p.drawPolygon(QPolygonF([QPointF(50, 8), QPointF(94, 88), QPointF(6, 88)]))
    p.setPen(_pluma(c, 9))
    p.drawLine(QPointF(50, 36), QPointF(50, 62))
    p.drawPoint(QPointF(50, 76))


def correcto(p, c, s):
    _trazo(p, c, s)
    p.drawEllipse(QPointF(50, 50), 42, 42)
    p.setPen(_pluma(c, 9))
    p.drawPolyline(QPolygonF([QPointF(30, 52), QPointF(44, 66), QPointF(70, 36)]))


def incorrecto(p, c, s):
    _trazo(p, c, s)
    p.drawEllipse(QPointF(50, 50), 42, 42)
    p.setPen(_pluma(c, 9))
    p.drawLine(QPointF(34, 34), QPointF(66, 66))
    p.drawLine(QPointF(66, 34), QPointF(34, 66))


def sin_red(p, c, s):
    p.setPen(_pluma(c, 7))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for r in (40, 27, 14):
        p.drawArc(QRectF(50 - r, 70 - r, 2 * r, 2 * r), 45 * 16, 90 * 16)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(50, 70), 6, 6)
    p.setPen(_pluma(QColor("#b91c1c"), 8))
    p.drawLine(QPointF(18, 18), QPointF(82, 86))


def mesa(p, c, s):
    """Mesa de votación con urna y persona (jurado)."""
    p.save()
    p.translate(0, -4)
    p.scale(0.55, 0.55)
    persona(p, c, s)
    p.restore()
    p.save()
    p.translate(48, 18)
    p.scale(0.5, 0.5)
    urna(p, c, s)
    p.restore()
    _trazo(p, c, s, 6)
    p.drawRect(QRectF(6, 64, 88, 10))
    p.drawLine(QPointF(16, 74), QPointF(16, 94))
    p.drawLine(QPointF(84, 74), QPointF(84, 94))


ICONOS = {f.__name__: f for f in (
    persona, grupo, operador, custodio, observador, documento, papeleta, acta, firma, lista, cedula, conteo,
    bitacora, urna, cabina, monitor, huella, camara, impresora, comprobante, resultados, candado, llave,
    escudo, base_datos, cadena, usb, lupa, engranaje, reloj, alerta, correcto, incorrecto, sin_red, mesa)}


def dibujar(p: QPainter, nombre: str, x: float, y: float, tam: float, color: str, claro: str) -> None:
    p.save()
    p.translate(x, y)
    p.scale(tam / 100, tam / 100)
    ICONOS[nombre](p, QColor(color), QColor(claro))
    p.restore()
