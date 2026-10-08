"""Figura 1.2 — DFD de contexto (nivel 0) de la situación actual (versión sobria e ilustrada)."""

from lienzo import AMBAR, AMBAR_SUAVE, Lienzo, colores_icono


def dibujar(ilustrada: bool) -> None:
    L = Lienzo(800, 330, ilustrada)
    L.proceso_dfd(320, 30, 160, 130, "0", "<b>Proceso de votación manual</b><br>de [EMPRESA]",
                  relleno=AMBAR_SUAVE, borde=AMBAR, tam=15 if not ilustrada else 14, icono="urna")
    for x, y, w, h, texto, icono in ((10, 60, 140, 70, "Comité<br>electoral", "grupo"),
                                     (650, 60, 140, 70, "Votante", "persona"),
                                     (325, 235, 150, 60, "Delegados de<br>los frentes", "observador")):
        L.entidad(x, y, w, h, texto, icono=icono, icono_color=colores_icono(icono)[0])

    L.flecha((150, 75), (320, 75), texto="Padrón, papeletas<br>y convocatoria", desplazar=(0, -22))
    L.flecha((320, 115), (150, 115), texto="Acta de resultados, lista<br>firmada y papeletas contadas",
             desplazar=(0, 24), ancho_texto=170)
    L.flecha((650, 75), (480, 75), texto="Cédula de identidad<br>y papeleta marcada", desplazar=(0, -22))
    L.flecha((480, 115), (650, 115), texto="Papeleta en blanco", desplazar=(0, 16))
    L.flecha((370, 235), (370, 160), texto="Observaciones<br>y reclamos", desplazar=(-62, 0))
    L.flecha((430, 160), (430, 235), texto="Copia<br>del acta", desplazar=(42, 0))
    L.texto(10, 262, 300, "<b>Notación Gane-Sarson</b><br>□ entidad externa · ▢ proceso · → flujo de datos",
            tam=12, color="#6b7280")
    L.guardar("fig_1_2_dfd_contexto_situacion_actual")


for ilustrada in (False, True):
    dibujar(ilustrada)
