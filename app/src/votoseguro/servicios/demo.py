"""Simulación de una elección completa con hardware simulado (``votoseguro demo``).

Simula una o varias urnas (mesas), cada una como un equipo distinto con su propio llavero,
custodios e impresora, compartiendo la base de datos de desarrollo. Recorre todas las fases e
incluye casos de borde: un votante empadronado en dos mesas (lo detecta el cruce de padrones),
lecturas de huella fallidas, una excepción manual por huella ilegible, un intento de doble voto y
abstención. Al final verifica cada mesa (auditoría triple) y consolida los resultados.
"""

import random
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from votoseguro.cripto.llavero import Llavero
from votoseguro.datos.conexion import VotanteNoHabilitado
from votoseguro.hardware.camara import CamaraSimulada
from votoseguro.hardware.huella import LectorSimulado
from votoseguro.hardware.impresora import ImpresoraPDF
from votoseguro.servicios import (
    apertura, cierre, configuracion, consolidacion, empadronamiento, escrutinio, exportacion, votacion,
)
from votoseguro.servicios.base import AutenticacionFallida, Contexto
from votoseguro.servicios.configuracion import Candidatura

FRASE_DEMO = "demo-votoseguro-2026"

_NOMBRES = ["Juan", "María", "Carlos", "Ana", "Luis", "Rosa", "Jorge", "Elena", "Mario", "Lucía",
            "Pedro", "Sonia", "Víctor", "Gladys", "René", "Patricia", "Freddy", "Wilma", "Hugo", "Norma"]
_APELLIDOS = ["Mamani", "Quispe", "Choque", "Condori", "Flores", "Apaza", "Limachi", "Huanca",
              "Ticona", "Callisaya", "Copa", "Poma", "Cruz", "Gutiérrez", "Rojas", "Vargas"]

CANDIDATURAS = [
    Candidatura("A", "Ana Choque Mamani", "Frente Unidad Laboral"),
    Candidatura("B", "Carlos Quispe Flores", "Alianza Renovación"),
    Candidatura("C", "Rosa Condori Apaza", "Movimiento Transparencia"),
]


@dataclass
class Urna:
    """Un equipo de votación simulado (una mesa)."""

    mesa: str
    ctx: Contexto
    eleccion_id: str = ""
    partes: list = field(default_factory=list)
    padron: list[str] = field(default_factory=list)


@dataclass
class ResumenDemo:
    eleccion_global: str
    carpeta: Path
    paquetes: list[Path]
    consolidado: consolidacion.ResultadoConsolidacion
    cruce: empadronamiento.ResultadoCruce
    eventos: Counter = field(default_factory=Counter)
    tiempos: dict[str, float] = field(default_factory=dict)

    @property
    def resultados(self) -> dict[str, int]:
        return self.consolidado.total

    @property
    def conforme(self) -> bool:
        return self.consolidado.conforme


