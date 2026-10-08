"""Figura 1.1 — Esquema entrada–proceso–salida de la situación actual (votación manual).

Genera la versión sobria y la ilustrada (con iconos)."""

from lienzo import (AZUL, AZUL_SUAVE, BLANCO, GRIS_MEDIO, GRIS_SUAVE, LINEA, ROJO, ROJO_SUAVE, TINTA, Lienzo,
                    colores_icono)


def dibujar(ilustrada: bool) -> None:
    L = Lienzo(800, 500, ilustrada)
    columnas = {"ENTRADA": (10, 200, "lista"), "PROCESO": (255, 290, "engranaje"), "SALIDA": (590, 200, "acta")}
    for titulo, (x, w, icono) in columnas.items():
        L.caja(x, 10, w, 34, f"<b>{titulo}</b>", relleno=TINTA, borde=TINTA, color=BLANCO, tam=15, radio=4)
        if ilustrada:
            L.icono(icono, x + 12, 15, 24, color=BLANCO, claro=TINTA)
        L.caja(x, 52, w, 352, relleno=GRIS_SUAVE, borde=GRIS_MEDIO, radio=6)

    alto, paso, y0 = 52, 66, 64
    entradas = [("Padrón de habilitados<br>en papel", "lista"), ("Cédulas de identidad<br>de los votantes", "cedula"),
                ("Papeletas impresas", "papeleta"), ("Urna y material<br>electoral", "urna"),
                ("Jurados de mesa<br>y delegados", "grupo")]
    lateral = dict(tam=12, icono_tam=28) if ilustrada else dict(tam=13)

    def texto_lateral(t):            # con icono, el texto se acomoda solo en el espacio que queda
        return t.replace("<br>", " ") if ilustrada else t

    for i, (t, icono) in enumerate(entradas):
        c, s = colores_icono(icono)
        L.caja(22, y0 + i * paso, 176, alto, texto_lateral(t), icono=icono, icono_color=c, icono_claro=s, **lateral)

    pasos = [("Identificación visual del votante<br>con su cédula", "P1", "lupa"),
             ("Firma en la lista y entrega<br>de la papeleta", None, "firma"),
             ("Voto en el recinto y depósito<br>de la papeleta en la urna", None, "urna"),
             ("Conteo manual de las papeletas<br>al cierre de la jornada", "P2", "conteo"),
             ("Llenado del acta en papel<br>y custodia del acta", "P3", "acta")]
    for i, (t, problema, icono) in enumerate(pasos):
        y = y0 + i * paso
        c, s = colores_icono(icono)
        r = L.caja(267, y, 266, alto, f"<b>{i + 1}.</b> {t}", relleno=AZUL_SUAVE, borde=AZUL, tam=13,
                   alinear="left", relleno_texto=12, icono=icono, icono_color=c, icono_claro=BLANCO)
        if i < len(pasos) - 1:
            L.flecha((r.cx, y + alto), (r.cx, y + paso), grosor=1.3)
        if problema:
            L.insignia(r.x + r.w - 2, y + 2, problema)

    salidas = [("Acta de resultados<br>en papel", "P3", "acta"), ("Papeletas contadas", None, "papeleta"),
               ("Lista firmada<br>de votantes", None, "lista"), ("Resultados proclamados", None, "resultados"),
               ("Reclamos sin evidencia<br>independiente del acta", "P4", "alerta")]
    for i, (t, problema, icono) in enumerate(salidas):
        rojo = problema == "P4"
        c, s = colores_icono(icono)
        r = L.caja(602, y0 + i * paso, 176, alto, texto_lateral(t), relleno=ROJO_SUAVE if rojo else BLANCO,
                   borde=ROJO if rojo else LINEA, icono=icono, icono_color=c, icono_claro=BLANCO if rojo else s,
                   **lateral)
        if problema:
            L.insignia(r.x + r.w - 2, r.y + 2, problema)

    L.flecha_gruesa(212, 200, 40, 56)
    L.flecha_gruesa(547, 200, 40, 56)

    r = L.caja(10, 416, 780, 40, "<b>En ninguna etapa</b> se registra de forma sistemática quién intervino ni "
               "cuándo: no es posible una auditoría posterior.", relleno=ROJO_SUAVE, borde=ROJO, tam=13,
               discontinua=True, icono="reloj", icono_tam=28, icono_color=ROJO)
    L.insignia(r.x + 2, r.y + 2, "P5")
    L.texto(10, 466, 780, "<span style='color:#b91c1c'>●</span> P1–P5: procesos en los que se originan los "
            "problemas secundarios descritos en el apartado 1.3.3.", tam=12, color=TINTA)
    L.guardar("fig_1_1_eps_situacion_actual")


for ilustrada in (False, True):
    dibujar(ilustrada)
