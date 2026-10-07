"""Figura 1.5 — Diagrama de contexto (DFD de nivel 0) del sistema propuesto."""

import math

from lienzo import AZUL, AZUL_SUAVE, GRIS, Lienzo, VERDE, VERDE_SUAVE

L = Lienzo(800, 530)
CX, CY, R = 400, 250, 92
L.circulo(CX, CY, R, "<b>0</b><br><b>VOTO SEGURO</b><br>sistema de votación<br>electrónica offline",
          relleno=AZUL_SUAVE, borde=AZUL, tam=14)

W, H = 150, 62
entidades = {
    "admin": (10, 20, "Administrador<br>(comité electoral)"),
    "operador": (10, 219, "Operador<br>de mesa"),
    "votante": (10, 418, "Votante"),
    "custodios": (640, 20, "Custodios<br>de la clave"),
    "auditor": (640, 219, "Auditor y<br>delegados"),
    "fabric": (640, 418, "Red Hyperledger<br>Fabric"),
}
rects = {}
for clave, (x, y, texto) in entidades.items():
    if clave == "fabric":
        rects[clave] = L.cilindro(x, y - 4, W, H + 8, f"<b>{texto}</b>", relleno=VERDE_SUAVE, borde=VERDE)
    else:
        rects[clave] = L.entidad(x, y, W, H, texto)


def horizontal(clave, entra, sale, rotulo=24):
    """Entidad a la izquierda o derecha del círculo: dos flujos horizontales."""
    r = rects[clave]
    izquierda = r.x < CX
    borde_e = r.x + r.w if izquierda else r.x
    for dy, texto, hacia_sistema in ((-12, sale, False), (12, entra, True)):
        y = CY + dy
        borde_c = CX + (-1 if izquierda else 1) * math.sqrt(R * R - dy * dy)
        a, b = (borde_e, y), (borde_c, y)
        L.flecha(*((a, b) if hacia_sistema else (b, a)), grosor=1.4)
        L.etiqueta((a[0] + b[0]) / 2, y + (-rotulo if dy < 0 else rotulo), texto, tam=12, ancho=170)


def esquina(clave, entra, sale):
    """Entidad en una esquina: dos conectores en ángulo recto que llegan al círculo por arriba o abajo."""
    r = rects[clave]
    izquierda, arriba = r.x < CX, r.y < CY
    borde_e = r.x + r.w if izquierda else r.x
    lado = -1 if izquierda else 1
    vert = -1 if arriba else 1
    # externo: más lejos de la entidad en vertical; interno: más cerca
    filas = (r.y + 16, r.y + r.h - 16) if arriba else (r.y + r.h - 16, r.y + 16)
    columnas = (CX + lado * 30, CX + lado * 55)
    for (y, x, texto, hacia_sistema, desplazar) in (
            (filas[0], columnas[0], entra if arriba else sale, arriba, -18 * (1 if arriba else -1)),
            (filas[1], columnas[1], sale if arriba else entra, not arriba, 18 * (1 if arriba else -1))):
        y_circulo = CY + vert * math.sqrt(R * R - (x - CX) ** 2)
        puntos = [(borde_e, y), (x, y), (x, y_circulo)]
        L.flecha(*(puntos if hacia_sistema else puntos[::-1]), grosor=1.4)
        ancho = 200 if x == columnas[0] else 165       # el rótulo cabe entre la entidad y la línea vertical
        L.etiqueta((borde_e + x) / 2, y + desplazar * (1.0 if x == columnas[0] else 1.4), texto, tam=12, ancho=ancho)


esquina("admin", "Definición de la elección y usuarios", "Hojas de los custodios<br>(partes con QR)")
horizontal("operador", "CI, foto y huella;<br>apertura y cierre", "Constancias, zerésima<br>y actas firmadas")
esquina("votante", "CI, huella, foto de hoy<br>y selección del voto", "Comprobante impreso (VVPAT)")
esquina("custodios", "3 de 5 partes para el escrutinio", "Parte de la clave<br>(una por custodio)")
horizontal("auditor", "Paquete USB, frase<br>y conteo del papel", "Informe de<br>verificación triple")
esquina("fabric", "Historial del ledger<br>para la auditoría", "Hitos: hashes, conteos<br>y raíz de Merkle")
L.texto(100, 508, 600, "Sin conexión a Internet: todos los intercambios son locales, en papel o por memoria USB.",
        tam=11, color=GRIS, alinear="center")
L.guardar("fig_1_5_contexto_propuesto")
