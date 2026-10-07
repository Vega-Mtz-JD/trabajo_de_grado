"""Pruebas de integración del proceso electoral completo (servicios + BD + verificador)."""

import io
import json
import zipfile
from collections import Counter

import pytest

from votoseguro.cripto.llavero import Llavero, cifrar_con_frase, descifrar_con_frase
from votoseguro.datos import repositorio as repo
from votoseguro.datos.conexion import VotanteNoHabilitado
from votoseguro.dominio.modelos import Estado, Rol
from votoseguro.hardware.camara import CamaraSimulada
from votoseguro.hardware.huella import LectorNoDisponible, LectorSimulado
from votoseguro.hardware.impresora import ImpresoraMemoria
from votoseguro.servicios import (
    apertura, cierre, configuracion, demo, empadronamiento, escrutinio, exportacion, usuarios,
    verificacion, votacion,
)
from votoseguro.servicios.base import (
    AutenticacionFallida, Contexto, EstadoIncorrecto, HardwareNoDisponible, OpcionInvalida,
)
from votoseguro.servicios.configuracion import Candidatura
from votoseguro.servicios.escrutinio import PartesInsuficientes
from votoseguro.servicios.exportacion import CONTEXTO_PAQUETE

pytestmark = pytest.mark.bd

FRASE = "frase-de-prueba-larga"


@pytest.fixture(scope="module")
def llavero():
    return Llavero.nuevo()


@pytest.fixture
def ctx(bd, llavero):
    return Contexto(bd("vs_app", autocommit=True), llavero, LectorSimulado(), ImpresoraMemoria(), "operador1",
                    CamaraSimulada())


def preparar(ctx, votantes=12, checkpoint_cada=10):
    """Elección con padrón cargado y abierta. Devuelve (eleccion_id, partes, cis)."""
    creada = configuracion.crear_eleccion(
        ctx, "Elección de prueba", [Candidatura("A", "Ana"), Candidatura("B", "Beto")],
        bits=2048, checkpoint_cada=checkpoint_cada)
    eid = creada.eleccion_id
    empadronamiento.iniciar(ctx, eid)
    cis = [str(5_000_000 + i) for i in range(votantes)]
    for ci in cis:
        ctx.lector.colocar_dedo(ci)
        ctx.camara.colocar_persona(ci)
        empadronamiento.registrar_votante(ctx, eid, ci, "Nombre", "Apellido")
    empadronamiento.cerrar_padron(ctx, eid)
    apertura.abrir(ctx, eid)
    return eid, creada.partes, cis


def votar(ctx, eid, ci, opcion):
    ctx.lector.colocar_dedo(ci)
    ctx.camara.colocar_persona(ci)
    return votacion.emitir(ctx, votacion.autenticar_huella(ctx, eid, ci), opcion)


# --- Flujo completo --------------------------------------------------------------------------

def test_eleccion_completa_conforme(ctx, tmp_path):
    eid, partes, cis = preparar(ctx, votantes=12)
    elecciones = ["A", "A", "B", "BLANCO", "A", "B", "NULO", "A", "B", "A", "A"]  # 11 de 12 votan
    papel = Counter(votar(ctx, eid, ci, op).opcion.codigo for ci, op in zip(cis, elecciones))
    cierre.cerrar(ctx, eid)
    acta = escrutinio.escrutar(ctx, eid, [partes[1], partes[2], partes[4]])

    assert acta.contenido["resultados"] == {"A": 6, "B": 3, "BLANCO": 1, "NULO": 1}
    assert repo.obtener_eleccion(ctx.conn, eid).estado == Estado.ESCRUTADA
    assert [c["conteo"] for c in repo.checkpoints(ctx.conn, eid)] == [10, 11]   # cada 10 + final
    tipos = [d.nombre_archivo for d in ctx.impresora.documentos]
    assert tipos.count("acta_zeresima") == tipos.count("acta_cierre") == tipos.count("acta_escrutinio") == 1
    assert sum(t.startswith("parte_mesa01_custodio") for t in tipos) == 5
    assert tipos.count("ausentes_mesa01") == 1

    paquete = exportacion.exportar(ctx, eid, tmp_path, FRASE)
    informe = verificacion.verificar_paquete(paquete.ruta, FRASE, conteo_papel=dict(papel),
                                             huella_esperada=ctx.llavero.huella_dispositivo)
    assert informe.conforme, informe.texto()
    funciones = [o["funcion"] for o in repo.outbox(ctx.conn)]
    assert funciones[0] == "RegistrarEleccion" and funciones[-1] == "RegistrarExportacion"


