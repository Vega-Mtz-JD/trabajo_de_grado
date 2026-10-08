"""Figura 1.4 — Esquema entrada–proceso–salida de la propuesta (VOTO SEGURO), sobria e ilustrada."""

from lienzo import (AZUL, AZUL_SUAVE, BLANCO, GRIS_MEDIO, GRIS_SUAVE, TINTA, VERDE, VERDE_SUAVE, Lienzo,
                    colores_icono)


def dibujar(ilustrada: bool) -> None:
    L = Lienzo(800, 520, ilustrada)
    columnas = {"ENTRADA": (10, 200, "lista"), "PROCESO · VOTO SEGURO": (255, 290, "cabina"),
                "SALIDA": (590, 200, "acta")}
    for titulo, (x, w, icono) in columnas.items():
        L.caja(x, 10, w, 34, f"<b>{titulo}</b>", relleno=TINTA, borde=TINTA, color=BLANCO, tam=15, radio=4)
        if ilustrada:
            L.icono(icono, x + 12, 15, 24, color=BLANCO, claro=TINTA)
        L.caja(x, 52, w, 372, relleno=GRIS_SUAVE, borde=GRIS_MEDIO, radio=6)

    alto, paso, y0 = 42, 51, 62
    lateral = dict(tam=11, icono_tam=26) if ilustrada else dict(tam=12)

    def texto_lateral(t):
        return t.replace("<br>", " ") if ilustrada else t

    entradas = [("Datos del votante:<br>CI, nombres y apellidos", "cedula"),
                ("Fotografía y<br>huella dactilar", "camara"),
                ("Definición de la elección:<br>opciones, mesa y custodios", "engranaje"),
                ("Foto de hoy y huella<br>el día de la votación", "huella"),
                ("Selección del votante<br>en la cabina", "cabina"),
                ("Partes de la clave de<br>3 de los 5 custodios", "llave"),
                ("Conteo del papel (VVPAT)<br>y frase del paquete", "comprobante")]
    for i, (t, icono) in enumerate(entradas):
        c, s = colores_icono(icono)
        L.caja(22, y0 + i * paso, 176, alto, texto_lateral(t), icono=icono, icono_color=c, icono_claro=s, **lateral)

    pasos = [("Configuración y claves de la elección", "O2", "llave"),
             ("Empadronamiento con foto y huella", "O1", "camara"),
             ("Apertura de la mesa y zerésima", None, "acta"),
             ("Identificación biométrica 1:1", "O1", "huella"),
             ("Voto cifrado y comprobante impreso", "O2", "candado"),
             ("Cierre y escrutinio con custodios", "O2", "custodio"),
             ("Exportación y auditoría triple", "O4", "usb")]
    for i, (t, objetivo, icono) in enumerate(pasos):
        y = y0 + i * paso
        c, _s = colores_icono(icono)
        r = L.caja(267, y, 266, alto, f"<b>{i + 1}.</b> {t}", relleno=AZUL_SUAVE, borde=AZUL, tam=13,
                   alinear="left", relleno_texto=12, icono=icono, icono_color=c, icono_claro=BLANCO, icono_tam=28)
        if i < len(pasos) - 1:
            L.flecha((r.cx, y + alto), (r.cx, y + paso), grosor=1.3)
        if objetivo:
            L.insignia(r.x + r.w - 2, y + 2, objetivo, relleno=VERDE)

    salidas = [("Constancia de<br>empadronamiento", "documento"), ("Zerésima firmada<br>(urna vacía)", "acta"),
               ("Comprobante en papel sin<br>hora ni datos del votante", "comprobante"),
               ("Actas de cierre y de<br>escrutinio firmadas", "firma"),
               ("Paquete de auditoría<br>cifrado (memoria USB)", "usb"),
               ("Hitos anclados en<br>Hyperledger Fabric", "cadena"),
               ("Informe de verificación<br>(conforme / no conforme)", "correcto")]
    for i, (t, icono) in enumerate(salidas):
        c, s = colores_icono(icono)
        L.caja(602, y0 + i * paso, 176, alto, texto_lateral(t), icono=icono, icono_color=c, icono_claro=s, **lateral)

    L.flecha_gruesa(212, 210, 40, 56, relleno=GRIS_MEDIO)
    L.flecha_gruesa(547, 210, 40, 56, relleno=GRIS_MEDIO)

    r = L.caja(10, 436, 780, 44, "<b>En todas las etapas:</b> bitácora encadenada con responsable y momento (O5) · "
               "base de datos PostgreSQL con auditoría pgaudit · anclaje de los hitos en Hyperledger Fabric (O3)",
               relleno=VERDE_SUAVE, borde=VERDE, tam=13, icono="bitacora", icono_tam=30, icono_color=VERDE)
    L.insignia(r.x + 2, r.y + 2, "O5", relleno=VERDE)
    L.texto(10, 490, 780, "<span style='color:#166534'>●</span> O1–O5: objetivos específicos (apartado 1.4.2) "
            "que atiende cada etapa.", tam=12)
    L.guardar("fig_1_4_eps_propuesta")


for ilustrada in (False, True):
    dibujar(ilustrada)
