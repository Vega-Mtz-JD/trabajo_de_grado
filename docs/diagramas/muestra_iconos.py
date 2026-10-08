"""Lámina de muestra de los iconos (no es una figura del informe)."""
from iconos import ICONOS
from lienzo import AZUL, AZUL_SUAVE, Lienzo

L = Lienzo(800, 60 + 90 * ((len(ICONOS) + 8) // 9))
for i, nombre in enumerate(ICONOS):
    x, y = 20 + (i % 9) * 86, 10 + (i // 9) * 90
    L.icono(nombre, x + 13, y, 52, color=AZUL, claro=AZUL_SUAVE)
    L.texto(x - 4, y + 58, 86, nombre, tam=11, alinear="center")
L.guardar("muestra_iconos")
