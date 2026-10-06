"""Fases 5–7 — Identificación, emisión del voto con VVPAT y checkpoints.

Flujo: ``identificar`` (CI) → ``autenticar_huella`` (1:1, máximo 3 intentos) o
``autorizar_excepcion`` (huella ilegible, con motivo) → ``emitir`` (una sola vez por sesión).
"""

from dataclasses import dataclass, field

from votoseguro.auditoria import bitacora
from votoseguro.blockchain import outbox
from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto.hashing import sha3
from votoseguro.cripto.merkle import raiz_merkle
from votoseguro.datos import repositorio as repo
from votoseguro.datos import urna
from votoseguro.datos.conexion import VotanteNoHabilitado
from votoseguro.dominio.modelos import Comprobante, Estado, codigo_vvpat
from votoseguro.hardware.huella import LectorNoDisponible
from votoseguro.hardware.impresora import ImpresoraNoDisponible
from votoseguro.servicios.base import (
    AutenticacionFallida, Contexto, ErrorServicio, HardwareNoDisponible, OpcionInvalida, exigir_estado,
)

MAX_INTENTOS = 3


@dataclass
class SesionVoto:
    """Autorización para emitir **un** voto. Se invalida al usarse."""

    eleccion_id: str
    ci: str
    metodo: str                      # HUELLA | EXCEPCION
    usada: bool = field(default=False)


class ErrorImpresionVVPAT(ErrorServicio):
    """El voto quedó registrado, pero el VVPAT no se imprimió: pausar y reimprimir."""

    def __init__(self, comprobante: Comprobante):
        super().__init__("el voto se registró pero el comprobante no se imprimió; revise la impresora")
        self.comprobante = comprobante


def identificar(ctx: Contexto, eleccion_id: str, ci: str) -> dict:
    """Verifica que el CI esté en el padrón, habilitado y sin votar. Devuelve nombres y apellidos."""
    exigir_estado(ctx, eleccion_id, Estado.ABIERTA)
    votante = repo.obtener_votante(ctx.conn, eleccion_id, ci)
    if votante is None or not votante["habilitado"]:
        motivo = "no figura en el padrón" if votante is None else "no está habilitado"
        bitacora.registrar(ctx.conn, ctx.actor, "IDENTIFICACION_RECHAZADA",
                           {"eleccion": eleccion_id, "ci": ci, "motivo": motivo})
        raise VotanteNoHabilitado(f"el CI {ci} {motivo}")
    if votante["ya_voto"]:
        bitacora.registrar(ctx.conn, ctx.actor, "IDENTIFICACION_RECHAZADA",
                           {"eleccion": eleccion_id, "ci": ci, "motivo": "ya votó"})
        raise VotanteNoHabilitado(f"el CI {ci} ya emitió su voto")
    return {"nombres": votante["nombres"], "apellidos": votante["apellidos"]}


def autenticar_huella(ctx: Contexto, eleccion_id: str, ci: str) -> SesionVoto:
    """Compara 1:1 la huella viva con la registrada. Hasta ``MAX_INTENTOS`` capturas."""
    identificar(ctx, eleccion_id, ci)
    votante = repo.obtener_votante(ctx.conn, eleccion_id, ci)
    registrada = ctx.llavero.descifrar_plantilla(eleccion_id, ci, bytes(votante["plantilla_cifrada"]))
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            viva = ctx.lector.capturar()
        except LectorNoDisponible as e:
            raise HardwareNoDisponible(str(e)) from e
        if ctx.lector.coincide(registrada, viva):
            bitacora.registrar(ctx.conn, ctx.actor, "VOTANTE_AUTENTICADO",
                               {"eleccion": eleccion_id, "ci": ci, "metodo": "HUELLA", "intento": intento})
            return SesionVoto(eleccion_id, ci, "HUELLA")
        bitacora.registrar(ctx.conn, ctx.actor, "AUTENTICACION_FALLIDA",
                           {"eleccion": eleccion_id, "ci": ci, "intento": intento})
    raise AutenticacionFallida(f"la huella no coincide tras {MAX_INTENTOS} intentos")