def test_vvpat_sin_hora_ni_votante_y_bitacora_sin_opcion(ctx):
    eid, _, cis = preparar(ctx, votantes=2)
    comprobante = votar(ctx, eid, cis[0], "B")
    texto = json.dumps(comprobante.__dict__, default=str)
    assert cis[0] not in texto and ":" not in comprobante.codigo
    detalles = [e["detalle"] for e in repo.bitacora_completa(ctx.conn) if e["evento"] == "VOTO_EMITIDO"]
    assert detalles == [{"eleccion": eid, "n": 1}]


# --- Casos de borde de la votación -----------------------------------------------------------

def test_huella_incorrecta_tres_veces_y_excepcion_manual(ctx):
    eid, _, cis = preparar(ctx, votantes=2)
    ctx.lector.colocar_dedo("otra-persona")
    with pytest.raises(AutenticacionFallida):
        votacion.autenticar_huella(ctx, eid, cis[0])
    assert repo.contar_eventos(ctx.conn, eid, "AUTENTICACION_FALLIDA") == 3
    with pytest.raises(ValueError):
        votacion.autorizar_excepcion(ctx, eid, cis[0], "corto")
    sesion = votacion.autorizar_excepcion(ctx, eid, cis[0], "Huella ilegible, CI verificado")
    votacion.emitir(ctx, sesion, "A")
    votar(ctx, eid, cis[1], "B")
    acta = cierre.cerrar(ctx, eid)
    assert acta.contenido["habilitados_por_excepcion"] == 1
    assert acta.contenido["autenticaciones_fallidas"] == 3


def test_doble_voto_y_sesion_reutilizada(ctx):
    eid, _, cis = preparar(ctx, votantes=2)
    ctx.lector.colocar_dedo(cis[0])
    sesion = votacion.autenticar_huella(ctx, eid, cis[0])
    votacion.emitir(ctx, sesion, "A")
    with pytest.raises(Exception, match="ya fue utilizada"):
        votacion.emitir(ctx, sesion, "A")
    with pytest.raises(VotanteNoHabilitado, match="ya emitió"):
        votacion.identificar(ctx, eid, cis[0])
    with pytest.raises(VotanteNoHabilitado, match="no figura"):
        votacion.identificar(ctx, eid, "1234567")


def test_opcion_invalida_no_consume_la_sesion(ctx):
    eid, _, cis = preparar(ctx, votantes=1)
    ctx.lector.colocar_dedo(cis[0])
    sesion = votacion.autenticar_huella(ctx, eid, cis[0])
    with pytest.raises(OpcionInvalida):
        votacion.emitir(ctx, sesion, "Z")
    votacion.emitir(ctx, sesion, "A")
    assert repo.contar_votos(ctx.conn, eid) == 1


def test_impresora_falla_despues_de_registrar_el_voto(ctx):
    eid, _, cis = preparar(ctx, votantes=1)
    ctx.impresora.conectada = False
    with pytest.raises(votacion.ErrorImpresionVVPAT) as e:
        votar(ctx, eid, cis[0], "A")
    assert repo.contar_votos(ctx.conn, eid) == 1              # el voto quedó registrado
    ctx.impresora.conectada = True
    votacion.reimprimir(ctx, e.value.comprobante)
    assert ctx.impresora.vvpat[-1].reimpresion


def test_apertura_exige_hardware(ctx):
    creada = configuracion.crear_eleccion(ctx, "Sin lector", [Candidatura("A", "Ana")], bits=2048)
    empadronamiento.iniciar(ctx, creada.eleccion_id)
    ctx.lector.colocar_dedo("1000000")
    empadronamiento.registrar_votante(ctx, creada.eleccion_id, "1000000", "N", "A")
    empadronamiento.cerrar_padron(ctx, creada.eleccion_id)
    ctx.lector.conectado = False
    with pytest.raises(HardwareNoDisponible, match="lector"):
        apertura.abrir(ctx, creada.eleccion_id)


