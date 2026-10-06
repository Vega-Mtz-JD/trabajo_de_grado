"""Pruebas del anclaje en el ledger: cliente del puente, sincronización del outbox, modo
degradado y comparación del paquete USB con el ledger (ADR-001, ADR-002)."""

import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from votoseguro.blockchain import outbox
from votoseguro.blockchain.cliente import AnclajeRechazado, ClientePuente, PuenteNoDisponible
from votoseguro.cripto.llavero import Llavero
from votoseguro.datos import repositorio as repo
from votoseguro.hardware.camara import CamaraSimulada
from votoseguro.hardware.huella import LectorSimulado
from votoseguro.hardware.impresora import ImpresoraMemoria
from votoseguro.servicios import (
    apertura, cierre, configuracion, empadronamiento, escrutinio, exportacion, verificacion, votacion,
)
from votoseguro.servicios.base import Contexto
from votoseguro.servicios.configuracion import Candidatura

FRASE = "frase-de-prueba-larga"


class LedgerFalso:
    """Imita al puente + chaincode: guarda el estado de cada mesa como lo haría ConsultarMesa."""

    def __init__(self):
        self.mesas: dict[tuple[str, str], dict] = {}
        self.caido = False
        self.rechazar: str | None = None
        self.recibidos: list[str] = []

    def enviar(self, funcion, a):
        if self.caido:
            raise PuenteNoDisponible("fabric no disponible: conexión rechazada")
        if funcion == self.rechazar:
            raise AnclajeRechazado("validación: hito incoherente")
        self.recibidos.append(funcion)
        k = (a["eleccion_global"], a["mesa"])
        if funcion == "RegistrarEleccion":
            self.mesas[k] = {**a, "estado": "REGISTRADA", "checkpoints": []}
            return f"tx{len(self.recibidos)}"
        m = self.mesas[k]
        if funcion == "RegistrarApertura":
            m.update(hash_zeresima=a["hash_zeresima"], compromiso_padron=a["compromiso_padron"], estado="ABIERTA")
        elif funcion == "RegistrarCheckpoint":
            m["checkpoints"].append({c: a[c] for c in ("seq", "conteo", "raiz_merkle")})
        elif funcion == "RegistrarCierre":
            m.update(total_votos=a["total_votos"], raiz_merkle=a["raiz_merkle"], hash_acta_cierre=a["hash_acta"],
                     estado="CERRADA")
        elif funcion == "RegistrarEscrutinio":
            m.update(resultados=a["resultados"], hash_acta_escrutinio=a["hash_acta"], estado="ESCRUTADA")
        elif funcion == "RegistrarExportacion":
            m.update(hash_manifiesto=a["hash_manifiesto"], estado="EXPORTADA")
        return f"tx{len(self.recibidos)}"

    def consultar_mesa(self, eleccion_global, mesa):
        if self.caido:
            raise PuenteNoDisponible("fabric no disponible")
        return copy.deepcopy(self.mesas.get((eleccion_global, mesa)))


@pytest.fixture
def ledger():
    return LedgerFalso()


@pytest.fixture
def ctx(bd, ledger):
    return Contexto(bd("vs_app", autocommit=True), Llavero.nuevo(), LectorSimulado(), ImpresoraMemoria(),
                    "operador1", CamaraSimulada(), ledger)


