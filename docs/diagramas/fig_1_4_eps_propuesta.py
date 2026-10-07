"""Figura 1.4 — Esquema entrada–proceso–salida de la propuesta (VOTO SEGURO)."""

from lienzo import AZUL, AZUL_SUAVE, BLANCO, GRIS_MEDIO, GRIS_SUAVE, LINEA, TINTA, VERDE, VERDE_SUAVE, Lienzo

L = Lienzo(800, 520)
COLUMNAS = {"ENTRADA": (10, 200), "PROCESO · VOTO SEGURO": (255, 290), "SALIDA": (590, 200)}
for titulo, (x, w) in COLUMNAS.items():
    L.caja(x, 10, w, 34, f"<b>{titulo}</b>", relleno=TINTA, borde=TINTA, color=BLANCO, tam=15, radio=4)
    L.caja(x, 52, w, 372, relleno=GRIS_SUAVE, borde=GRIS_MEDIO, radio=6)

ALTO, PASO, Y0 = 42, 51, 62
entradas = ["Datos del votante:<br>CI, nombres y apellidos", "Fotografía y<br>huella dactilar",
            "Definición de la elección:<br>opciones, mesa y custodios", "Foto de hoy y huella<br>el día de la votación",
            "Selección del votante<br>en la cabina", "Partes de la clave de<br>3 de los 5 custodios",
            "Conteo del papel (VVPAT)<br>y frase del paquete"]
for i, t in enumerate(entradas):
    L.caja(22, Y0 + i * PASO, 176, ALTO, t, tam=12)

pasos = [("Configuración y claves de la elección", "O2"), ("Empadronamiento con foto y huella", "O1"),
         ("Apertura de la mesa y zerésima", None), ("Identificación biométrica 1:1", "O1"),
         ("Voto cifrado y comprobante impreso", "O2"), ("Cierre y escrutinio con custodios", "O2"),
         ("Exportación y auditoría triple", "O4")]
for i, (t, objetivo) in enumerate(pasos):
    y = Y0 + i * PASO
    r = L.caja(267, y, 266, ALTO, f"<b>{i + 1}.</b> {t}", relleno=AZUL_SUAVE, borde=AZUL, tam=13,
               alinear="left", relleno_texto=12)
    if i < len(pasos) - 1:
        L.flecha((r.cx, y + ALTO), (r.cx, y + PASO), grosor=1.3)
    if objetivo:
        L.insignia(r.x + r.w - 2, y + 2, objetivo, relleno=VERDE)

salidas = ["Constancia de<br>empadronamiento", "Zerésima firmada<br>(urna vacía)",
           "Comprobante en papel sin<br>hora ni datos del votante", "Actas de cierre y de<br>escrutinio firmadas",
           "Paquete de auditoría<br>cifrado (memoria USB)", "Hitos anclados en<br>Hyperledger Fabric",
           "Informe de verificación<br>(conforme / no conforme)"]
for i, t in enumerate(salidas):
    L.caja(602, Y0 + i * PASO, 176, ALTO, t, tam=12)

L.flecha_gruesa(212, 210, 40, 56, relleno=GRIS_MEDIO)
L.flecha_gruesa(547, 210, 40, 56, relleno=GRIS_MEDIO)

r = L.caja(10, 436, 780, 44, "<b>En todas las etapas:</b> bitácora encadenada con responsable y momento (O5) · "
           "base de datos PostgreSQL con auditoría pgaudit · anclaje de los hitos en Hyperledger Fabric (O3)",
           relleno=VERDE_SUAVE, borde=VERDE, tam=13)
L.insignia(r.x + 2, r.y + 2, "O5", relleno=VERDE)
L.texto(10, 490, 780, "<span style='color:#166534'>●</span> O1–O5: objetivos específicos (apartado 1.4.2) "
        "que atiende cada etapa.", tam=12)
L.guardar("fig_1_4_eps_propuesta")