def test_foto_y_huella_tomadas_antes_por_la_interfaz(ctx):
    """La interfaz toma la foto y la huella paso a paso y las entrega al registrar y al identificar:
    el servicio no vuelve a usar la cámara ni el lector para eso."""
    creada = configuracion.crear_eleccion(ctx, "Paso a paso", [Candidatura("A", "Ana")], bits=2048)
    eid = creada.eleccion_id
    empadronamiento.iniciar(ctx, eid)
    ctx.lector.colocar_dedo("7001001")
    plantilla = empadronamiento.capturar_huella(ctx)
    ctx.camara.conectada = False                         # la cámara ya no se usa al registrar
    empadronamiento.registrar_votante(ctx, eid, "7001001", "Rosa", "Mamani", foto=b"foto-registro",
                                      plantilla=plantilla)
    assert votacion.foto_registro(ctx, eid, "7001001") == b"foto-registro"
    empadronamiento.cerrar_padron(ctx, eid)
    ctx.camara.conectada = True
    apertura.abrir(ctx, eid)
    ctx.camara.conectada = False
    sesion = votacion.autenticar_huella(ctx, eid, "7001001", foto=b"foto-de-hoy")
    assert sesion.metodo == "HUELLA"
    cifrada = ctx.conn.execute("SELECT foto_cifrada FROM padron.presencia WHERE eleccion_id = %s",
                               (eid,)).fetchone()[0]
    assert ctx.llavero.descifrar_personal("foto_presencia", eid, "7001001", bytes(cifrada)) == b"foto-de-hoy"


def test_lector_cerrado_no_captura(ctx):
    lector = LectorSimulado(abierto=False)
    lector.colocar_dedo("7002")
    with pytest.raises(LectorNoDisponible, match="Conectar"):
        lector.capturar()
    lector.abrir()
    assert lector.capturar().startswith(b"SIM1")
    lector.cerrar()
    lector.conectado = False
    with pytest.raises(LectorNoDisponible, match="USB"):
        lector.abrir()


def test_fases_fuera_de_orden(ctx):
    eid, partes, _ = preparar(ctx, votantes=1)
    with pytest.raises(EstadoIncorrecto):
        escrutinio.escrutar(ctx, eid, partes[:3])
    with pytest.raises(EstadoIncorrecto):
        empadronamiento.registrar_votante(ctx, eid, "7777777", "N", "A")


def test_escrutinio_con_dos_partes_falla(ctx):
    eid, partes, cis = preparar(ctx, votantes=1)
    votar(ctx, eid, cis[0], "A")
    cierre.cerrar(ctx, eid)
    with pytest.raises(PartesInsuficientes):
        escrutinio.escrutar(ctx, eid, partes[:2])
    assert repo.contar_eventos(ctx.conn, eid, "ESCRUTINIO_FALLIDO") == 1


def test_usuarios_argon2(ctx):
    usuarios.crear_usuario(ctx.conn, "operador.mesa1", Rol.OPERADOR, "clave-segura-123")
    assert usuarios.autenticar(ctx.conn, "operador.mesa1", "clave-segura-123") == Rol.OPERADOR
    for nombre, clave in [("operador.mesa1", "incorrecta-123"), ("noexiste", "clave-segura-123")]:
        with pytest.raises(usuarios.CredencialesInvalidas):
            usuarios.autenticar(ctx.conn, nombre, clave)
    hash_guardado = ctx.conn.execute("SELECT hash_password FROM eleccion.usuario").fetchone()[0]
    assert hash_guardado.startswith("$argon2id$")


# --- Manipulación del paquete USB ------------------------------------------------------------

@pytest.fixture
def paquete(ctx, tmp_path):
    eid, partes, cis = preparar(ctx, votantes=11)
    for ci, op in zip(cis, "AABABBAAB" + "AB"):
        votar(ctx, eid, ci, op)
    cierre.cerrar(ctx, eid)
    escrutinio.escrutar(ctx, eid, partes[:3])
    return exportacion.exportar(ctx, eid, tmp_path, FRASE).ruta


def _reempacar(ruta, modificar, *, actualizar_manifiesto=False):
    """Simula a un atacante que conoce la frase y modifica el contenido del paquete."""
    contenido = descifrar_con_frase(ruta.read_bytes(), FRASE, CONTEXTO_PAQUETE)
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        archivos = {n: z.read(n) for n in z.namelist()}
    datos = {n: json.loads(d) for n, d in archivos.items() if n.endswith(".json")}
    modificar(datos)
    for n, d in datos.items():
        archivos[n] = json.dumps(d).encode()
    if actualizar_manifiesto:
        from votoseguro.cripto.hashing import sha3
        datos["manifiesto.json"]["archivos"] = {n: sha3(archivos[n]) for n in datos["manifiesto.json"]["archivos"]}
        archivos["manifiesto.json"] = json.dumps(datos["manifiesto.json"]).encode()
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        for n, d in archivos.items():
            z.writestr(n, d)
    ruta.write_bytes(cifrar_con_frase(memoria.getvalue(), FRASE, CONTEXTO_PAQUETE))


def _fallidos(informe):
    return {c.nombre for c in informe.chequeos if c.ok is False}