def eleccion_completa(ctx, tmp_path, votantes=12, caer_despues_de=None):
    """Recorre todas las fases. Si ``caer_despues_de`` es un número, Fabric cae tras ese voto y
    vuelve antes del cierre."""
    creada = configuracion.crear_eleccion(ctx, "Con ledger", [Candidatura("A", "Ana"), Candidatura("B", "Beto")],
                                          bits=2048)
    eid = creada.eleccion_id
    empadronamiento.iniciar(ctx, eid)
    cis = [str(6_000_000 + i) for i in range(votantes)]
    for ci in cis:
        ctx.lector.colocar_dedo(ci)
        ctx.camara.colocar_persona(ci)
        empadronamiento.registrar_votante(ctx, eid, ci, "N", "A")
    empadronamiento.cerrar_padron(ctx, eid)
    apertura.abrir(ctx, eid)
    for i, ci in enumerate(cis, 1):
        ctx.lector.colocar_dedo(ci)
        ctx.camara.colocar_persona(ci)
        votacion.emitir(ctx, votacion.autenticar_huella(ctx, eid, ci), "AB"[i % 2])
        if caer_despues_de == i:
            ctx.puente.caido = True
    ctx.puente.caido = False
    cierre.cerrar(ctx, eid)
    escrutinio.escrutar(ctx, eid, creada.partes[:3])
    return eid, exportacion.exportar(ctx, eid, tmp_path, FRASE).ruta


# --- Sincronización y modo degradado ---------------------------------------------------------

def test_todos_los_hitos_se_anclan_en_orden(ctx, ledger, tmp_path):
    eleccion_completa(ctx, tmp_path)
    assert ledger.recibidos == ["RegistrarEleccion", "RegistrarApertura", "RegistrarCheckpoint",
                                "RegistrarCheckpoint", "RegistrarCierre", "RegistrarEscrutinio",
                                "RegistrarExportacion"]
    filas = repo.outbox(ctx.conn)
    assert all(f["estado"] == "ENVIADO" and f["tx_id"] for f in filas)


def test_modo_degradado_la_votacion_continua_y_luego_se_sincroniza(ctx, ledger, tmp_path):
    eid, paquete = eleccion_completa(ctx, tmp_path, votantes=25, caer_despues_de=5)
    assert repo.contar_votos(ctx.conn, eid) == 25           # nadie dejó de votar
    eventos = [e["evento"] for e in repo.bitacora_completa(ctx.conn)]
    assert eventos.count("MODO_DEGRADADO") == 1 and eventos.count("ANCLAJE_RESTABLECIDO") == 1
    assert all(f["estado"] == "ENVIADO" for f in repo.outbox(ctx.conn))
    assert [c["seq"] for c in ledger.mesas[next(iter(ledger.mesas))]["checkpoints"]] == [1, 2, 3]


def test_sincronizar_se_detiene_en_el_primer_fallo(ctx, ledger):
    for i in range(3):
        outbox.encolar(ctx.conn, "RegistrarCheckpoint", {"eleccion_global": "x", "mesa": "01", "seq": i})
    ledger.caido = True
    r = outbox.sincronizar(ctx.conn, ledger)
    assert r.enviados == 0 and r.pendientes == 3 and not r.al_dia
    assert [f["estado"] for f in repo.outbox(ctx.conn)] == ["PENDIENTE"] * 3


def test_rechazo_del_chaincode_queda_en_error(ctx, ledger, tmp_path):
    ledger.rechazar = "RegistrarApertura"
    creada = configuracion.crear_eleccion(ctx, "Rechazo", [Candidatura("A", "Ana")], bits=2048)
    empadronamiento.iniciar(ctx, creada.eleccion_id)
    ctx.camara.colocar_persona("6000000")
    ctx.lector.colocar_dedo("6000000")
    empadronamiento.registrar_votante(ctx, creada.eleccion_id, "6000000", "N", "A")
    empadronamiento.cerrar_padron(ctx, creada.eleccion_id)
    apertura.abrir(ctx, creada.eleccion_id)                  # la apertura local no se bloquea
    estados = [f["estado"] for f in repo.outbox(ctx.conn)]
    assert estados == ["ENVIADO", "ERROR"]
    assert repo.contar_eventos(ctx.conn, creada.eleccion_id, "APERTURA") == 1
    assert "ANCLAJE_RECHAZADO" in [e["evento"] for e in repo.bitacora_completa(ctx.conn)]


# --- Verificación contra el ledger -----------------------------------------------------------

def _ledger_fallidos(informe):
    return {c.nombre for c in informe.chequeos if c.nivel == "LEDGER" and c.ok is False}