def ejecutar(conn, carpeta: Path, *, votantes: int = 100, mesas: int = 1, bits: int = 3072,
             semilla: int | None = None, avisar=print, puente=None) -> ResumenDemo:
    """``puente``: ClientePuente para anclar en Hyperledger Fabric (None = sin anclaje)."""
    # Solo simula el comportamiento de los votantes; no se usa para nada criptográfico.
    azar = random.Random(semilla)  # nosec B311
    carpeta = Path(carpeta)
    eventos: Counter = Counter()
    tiempos: dict[str, float] = {}
    codigos_mesa = [f"{i:02d}" for i in range(1, mesas + 1)]

    urnas = []
    for mesa in codigos_mesa:
        llavero = Llavero.nuevo()
        llavero.guardar(carpeta / f"mesa{mesa}" / "llavero.vsk", FRASE_DEMO)
        ctx = Contexto(conn, llavero, LectorSimulado(tasa_rechazo=0.15, azar=azar),
                       ImpresoraPDF(carpeta / f"mesa{mesa}" / "impresiones"), f"operador.mesa{mesa}",
                       CamaraSimulada(), puente)
        urnas.append(Urna(mesa, ctx))

    t = time.perf_counter()
    avisar(f"1/9 Definiendo la elección ({mesas} mesa/s) y exportando la definición firmada…")
    definicion = configuracion.definir_eleccion("Elección de Directorio 2026 (DEMO)", CANDIDATURAS,
                                                mesas=codigos_mesa)
    ruta_def = carpeta / "usb" / "definicion.vsd"
    configuracion.exportar_definicion(urnas[0].ctx, definicion, ruta_def, FRASE_DEMO)
    huella_creadora = urnas[0].ctx.llavero.huella_dispositivo
    for urna in urnas:
        importada = configuracion.importar_definicion(ruta_def, FRASE_DEMO, huella_creadora)
        creada = configuracion.instalar_mesa(urna.ctx, importada, urna.mesa, bits=bits, custodios=[
            f"Presidente de mesa {urna.mesa}", "Jurado A", "Jurado B", "Delegado auditor", "Delegado empresa"])
        urna.eleccion_id, urna.partes = creada.eleccion_id, creada.partes
    tiempos["configuracion"] = time.perf_counter() - t

    t = time.perf_counter()
    avisar(f"2/9 Empadronando {votantes} votantes en sus mesas (datos, foto y huella)…")
    personas = [(str(4_000_000 + i * 37), azar.choice(_NOMBRES),
                 f"{azar.choice(_APELLIDOS)} {azar.choice(_APELLIDOS)}") for i in range(votantes)]
    for urna in urnas:
        empadronamiento.iniciar(urna.ctx, urna.eleccion_id)
    for i, persona in enumerate(personas):
        _empadronar(urnas[i % mesas], *persona)
    if mesas > 1:   # alguien se empadrona también en otra mesa (error o intento de fraude)
        _empadronar(urnas[1], *personas[0])
    tiempos["empadronamiento"] = time.perf_counter() - t

    avisar("3/9 Cruce de padrones entre mesas…")
    resumenes = [empadronamiento.exportar_resumen_padron(u.ctx, u.eleccion_id, carpeta / "usb", FRASE_DEMO)
                 for u in urnas]
    cruce = empadronamiento.cruzar_padrones(resumenes, FRASE_DEMO)
    for ci, mesas_ci in cruce.duplicados.items():
        for urna in urnas:
            if urna.mesa in mesas_ci[1:]:       # se conserva en la primera mesa
                empadronamiento.inhabilitar_votante(urna.ctx, urna.eleccion_id, ci,
                                                    f"Duplicado: también empadronado en mesa {mesas_ci[0]}")
                urna.padron.remove(ci)
                eventos["duplicados_inhabilitados"] += 1
    for urna in urnas:
        empadronamiento.cerrar_padron(urna.ctx, urna.eleccion_id)

    avisar("4/9 Apertura de cada mesa: autodiagnóstico y zerésima…")
    for urna in urnas:
        apertura.abrir(urna.ctx, urna.eleccion_id)

    t = time.perf_counter()
    avisar("5/9 Votación (fallas de huella, excepción manual, doble voto, abstención)…")
    pesos = [0.38, 0.33, 0.19, 0.06, 0.04]  # A, B, C, BLANCO, NULO
    codigos = ["A", "B", "C", "BLANCO", "NULO"]
    ilegible = urnas[0].padron[min(3, len(urnas[0].padron) - 1)]
    papel: dict[str, Counter] = {u.mesa: Counter() for u in urnas}
    for urna in urnas:
        asistentes = [ci for ci in urna.padron if azar.random() > 0.06]
        for ci in asistentes:
            urna.ctx.camara.colocar_persona(ci)
            urna.ctx.lector.colocar_dedo(f"dedo-dañado-{ci}" if ci == ilegible else ci)
            try:
                sesion = votacion.autenticar_huella(urna.ctx, urna.eleccion_id, ci)
            except AutenticacionFallida:
                # Huella ilegible forzada (1) y, por azar, alguna lectura fallida 3 veces seguidas
                eventos["excepciones_manuales"] += 1
                sesion = votacion.autorizar_excepcion(urna.ctx, urna.eleccion_id, ci,
                                                      "Huella ilegible; CI y foto verificados en persona")
            comprobante = votacion.emitir(urna.ctx, sesion, azar.choices(codigos, pesos)[0])
            papel[urna.mesa][comprobante.opcion.codigo] += 1   # el VVPAT cae en la urna física
        eventos["votos"] += len(asistentes)
        eventos["abstencion"] += len(urna.padron) - len(asistentes)
        if asistentes and urna is urnas[0]:
            try:
                votacion.identificar(urna.ctx, urna.eleccion_id, asistentes[0])
            except VotanteNoHabilitado:
                eventos["doble_voto_rechazado"] += 1
    tiempos["votacion"] = time.perf_counter() - t

    avisar("6/9 Cierre de cada mesa: acta de cierre y lista de ausentes…")
    for urna in urnas:
        cierre.cerrar(urna.ctx, urna.eleccion_id)

    t = time.perf_counter()
    avisar("7/9 Escrutinio en cada mesa con 3 de sus 5 custodios…")
    for urna in urnas:
        escrutinio.escrutar(urna.ctx, urna.eleccion_id, [p.a_texto() for p in urna.partes[0::2]])
    tiempos["escrutinio"] = time.perf_counter() - t

    avisar("8/9 Exportando el paquete de auditoría cifrado de cada mesa (USB)…")
    paquetes = [exportacion.exportar(u.ctx, u.eleccion_id, carpeta / "usb", FRASE_DEMO).ruta for u in urnas]

    avisar("9/9 Auditoría triple de cada mesa y consolidación…")
    # El auditor ingresa, por mesa, el conteo manual de los VVPAT y la huella impresa en la zerésima.
    consolidado = consolidacion.consolidar(
        paquetes, FRASE_DEMO, conteos_papel={m: dict(c) for m, c in papel.items()},
        huellas={u.mesa: u.ctx.llavero.huella_dispositivo for u in urnas},
        consultar_ledger=puente.consultar_mesa if puente else None)
    return ResumenDemo(definicion.eleccion_global, carpeta, paquetes, consolidado, cruce, eventos, tiempos)


