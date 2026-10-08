"""Figura A1 — Árbol de problemas (Anexo A) (causas = problemas secundarios del apartado 1.3.3)."""

from arbol import dibujar
from lienzo import AMBAR, AMBAR_SUAVE, ROJO, ROJO_SUAVE

for ilustrada in (False, True):
    dibujar(
        "fig_a1_arbol_de_problemas",
        final="Desconfianza en los resultados proclamados",
        efectos=["Suplantación de identidad y voto múltiple", "Demoras en el escrutinio, errores y reclamos",
                 "Alteraciones del acta que no dejan rastro", "Impugnaciones difíciles de resolver",
                 "Imposibilidad de auditar el proceso"],
        central="<b>PROBLEMA PRINCIPAL:</b> los procesos de votación de [EMPRESA] carecen de mecanismos para "
                "verificar de forma independiente la identidad de los votantes, la integridad de los votos "
                "y la exactitud de los resultados.",
        base=["Identificación del votante solo por verificación visual de la cédula",
              "Conteo manual de las papeletas al cierre de la jornada",
              "Actas elaboradas y custodiadas en papel sin mecanismo de integridad",
              "Ninguna evidencia independiente del acta para contrastar",
              "Sin registro sistemático de quién interviene en cada etapa ni cuándo"],
        colores=((AMBAR_SUAVE, AMBAR), (AMBAR_SUAVE, AMBAR), (ROJO, ROJO), (ROJO_SUAVE, ROJO)),
        marcas="P",
        titulos=["EFECTO FINAL", "EFECTOS", "PROBLEMA", "CAUSAS"],
        ilustrada=ilustrada,
        iconos=dict(final="incorrecto", central="alerta",
                   efectos=["persona", "reloj", "acta", "observador", "lupa"],
                   base=["cedula", "conteo", "documento", "incorrecto", "reloj"]),
    )