def autorizar_excepcion(ctx: Contexto, eleccion_id: str, ci: str, motivo: str) -> SesionVoto:
    """Habilita a un votante con huella ilegible tras verificar su CI en persona.

    Queda registrado quién autorizó y por qué, y se cuenta en el acta de cierre.
    """
    if len(motivo.strip()) < 10:
        raise ValueError("describa el motivo de la excepción (mínimo 10 caracteres)")
    identificar(ctx, eleccion_id, ci)
    bitacora.registrar(ctx.conn, ctx.actor, "EXCEPCION_MANUAL",
                       {"eleccion": eleccion_id, "ci": ci, "motivo": motivo.strip()})
    return SesionVoto(eleccion_id, ci, "EXCEPCION")


def emitir(ctx: Contexto, sesion: SesionVoto, codigo_opcion: str) -> Comprobante:
    """Cifra y deposita el voto, imprime el VVPAT y, cada N votos, hace un checkpoint.

    El registro (votante marcado + voto + evento de bitácora) es una sola transacción. La
    bitácora no guarda la opción ni el hash del voto (ADR-004).
    """
    if sesion.usada:
        raise ErrorServicio("esta sesión de voto ya fue utilizada")
    eleccion = exigir_estado(ctx, sesion.eleccion_id, Estado.ABIERTA)
    opcion = next((o for o in repo.opciones(ctx.conn, eleccion.id) if o.codigo == codigo_opcion), None)
    if opcion is None:
        raise OpcionInvalida(f"opción inexistente: {codigo_opcion}")

    publica = cv.publica_desde_pem(eleccion.clave_publica_pem)
    cifrado = cv.cifrar_voto(publica, eleccion.id, opcion.codigo.encode())
    hash_voto = sha3(cifrado)
    with ctx.conn.transaction():
        total = urna.emitir_voto(ctx.conn, eleccion.id, sesion.ci, cifrado, hash_voto)
        bitacora.registrar(ctx.conn, ctx.actor, "VOTO_EMITIDO", {"eleccion": eleccion.id, "n": total})
    sesion.usada = True

    comprobante = Comprobante(eleccion.nombre, ctx.mesa, opcion, codigo_vvpat(hash_voto))
    if total % eleccion.checkpoint_cada == 0:
        checkpoint(ctx, eleccion.id)
    try:
        ctx.impresora.imprimir_vvpat(comprobante)
    except ImpresoraNoDisponible as e:
        bitacora.registrar(ctx.conn, ctx.actor, "VVPAT_NO_IMPRESO", {"eleccion": eleccion.id})
        raise ErrorImpresionVVPAT(comprobante) from e
    return comprobante


def reimprimir(ctx: Contexto, comprobante: Comprobante) -> None:
    ctx.impresora.imprimir_vvpat(
        Comprobante(comprobante.eleccion, comprobante.mesa, comprobante.opcion, comprobante.codigo, True))
    bitacora.registrar(ctx.conn, ctx.actor, "VVPAT_REIMPRESO", {})


def checkpoint(ctx: Contexto, eleccion_id: str) -> dict:
    """Mezcla la urna, calcula la raíz de Merkle y la deja anclada (BD + bitácora + outbox)."""
    with ctx.conn.transaction():
        urna.mezclar(ctx.conn)
        hashes = urna.hashes_votos(ctx.conn, eleccion_id)
        previos = repo.checkpoints(ctx.conn, eleccion_id)
        seq = previos[-1]["seq"] + 1 if previos else 1
        datos = {"seq": seq, "conteo": len(hashes), "raiz_merkle": raiz_merkle(hashes)}
        repo.insertar_checkpoint(ctx.conn, eleccion_id, seq, datos["conteo"], datos["raiz_merkle"])
        bitacora.registrar(ctx.conn, "sistema", "CHECKPOINT", {"eleccion": eleccion_id, **datos})
        outbox.encolar(ctx.conn, "RegistrarCheckpoint", {"eleccion_id": eleccion_id, **datos})
    return datos