def _empadronar(urna: Urna, ci: str, nombres: str, apellidos: str) -> None:
    urna.ctx.camara.colocar_persona(ci)
    urna.ctx.lector.colocar_dedo(ci)
    urna.ctx.lector.tasa_rechazo = 0.0   # al empadronar se repite hasta tener buena calidad
    empadronamiento.registrar_votante(urna.ctx, urna.eleccion_id, ci, nombres, apellidos)
    urna.ctx.lector.tasa_rechazo = 0.15
    urna.padron.append(ci)


# --- Demostración en la interfaz ----------------------------------------------------------------

PERSONAS_DEMO = [
    ("4501001", "Rosa", "Mamani Apaza"), ("4501002", "Luis", "Quispe Choque"),
    ("4501003", "Elena", "Condori Flores"), ("4501004", "Jorge", "Limachi Huanca"),
    ("4501005", "Lucía", "Ticona Copa"), ("4501006", "Mario", "Callisaya Poma"),
    ("4501007", "Gladys", "Apaza Rojas"), ("4501008", "René", "Cruz Vargas"),
    ("4501009", "Norma", "Choque Mamani"), ("4501010", "Hugo", "Flores Quispe"),
]


@dataclass
class DemostracionPreparada:
    eleccion_id: str
    personas: list[tuple[str, str, str]]
    partes: list[str]
    abierta: bool


def preparar_para_interfaz(ctx: Contexto, *, votantes: int = 5, abrir: bool = False,
                           bits: int = 3072) -> DemostracionPreparada:
    """Deja una elección lista para mostrar la votación en la interfaz: definida, con la mesa
    instalada, el padrón empadronado (fotos y huellas simuladas) y cerrado, y opcionalmente abierta.
    Debe usar el MISMO llavero que la interfaz, para que ella pueda leer las fotos y huellas."""
    personas = PERSONAS_DEMO[:max(1, min(votantes, len(PERSONAS_DEMO)))]
    creada = configuracion.crear_eleccion(
        ctx, "Demostración — Elección de Directorio 2026", CANDIDATURAS, bits=bits,
        custodios=["Presidente de mesa", "Jurado A", "Jurado B", "Delegado auditor", "Delegado empresa"])
    eid = creada.eleccion_id
    empadronamiento.iniciar(ctx, eid)
    for ci, nombres, apellidos in personas:
        if isinstance(ctx.camara, CamaraSimulada):
            ctx.camara.colocar_persona(ci)
        if isinstance(ctx.lector, LectorSimulado):
            ctx.lector.colocar_dedo(ci)
        empadronamiento.registrar_votante(ctx, eid, ci, nombres, apellidos)
    empadronamiento.cerrar_padron(ctx, eid)
    if abrir:
        apertura.abrir(ctx, eid)
    return DemostracionPreparada(eid, personas, [p.a_texto() for p in creada.partes], abrir)