def test_paquete_coincide_con_el_ledger(ctx, ledger, tmp_path):
    _, paquete = eleccion_completa(ctx, tmp_path)
    informe = verificacion.verificar_paquete(paquete, FRASE, consultar_ledger=ledger.consultar_mesa)
    assert informe.conforme, informe.texto()
    assert sum(c.nivel == "LEDGER" and c.ok for c in informe.chequeos) == 6


def test_ledger_distinto_al_paquete_se_detecta(ctx, ledger, tmp_path):
    _, paquete = eleccion_completa(ctx, tmp_path)
    mesa = next(iter(ledger.mesas.values()))
    mesa["resultados"]["A"] += 1                 # el paquete dice otra cosa que el ledger
    mesa["checkpoints"].pop()
    fallidos = _ledger_fallidos(verificacion.verificar_paquete(paquete, FRASE, consultar_ledger=ledger.consultar_mesa))
    assert fallidos == {"Escrutinio: resultados y hash del acta", "Checkpoints anclados = checkpoints del paquete"}


def test_mesa_ausente_o_ledger_caido(ctx, ledger, tmp_path):
    _, paquete = eleccion_completa(ctx, tmp_path)
    vacio = LedgerFalso()
    assert "La mesa está registrada en el ledger" in _ledger_fallidos(
        verificacion.verificar_paquete(paquete, FRASE, consultar_ledger=vacio.consultar_mesa))
    vacio.caido = True
    informe = verificacion.verificar_paquete(paquete, FRASE, consultar_ledger=vacio.consultar_mesa)
    sin_evaluar = [c for c in informe.chequeos if c.nivel == "LEDGER" and c.ok is None]
    assert informe.conforme and "no disponible" in sin_evaluar[0].detalle


# --- Cliente HTTP del puente -----------------------------------------------------------------

class _Manejador(BaseHTTPRequestHandler):
    respuestas: dict[str, tuple[int, dict]] = {}

    def _responder(self):
        if self.headers.get("Authorization") != "Bearer token-de-prueba":
            codigo, cuerpo = 401, {"error": "token inválido"}
        else:
            codigo, cuerpo = self.respuestas.get(self.path, (404, {"error": "no encontrado"}))
        datos = json.dumps(cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    do_GET = do_POST = _responder

    def log_message(self, *args):
        pass


@pytest.fixture
def servidor_http():
    servidor = HTTPServer(("127.0.0.1", 0), _Manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


def test_cliente_mapea_respuestas_del_puente(servidor_http):
    _Manejador.respuestas = {
        "/tx/RegistrarCierre": (200, {"tx_id": "abc"}),
        "/tx/RegistrarApertura": (409, {"error": "validación: se requiere REGISTRADA"}),
        "/tx/RegistrarCheckpoint": (503, {"error": "fabric no disponible"}),
        "/mesa/g/01": (200, {"estado": "ABIERTA"}),
        "/salud": (200, {"estado": "ok"}),
    }
    cliente = ClientePuente(servidor_http, "token-de-prueba", timeout=5)
    assert cliente.disponible()
    assert cliente.enviar("RegistrarCierre", {}) == "abc"
    with pytest.raises(AnclajeRechazado, match="REGISTRADA"):
        cliente.enviar("RegistrarApertura", {})
    with pytest.raises(PuenteNoDisponible):
        cliente.enviar("RegistrarCheckpoint", {})
    assert cliente.consultar_mesa("g", "01") == {"estado": "ABIERTA"}
    assert cliente.consultar_mesa("g", "99") is None
    assert cliente.historial("g", "99") == []


def test_cliente_sin_puente_o_con_token_incorrecto(servidor_http):
    caido = ClientePuente("http://127.0.0.1:1", "x", timeout=2)
    assert not caido.disponible()
    with pytest.raises(PuenteNoDisponible):
        caido.enviar("RegistrarCierre", {})
    with pytest.raises(Exception):
        ClientePuente(servidor_http, "otro-token", timeout=5).enviar("RegistrarCierre", {})
