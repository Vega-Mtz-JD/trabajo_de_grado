"""Figura 1.1 — Esquema entrada–proceso–salida de la situación actual (votación manual)."""

from lienzo import (AMBAR, AZUL, AZUL_SUAVE, BLANCO, GRIS_MEDIO, GRIS_SUAVE, LINEA, ROJO, ROJO_SUAVE, TINTA,
                    Lienzo)

L = Lienzo(800, 500)
COLUMNAS = {"ENTRADA": (10, 200), "PROCESO": (255, 290), "SALIDA": (590, 200)}
for titulo, (x, w) in COLUMNAS.items():
    L.caja(x, 10, w, 34, f"<b>{titulo}</b>", relleno=TINTA, borde=TINTA, color=BLANCO, tam=15, radio=4)
    L.caja(x, 52, w, 352, relleno=GRIS_SUAVE, borde=GRIS_MEDIO, radio=6)

ALTO, PASO, Y0 = 52, 66, 64
entradas = ["Padrón de habilitados<br>en papel", "Cédulas de identidad<br>de los votantes", "Papeletas impresas",
            "Urna y material<br>electoral", "Jurados de mesa<br>y delegados"]
for i, t in enumerate(entradas):
    L.caja(22, Y0 + i * PASO, 176, ALTO, t, tam=13)

pasos = [("Identificación visual del votante<br>con su cédula", "P1"),
         ("Firma en la lista y entrega<br>de la papeleta", None),
         ("Voto en el recinto y depósito<br>de la papeleta en la urna", None),
         ("Conteo manual de las papeletas<br>al cierre de la jornada", "P2"),
         ("Llenado del acta en papel<br>y custodia del acta", "P3")]
for i, (t, problema) in enumerate(pasos):
    y = Y0 + i * PASO
    r = L.caja(267, y, 266, ALTO, f"<b>{i + 1}.</b> {t}", relleno=AZUL_SUAVE, borde=AZUL, tam=13,
               alinear="left", relleno_texto=12)
    if i < len(pasos) - 1:
        L.flecha((r.cx, y + ALTO), (r.cx, y + PASO), grosor=1.3)
    if problema:
        L.insignia(r.x + r.w - 2, y + 2, problema)

salidas = [("Acta de resultados<br>en papel", "P3"), ("Papeletas contadas", None),
           ("Lista firmada<br>de votantes", None), ("Resultados proclamados", None),
           ("Reclamos sin evidencia<br>independiente del acta", "P4")]
for i, (t, problema) in enumerate(salidas):
    rojo = problema == "P4"
    r = L.caja(602, Y0 + i * PASO, 176, ALTO, t, tam=13, relleno=ROJO_SUAVE if rojo else BLANCO,
               borde=ROJO if rojo else LINEA)
    if problema:
        L.insignia(r.x + r.w - 2, r.y + 2, problema)

L.flecha_gruesa(212, 200, 40, 56)
L.flecha_gruesa(547, 200, 40, 56)

# Problema transversal
r = L.caja(10, 416, 780, 40, "<b>En ninguna etapa</b> se registra de forma sistemática quién intervino ni cuándo: "
           "no es posible una auditoría posterior.", relleno=ROJO_SUAVE, borde=ROJO, tam=13, discontinua=True)
L.insignia(r.x + 2, r.y + 2, "P5")
L.texto(10, 466, 780, "<span style='color:#b91c1c'>●</span> P1–P5: procesos en los que se originan los problemas "
        "secundarios descritos en el apartado 1.3.3.", tam=12, color=TINTA)
L.guardar("fig_1_1_eps_situacion_actual")