def test_paquete_integro_es_conforme(paquete):
    assert verificacion.verificar_paquete(paquete, FRASE).conforme


def test_frase_incorrecta(paquete):
    informe = verificacion.verificar_paquete(paquete, "otra-frase-cualquiera")
    assert not informe.conforme and len(informe.chequeos) == 1


def test_resultado_alterado_se_detecta_aunque_se_rehaga_el_manifiesto(paquete):
    def subir_a(d):
        d["actas.json"]["ESCRUTINIO"]["contenido"]["resultados"]["A"] += 5
    _reempacar(paquete, subir_a, actualizar_manifiesto=True)
    fallidos = _fallidos(verificacion.verificar_paquete(paquete, FRASE))
    assert "Firma del manifiesto" in fallidos                          # manifiesto rehecho sin la clave
    assert "Acta ESCRUTINIO: hash y firma del dispositivo" in fallidos


def test_voto_eliminado_se_detecta(paquete):
    _reempacar(paquete, lambda d: d["votos.json"].pop())
    fallidos = _fallidos(verificacion.verificar_paquete(paquete, FRASE))
    assert "Hashes de los archivos del paquete" in fallidos
    assert "Raíz de Merkle = acta de cierre = acta de escrutinio" in fallidos


def test_bitacora_alterada_se_detecta(paquete):
    def editar(d):
        d["bitacora.json"][2]["actor"] = "intruso"
    _reempacar(paquete, editar, actualizar_manifiesto=True)
    fallidos = _fallidos(verificacion.verificar_paquete(paquete, FRASE))
    assert "Bitácora encadenada íntegra y contiene el hash del acta de cierre" in fallidos


def test_padron_alterado_se_detecta(paquete):
    def borrar_participacion(d):
        d["padron.json"][0]["ya_voto"] = False   # ocultar que alguien votó
    _reempacar(paquete, borrar_participacion, actualizar_manifiesto=True)
    fallidos = _fallidos(verificacion.verificar_paquete(paquete, FRASE))
    assert "Padrón: votantes marcados = votos en urna; ausentes = acta de cierre" in fallidos


def test_conteo_de_papel_distinto(paquete):
    informe = verificacion.verificar_paquete(paquete, FRASE, conteo_papel={"A": 1, "B": 0})
    assert "Conteo manual de VVPAT = resultados digitales" in _fallidos(informe)


def test_huella_de_dispositivo_distinta(paquete):
    informe = verificacion.verificar_paquete(paquete, FRASE, huella_esperada="f" * 64)
    assert "Huella del dispositivo = la impresa en la zerésima de papel" in _fallidos(informe)


# --- Demo ------------------------------------------------------------------------------------

def test_demo_completa(bd, tmp_path):
    r = demo.ejecutar(bd("vs_app", autocommit=True), tmp_path, votantes=25, bits=2048, semilla=7,
                      avisar=lambda _m: None)
    assert r.conforme, r.consolidado.texto()
    assert sum(r.resultados.values()) == r.eventos["votos"]
    assert r.eventos["excepciones_manuales"] >= 1 and r.eventos["doble_voto_rechazado"] == 1
    assert (tmp_path / "mesa01" / "impresiones" / "urna_vvpat.pdf").exists()
    assert all(p.exists() for p in r.paquetes)


def test_demo_varias_mesas_detecta_duplicado_y_consolida(bd, tmp_path):
    r = demo.ejecutar(bd("vs_app", autocommit=True), tmp_path, votantes=30, mesas=3, bits=2048, semilla=5,
                      avisar=lambda _m: None)
    assert r.conforme, r.consolidado.texto()
    assert len(r.cruce.duplicados) == 1 and r.eventos["duplicados_inhabilitados"] == 1
    assert sorted(r.consolidado.informes_mesa) == ["01", "02", "03"]
    assert sum(r.resultados.values()) == r.eventos["votos"]
    papel = [c for i in r.consolidado.informes_mesa.values() for c in i.chequeos
             if c.nombre == "Conteo manual de VVPAT = resultados digitales"]
    assert len(papel) == 3 and all(c.ok for c in papel)


def test_demo_es_reproducible_con_semilla(bd, tmp_path):
    conn = bd("vs_app", autocommit=True)
    a = demo.ejecutar(conn, tmp_path / "a", votantes=20, bits=2048, semilla=11, avisar=lambda _m: None)
    b = demo.ejecutar(conn, tmp_path / "b", votantes=20, bits=2048, semilla=11, avisar=lambda _m: None)
    assert a.resultados == b.resultados and a.eventos == b.eventos
