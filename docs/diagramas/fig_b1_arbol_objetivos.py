"""Figura B1 — Árbol de objetivos (Anexo B) (medios = objetivos específicos del apartado 1.4.2)."""

from arbol import dibujar
from lienzo import AZUL, AZUL_SUAVE, VERDE, VERDE_SUAVE

dibujar(
    "fig_b1_arbol_de_objetivos",
    final="Mayor confianza en los resultados de los procesos de votación",
    efectos=["Se reduce la suplantación y se rechaza el voto múltiple", "Resultados al cierre, sin conteo manual",
             "Toda alteración del acta se vuelve detectable", "Impugnaciones resueltas con evidencia complementaria",
             "Auditoría completa sin revelar el voto"],
    central="<b>OBJETIVO GENERAL:</b> desarrollar un sistema de votación electrónica sin conexión a red, con "
            "autenticación biométrica, comprobante en papel verificable y registro en Hyperledger Fabric, "
            "para la verificación multinivel de los resultados de [EMPRESA].",
    base=["Empadronamiento con foto y huella e identificación biométrica 1:1",
          "Escrutinio automático con votos cifrados y clave repartida entre custodios",
          "Actas firmadas digitalmente y ancladas en Hyperledger Fabric",
          "Verificador de auditoría triple: papel, USB y registro distribuido",
          "Bitácora encadenada de cada acción con su responsable y momento"],
    colores=((AZUL_SUAVE, AZUL), (AZUL_SUAVE, AZUL), (VERDE, VERDE), (VERDE_SUAVE, VERDE)),
    marcas="O",
    titulos=["FIN ÚLTIMO", "FINES", "OBJETIVO", "MEDIOS"],
)
