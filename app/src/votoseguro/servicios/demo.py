"""Simulación de una elección completa con hardware simulado (``votoseguro demo``).

Recorre todas las fases de la propuesta §13.1 con votantes sintéticos e incluye casos de
borde: lecturas de huella fallidas, una excepción manual por huella ilegible, un intento de
doble voto y abstención. Al final exporta el paquete y lo verifica (auditoría triple).
"""

import random
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from votoseguro.cripto.llavero import Llavero
from votoseguro.datos.conexion import VotanteNoHabilitado
from votoseguro.hardware.huella import LectorSimulado
from votoseguro.hardware.impresora import ImpresoraPDF
from votoseguro.servicios import (
    apertura, cierre, configuracion, empadronamiento, escrutinio, exportacion, verificacion, votacion,
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
class ResumenDemo:
    eleccion_id: str
    carpeta: Path
    paquete: Path
    resultados: dict[str, int]
    informe: verificacion.Informe
    huella_dispositivo: str
    eventos: Counter = field(default_factory=Counter)
    tiempos: dict[str, float] = field(default_factory=dict)


def ejecutar(conn, carpeta: Path, *, votantes: int = 100, bits: int = 3072, semilla: int | None = None,
             avisar=print) -> ResumenDemo:
    # Solo simula el comportamiento de los votantes; no se usa para nada criptográfico.
    azar = random.Random(semilla)  # nosec B311
    carpeta = Path(carpeta)
    llavero = Llavero.nuevo()
    llavero.guardar(carpeta / "llavero.vsk", FRASE_DEMO)
    lector = LectorSimulado(tasa_rechazo=0.15, azar=azar)
    impresora = ImpresoraPDF(carpeta / "impresiones")
    eventos: Counter = Counter()
    tiempos: dict[str, float] = {}

    def ctx(actor):
        return Contexto(conn, llavero, lector, impresora, actor)

    admin, operador, auditor = ctx("admin.demo"), ctx("operador.demo"), ctx("auditor.demo")

    t = time.perf_counter()
    avisar("1/8 Configurando la elección y repartiendo la clave entre 5 custodios…")
    creada = configuracion.crear_eleccion(
        admin, "Elección de Directorio 2026 (DEMO)", CANDIDATURAS, bits=bits,
        custodios=["Presidente del comité", "Delegado A", "Delegado B", "Auditor", "Representante empresa"])
    eid = creada.eleccion_id
    tiempos["configuracion"] = time.perf_counter() - t

    t = time.perf_counter()
    avisar(f"2/8 Empadronando {votantes} votantes con huella…")
    empadronamiento.iniciar(operador, eid)
    padron = []
    for i in range(votantes):
        ci = str(4_000_000 + i * 37)
        lector.colocar_dedo(ci)
        lector.tasa_rechazo = 0.0          # al empadronar se repite hasta tener buena calidad
        empadronamiento.registrar_votante(operador, eid, ci, azar.choice(_NOMBRES),
                                          f"{azar.choice(_APELLIDOS)} {azar.choice(_APELLIDOS)}")
        padron.append(ci)
    lector.tasa_rechazo = 0.15
    empadronamiento.cerrar_padron(operador, eid)
    tiempos["empadronamiento"] = time.perf_counter() - t

    avisar("3/8 Apertura: autodiagnóstico y zerésima…")
    apertura.abrir(operador, eid)

    t = time.perf_counter()
    avisar("4/8 Votación (con fallas de huella, una excepción manual, un doble voto y abstención)…")
    ilegible = padron[3]
    papel: Counter = Counter()
    pesos = [0.38, 0.33, 0.19, 0.06, 0.04]  # A, B, C, BLANCO, NULO
    codigos = ["A", "B", "C", "BLANCO", "NULO"]
    asistentes = [ci for ci in padron if azar.random() > 0.06]
    for ci in asistentes:
        lector.colocar_dedo(f"dedo-dañado-{ci}" if ci == ilegible else ci)
        try:
            sesion = votacion.autenticar_huella(operador, eid, ci)
        except AutenticacionFallida:
            # Huella ilegible forzada (1) y, por azar, alguna lectura fallida 3 veces seguidas
            eventos["excepciones_manuales"] += 1
            sesion = votacion.autorizar_excepcion(operador, eid, ci, "Huella ilegible; CI verificado en persona")
        comprobante = votacion.emitir(operador, sesion, azar.choices(codigos, pesos)[0])
        papel[comprobante.opcion.codigo] += 1   # el VVPAT cae en la urna física
    try:
        votacion.identificar(operador, eid, asistentes[0])
    except VotanteNoHabilitado:
        eventos["doble_voto_rechazado"] += 1
    tiempos["votacion"] = time.perf_counter() - t
    eventos["votos"] = len(asistentes)
    eventos["abstencion"] = votantes - len(asistentes)

    avisar("5/8 Cierre: checkpoint final y acta de cierre…")
    cierre.cerrar(operador, eid)

    t = time.perf_counter()
    avisar("6/8 Escrutinio con 3 de 5 custodios (partes 1, 3 y 5)…")
    acta = escrutinio.escrutar(auditor, eid, [p.a_texto() for p in creada.partes[0::2]])
    tiempos["escrutinio"] = time.perf_counter() - t

    avisar("7/8 Exportando el paquete de auditoría cifrado (USB)…")
    paquete = exportacion.exportar(operador, eid, carpeta / "usb", FRASE_DEMO)

    avisar("8/8 Auditoría triple: papel + USB + ledger…")
    informe = verificacion.verificar_paquete(paquete.ruta, FRASE_DEMO, conteo_papel=dict(papel),
                                             huella_esperada=llavero.huella_dispositivo)
    return ResumenDemo(eid, carpeta, paquete.ruta, acta.contenido["resultados"], informe,
                       llavero.huella_dispositivo, eventos, tiempos)
