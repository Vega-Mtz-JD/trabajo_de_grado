"""Consolidación de varias mesas (RF13, ADR-009).

Recibe los paquetes USB de todas las mesas de una elección y:
  1. verifica cada paquete por separado (auditoría triple de la mesa);
  2. exige la misma elección y la misma definición, y mesas distintas;
  3. comprueba que todas las mesas definidas estén presentes;
  4. comprueba que ningún CI esté habilitado ni haya votado en dos mesas;
  5. suma los resultados de las actas de escrutinio de cada mesa.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from votoseguro.servicios import verificacion
from votoseguro.servicios.verificacion import Informe


@dataclass
class ResultadoConsolidacion:
    informes_mesa: dict[str, Informe] = field(default_factory=dict)
    global_: Informe = field(default_factory=Informe)
    resultados_mesa: dict[str, dict[str, int]] = field(default_factory=dict)
    total: dict[str, int] = field(default_factory=dict)
    nombre: str = ""
    eleccion_global: str = ""

    @property
    def conforme(self) -> bool:
        return self.global_.conforme and all(i.conforme for i in self.informes_mesa.values())

    def texto(self) -> str:
        lineas = [f"CÓMPUTO CONSOLIDADO — {self.nombre}", f"Elección: {self.eleccion_global}", ""]
        for mesa, informe in sorted(self.informes_mesa.items()):
            fallas = sum(c.ok is False for c in informe.chequeos)
            estado = "CONFORME" if informe.conforme else f"DISCREPANCIAS ({fallas})"
            lineas.append(f"Mesa {mesa}: {estado} · {self.resultados_mesa.get(mesa, {})}")
        lineas += ["", self.global_.texto(), "", "TOTAL:"]
        suma = sum(self.total.values()) or 1
        lineas += [f"  {k:<8} {v:>6}  {100 * v / suma:5.1f} %" for k, v in self.total.items()]
        lineas += ["", "RESULTADO CONSOLIDADO: " + ("CONFORME" if self.conforme else "CON DISCREPANCIAS")]
        return "\n".join(lineas)


def consolidar(paquetes: list[Path], frase: str, *,
               conteos_papel: dict[str, dict[str, int]] | None = None,
               huellas: dict[str, str] | None = None) -> ResultadoConsolidacion:
    """``conteos_papel`` y ``huellas`` son, por mesa, el conteo manual de VVPAT y la huella del
    equipo impresa en su zerésima (los ingresa el auditor)."""
    r = ResultadoConsolidacion()
    expedientes = {}
    for ruta in paquetes:
        informe = Informe()
        exp = verificacion.abrir_paquete(Path(ruta), frase, informe)
        mesa = exp["eleccion.json"]["mesa"] if exp else f"? ({Path(ruta).name})"
        if exp:
            verificacion.verificar_expediente(exp, informe, conteo_papel=(conteos_papel or {}).get(mesa),
                                              huella_esperada=(huellas or {}).get(mesa))
            informe.expediente = exp
        if mesa in r.informes_mesa:
            r.global_.agregar("CONSOLIDADO", f"Mesa {mesa} entregada una sola vez", False, "paquete repetido")
            continue
        r.informes_mesa[mesa] = informe
        if exp:
            expedientes[mesa] = exp
    if not expedientes:
        r.global_.agregar("CONSOLIDADO", "Paquetes legibles", False, "ningún paquete pudo abrirse")
        return r

    elecciones = {(e["eleccion.json"]["eleccion_global"], e["eleccion.json"]["hash_configuracion"])
                  for e in expedientes.values()}
    r.global_.agregar("CONSOLIDADO", "Todas las mesas son de la misma elección y definición", len(elecciones) == 1)
    primera = next(iter(expedientes.values()))["eleccion.json"]
    r.nombre, r.eleccion_global = primera["nombre"], primera["eleccion_global"]
    definidas = set(primera["definicion"]["mesas"])
    faltantes = sorted(definidas - set(expedientes))
    r.global_.agregar("CONSOLIDADO", "Están los paquetes de todas las mesas definidas", not faltantes,
                      f"faltan: {', '.join(faltantes)}" if faltantes else f"{len(definidas)} mesas")

    habilitado_en, voto_en = defaultdict(list), defaultdict(list)
    for mesa, exp in expedientes.items():
        for v in exp["padron.json"]:
            if v["habilitado"]:
                habilitado_en[v["ci"]].append(mesa)
            if v["ya_voto"]:
                voto_en[v["ci"]].append(mesa)
    dobles = {ci: m for ci, m in voto_en.items() if len(m) > 1}
    duplicados = {ci: m for ci, m in habilitado_en.items() if len(m) > 1}
    r.global_.agregar("CONSOLIDADO", "Ningún CI votó en más de una mesa", not dobles,
                      "; ".join(f"{ci}: mesas {', '.join(m)}" for ci, m in dobles.items()))
    r.global_.agregar("CONSOLIDADO", "Ningún CI habilitado en más de una mesa", not duplicados,
                      "; ".join(f"{ci}: mesas {', '.join(m)}" for ci, m in duplicados.items()))

    total = Counter()
    for mesa, exp in sorted(expedientes.items()):
        resultados = exp["actas.json"]["ESCRUTINIO"]["contenido"]["resultados"]
        r.resultados_mesa[mesa] = resultados
        total.update(resultados)
    r.total = {o[0]: total.get(o[0], 0) for o in primera["definicion"]["opciones"]}
    return r
