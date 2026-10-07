"""Árbol de problemas / árbol de objetivos (misma geometría, para que uno sea el espejo del otro)."""

from lienzo import BLANCO, GRIS_SUAVE, Lienzo

ANCHO_COL, SEP, X0 = 140, 11, 46


def dibujar(nombre, *, final, efectos, central, base, colores, marcas, titulos):
    """``colores`` = (final, efectos, central, base) como pares (relleno, borde); el central
    lleva texto blanco. ``titulos`` = rótulos de las cuatro filas, de arriba abajo."""
    L = Lienzo(800, 500)
    (rf, bf), (re_, be), (rc, bc), (rb, bb) = colores
    filas = {"final": (10, 50), "efectos": (100, 80), "central": (230, 84), "base": (364, 110)}
    for (y, h), titulo in zip(filas.values(), titulos):
        L.rotulo_vertical(4, y, 32, h, titulo, relleno=GRIS_SUAVE, tam=10)

    ancho_total = 5 * ANCHO_COL + 4 * SEP
    yf, hf = filas["final"]
    f = L.caja(X0, yf, ancho_total, hf, f"<b>{final}</b>", relleno=rf, borde=bf, tam=15)
    yc, hc = filas["central"]
    c = L.caja(X0, yc, ancho_total, hc, central, relleno=rc, borde=bc, color=BLANCO, tam=14, grosor=1.6)
    for i, (efecto, causa) in enumerate(zip(efectos, base)):
        x = X0 + i * (ANCHO_COL + SEP)
        e = L.caja(x, filas["efectos"][0], ANCHO_COL, filas["efectos"][1], efecto, relleno=re_, borde=be, tam=13)
        b = L.caja(x, filas["base"][0], ANCHO_COL, filas["base"][1], causa, relleno=rb, borde=bb, tam=13)
        L.insignia(b.x + 14, b.y + 2, f"{marcas}{i + 1}", relleno=bb)
        L.flecha(b.arriba, (b.cx, c.y + c.h), grosor=1.3)
        L.flecha((e.cx, c.y), e.abajo, grosor=1.3)
        L.flecha(e.arriba, (e.cx, f.y + f.h), grosor=1.3)
    return L.guardar(nombre)
