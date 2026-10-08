"""Figura 1.3 — DFD de nivel 1 de la situación actual, con los procesos donde nacen los problemas
(versión sobria e ilustrada)."""

from lienzo import AMBAR, AMBAR_SUAVE, ROJO, ROJO_SUAVE, Lienzo, colores_icono


def dibujar(ilustrada: bool) -> None:
    L = Lienzo(800, 640, ilustrada)
    pr = dict(relleno=AMBAR_SUAVE, borde=AMBAR, tam=13 if ilustrada else 14)

    def t(texto):
        return texto.replace("<br>", " ") if ilustrada else texto

    def entidad(x, y, w, h, texto, icono):
        return L.entidad(x, y, w, h, texto, icono=icono, icono_color=colores_icono(icono)[0])

    votante = entidad(10, 130, 120, 60, "Votante", "persona")
    entidad(660, 20, 130, 56, "Comité<br>electoral", "grupo")
    entidad(660, 556, 130, 60, "Delegados de<br>los frentes", "observador")

    L.almacen(180, 20, 200, 36, "A1", "Padrón en papel", icono="lista")
    L.almacen(180, 440, 200, 36, "A2", "Urna con papeletas", icono="urna")
    L.almacen(650 if not ilustrada else 636, 362, 140 if not ilustrada else 160, 36, "A3", "Actas en papel",
              icono="acta")

    p1 = L.proceso_dfd(190, 100, 170, 90, "1.0", t("Identificar al votante<br>con su cédula"), icono="lupa", **pr)
    L.proceso_dfd(190, 290, 170, 90, "2.0", t("Entregar la papeleta<br>y recibir el voto"), icono="papeleta", **pr)
    p3 = L.proceso_dfd(450, 410, 170, 90, "3.0", t("Contar los votos<br>manualmente"), icono="conteo", **pr)
    p4 = L.proceso_dfd(450, 210, 170, 90, "4.0", t("Elaborar y custodiar<br>el acta"), icono="acta", **pr)
    p5 = L.proceso_dfd(420, 540, 170, 80, "5.0", t("Atender reclamos<br>e impugnaciones"), icono="alerta", **pr)
    for proc, problema in ((p1, "P1"), (p3, "P2"), (p4, "P3"), (p5, "P4")):
        L.insignia(proc.x + proc.w - 2, proc.y + 2, problema)

    L.flecha(votante.der, (190, 160), texto="Cédula", tramo=0)
    L.flecha((660, 38), (380, 38), texto="Padrón de habilitados")
    L.flecha((275, 56), (275, 100), texto="Consulta y firma", doble=True, desplazar=(58, 0))
    L.flecha((275, 190), (275, 290), texto="Votante<br>habilitado")
    L.flecha((90, 190), (90, 315), (190, 315), texto="Papeleta<br>marcada", tramo=0)
    L.flecha((190, 355), (45, 355), (45, 190), texto="Papeleta<br>en blanco", tramo=1, desplazar=(0, 40))
    L.flecha((275, 380), (275, 440), texto="Papeleta depositada", desplazar=(68, 0))
    L.flecha((380, 458), (450, 458), texto="Papeletas", desplazar=(0, -14))
    L.flecha((535, 410), (535, 300), texto="Resultados<br>del conteo")
    L.flecha((620, 240), (725, 240), (725, 76), texto="Acta de<br>resultados", tramo=1)
    L.flecha((620, 280), (705, 280), (705, 362), texto="Acta<br>firmada", tramo=1, desplazar=(0, 8))
    L.flecha((720, 398), (720, 520), (505, 520), (505, 540), texto="Acta (única evidencia)", tramo=1)
    L.flecha((660, 572), (590, 572), texto="Reclamo", desplazar=(0, -12))
    L.flecha((590, 604), (660, 604), texto="Resolución", desplazar=(0, 12))

    r = L.caja(10, 510, 380, 92, "<b>Ningún proceso registra quién intervino ni cuándo.</b><br>"
               "El acta en papel (A3) es la única evidencia del resultado.", relleno=ROJO_SUAVE, borde=ROJO,
               tam=13, discontinua=True, icono="reloj", icono_color=ROJO)
    L.insignia(r.x + 2, r.y + 2, "P5")
    L.guardar("fig_1_3_dfd_nivel1_situacion_actual")


for ilustrada in (False, True):
    dibujar(ilustrada)
