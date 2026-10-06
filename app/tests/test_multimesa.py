"""Pruebas de varias urnas, foto de registro y de presencia, cruce de padrones y consolidación
(ADR-009, RF01–RF04, RF07, RF09, RF13)."""

import psycopg
import pytest

from votoseguro.cripto.llavero import Llavero
from votoseguro.datos import repositorio as repo
from votoseguro.hardware.camara import CamaraSimulada
from votoseguro.hardware.huella import LectorSimulado
from votoseguro.hardware.impresora import ImpresoraMemoria
from votoseguro.servicios import (
    apertura, cierre, configuracion, consolidacion, empadronamiento, escrutinio, exportacion, votacion,
)
from votoseguro.servicios.base import AutenticacionFallida, Contexto, HardwareNoDisponible
from votoseguro.servicios.configuracion import Candidatura, DefinicionInvalida

pytestmark = pytest.mark.bd

FRASE = "frase-de-prueba-larga"
PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def equipo(bd):
    """Fábrica de urnas: cada llamada simula un equipo distinto (llavero, periféricos)."""
    conn = bd("vs_app", autocommit=True)

    def nuevo(nombre="operador"):
        return Contexto(conn, Llavero.nuevo(), LectorSimulado(), ImpresoraMemoria(), nombre, CamaraSimulada())
    return nuevo


def definicion(mesas=("01", "02")):
    return configuracion.definir_eleccion("Elección multimesa", [Candidatura("A", "Ana"), Candidatura("B", "Beto")],
                                          mesas=list(mesas))


def empadronar(ctx, eid, cis):
    for ci in cis:
        ctx.camara.colocar_persona(ci)
        ctx.lector.colocar_dedo(ci)
        empadronamiento.registrar_votante(ctx, eid, ci, "Nombre", f"Apellido {ci}")


def votar(ctx, eid, ci, opcion):
    ctx.camara.colocar_persona(ci)
    ctx.lector.colocar_dedo(ci)
    return votacion.emitir(ctx, votacion.autenticar_huella(ctx, eid, ci), opcion)


def mesa_completa(ctx, defi, mesa, cis, votos, carpeta):
    """Instala, empadrona, abre, vota, cierra, escruta y exporta una mesa. Devuelve el paquete."""
    creada = configuracion.instalar_mesa(ctx, defi, mesa, bits=2048)
    eid = creada.eleccion_id
    empadronamiento.iniciar(ctx, eid)
    empadronar(ctx, eid, cis)
    empadronamiento.cerrar_padron(ctx, eid)
    apertura.abrir(ctx, eid)
    for ci, op in zip(cis, votos):
        votar(ctx, eid, ci, op)
    cierre.cerrar(ctx, eid)
    escrutinio.escrutar(ctx, eid, creada.partes[:3])
    return exportacion.exportar(ctx, eid, carpeta, FRASE).ruta


# --- Definición exportable -------------------------------------------------------------------

def test_definicion_ida_y_vuelta_con_huella(equipo, tmp_path):
    creador = equipo()
    defi = definicion()
    h = configuracion.exportar_definicion(creador, defi, tmp_path / "d.vsd", FRASE)
    importada = configuracion.importar_definicion(tmp_path / "d.vsd", FRASE, creador.llavero.huella_dispositivo)
    assert importada == defi and configuracion.hash_definicion(importada) == h
    assert creador.impresora.documentos[-1].nombre_archivo == "definicion_eleccion"


def test_definicion_de_otro_equipo_frase_incorrecta_o_alterada(equipo, tmp_path):
    creador, otro = equipo(), equipo()
    ruta = tmp_path / "d.vsd"
    configuracion.exportar_definicion(creador, definicion(), ruta, FRASE)
    with pytest.raises(DefinicionInvalida, match="equipo esperado"):
        configuracion.importar_definicion(ruta, FRASE, otro.llavero.huella_dispositivo)
    with pytest.raises(DefinicionInvalida):
        configuracion.importar_definicion(ruta, "otra-frase-cualquiera")
    datos = bytearray(ruta.read_bytes())
    datos[-5] ^= 0x01
    ruta.write_bytes(bytes(datos))
    with pytest.raises(DefinicionInvalida):
        configuracion.importar_definicion(ruta, FRASE)


def test_mesa_fuera_de_la_definicion(equipo):
    with pytest.raises(DefinicionInvalida, match="no figura"):
        configuracion.instalar_mesa(equipo(), definicion(["01"]), "07", bits=2048)


def test_cada_mesa_tiene_su_propia_clave(equipo):
    defi = definicion()
    a = configuracion.instalar_mesa(equipo(), defi, "01", bits=2048)
    ctx = equipo()
    b = configuracion.instalar_mesa(ctx, defi, "02", bits=2048)
    ea, eb = repo.obtener_eleccion(ctx.conn, a.eleccion_id), repo.obtener_eleccion(ctx.conn, b.eleccion_id)
    assert ea.eleccion_global == eb.eleccion_global and ea.hash_configuracion == eb.hash_configuracion
    assert ea.clave_publica_pem != eb.clave_publica_pem


# --- Foto de registro y de presencia ---------------------------------------------------------

def test_foto_de_registro_cifrada_y_visible_para_el_operador(equipo):
    ctx = equipo()
    eid = configuracion.instalar_mesa(ctx, definicion(["01"]), "01", bits=2048).eleccion_id
    empadronamiento.iniciar(ctx, eid)
    empadronar(ctx, eid, ["4000001"])
    guardada = bytes(repo.obtener_votante(ctx.conn, eid, "4000001")["foto_cifrada"])
    assert PNG not in guardada                                    # cifrada en la BD
    assert votacion.foto_registro(ctx, eid, "4000001").startswith(PNG)


def test_empadronar_sin_camara_falla(equipo):
    ctx = equipo()
    ctx.camara.conectada = False
    eid = configuracion.instalar_mesa(ctx, definicion(["01"]), "01", bits=2048).eleccion_id
    empadronamiento.iniciar(ctx, eid)
    with pytest.raises(HardwareNoDisponible, match="cámara"):
        empadronar(ctx, eid, ["4000001"])


def test_presencia_con_foto_solo_si_se_identifica(equipo):
    ctx = equipo()
    eid = configuracion.instalar_mesa(ctx, definicion(["01"]), "01", bits=2048).eleccion_id
    empadronamiento.iniciar(ctx, eid)
    empadronar(ctx, eid, ["4000001", "4000002", "4000003"])
    empadronamiento.cerrar_padron(ctx, eid)
    apertura.abrir(ctx, eid)

    votar(ctx, eid, "4000001", "A")
    ctx.lector.colocar_dedo("impostor")
    with pytest.raises(AutenticacionFallida):
        votacion.autenticar_huella(ctx, eid, "4000002")             # huella falla: no hay presencia
    ctx.camara.colocar_persona("4000003")
    ctx.lector.colocar_dedo("4000003")
    votacion.autenticar_huella(ctx, eid, "4000003")                 # se identifica y se va sin votar
    votacion.autenticar_huella(ctx, eid, "4000003")                 # vuelve: se conserva la primera

    filas = {f["ci"]: f for f in repo.padron_completo(ctx.conn, eid)}
    assert filas["4000001"]["presente"] and filas["4000001"]["ya_voto"]
    assert not filas["4000002"]["presente"]
    assert filas["4000003"]["presente"] and not filas["4000003"]["ya_voto"]
    assert repo.contar_eventos(ctx.conn, eid, "PRESENCIA_REGISTRADA") == 2
    foto = ctx.conn.execute("SELECT foto_cifrada FROM padron.presencia WHERE ci = '4000001'").fetchone()[0]
    assert ctx.llavero.descifrar_personal("foto_presencia", eid, "4000001", bytes(foto)).startswith(PNG)

    acta = cierre.cerrar(ctx, eid)
    assert acta.contenido["ausentes"] == 2 and acta.contenido["presentes_sin_votar"] == 1
    lista = ctx.impresora.documentos[-1]
    assert lista.nombre_archivo == "ausentes_mesa01"
    assert any("4000002" in linea for linea in lista.lineas)
    assert any("4000003" in linea and "NO votaron" in linea for linea in lista.lineas)


def test_presencia_solo_con_eleccion_abierta_y_auditor_sin_fotos(equipo, bd):
    ctx = equipo()
    eid = configuracion.instalar_mesa(ctx, definicion(["01"]), "01", bits=2048).eleccion_id
    empadronamiento.iniciar(ctx, eid)
    empadronar(ctx, eid, ["4000001"])
    with pytest.raises(psycopg.Error) as e:
        ctx.conn.execute("INSERT INTO padron.presencia (eleccion_id, ci, metodo) VALUES (%s, '4000001', 'HUELLA')",
                         (eid,))
    assert e.value.sqlstate == "VS002"
    auditor = bd("vs_auditor")
    for sql in ("SELECT foto_cifrada FROM padron.votante", "SELECT foto_cifrada FROM padron.presencia"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            auditor.execute(sql)
        auditor.rollback()


# --- Cruce de padrones -----------------------------------------------------------------------

def test_cruce_detecta_empadronado_en_dos_mesas(equipo, tmp_path):
    defi = definicion()
    m1, m2 = equipo("op1"), equipo("op2")
    e1 = configuracion.instalar_mesa(m1, defi, "01", bits=2048).eleccion_id
    e2 = configuracion.instalar_mesa(m2, defi, "02", bits=2048).eleccion_id
    for ctx, eid, cis in ((m1, e1, ["4000001", "4000002"]), (m2, e2, ["4000003", "4000001"])):
        empadronamiento.iniciar(ctx, eid)
        empadronar(ctx, eid, cis)
    rutas = [empadronamiento.exportar_resumen_padron(m1, e1, tmp_path, FRASE),
             empadronamiento.exportar_resumen_padron(m2, e2, tmp_path, FRASE)]
    cruce = empadronamiento.cruzar_padrones(rutas, FRASE)
    assert cruce.duplicados == {"4000001": ["01", "02"]} and not cruce.limpio

    empadronamiento.inhabilitar_votante(m2, e2, "4000001", "Duplicado: también en la mesa 01")
    rutas[1] = empadronamiento.exportar_resumen_padron(m2, e2, tmp_path, FRASE)
    assert empadronamiento.cruzar_padrones(rutas, FRASE).limpio
    assert repo.contar_eventos(m2.conn, e2, "VOTANTE_INHABILITADO") == 1


def test_cruce_rechaza_elecciones_distintas(equipo, tmp_path):
    rutas = []
    for i in range(2):
        ctx = equipo()
        eid = configuracion.instalar_mesa(ctx, definicion(["01"]), "01", bits=2048).eleccion_id
        empadronamiento.iniciar(ctx, eid)
        empadronar(ctx, eid, [f"400000{i}"])
        rutas.append(empadronamiento.exportar_resumen_padron(ctx, eid, tmp_path / str(i), FRASE))
    with pytest.raises(Exception, match="elecciones o definiciones distintas"):
        empadronamiento.cruzar_padrones(rutas, FRASE)


# --- Consolidación ---------------------------------------------------------------------------

def test_consolidacion_de_dos_mesas(equipo, tmp_path):
    defi = definicion()
    p1 = mesa_completa(equipo("op1"), defi, "01", ["4000001", "4000002", "4000003"], "AAB", tmp_path)
    p2 = mesa_completa(equipo("op2"), defi, "02", ["4000004", "4000005"], "BB", tmp_path)
    r = consolidacion.consolidar([p1, p2], FRASE)
    assert r.conforme, r.texto()
    assert r.resultados_mesa["01"]["A"] == 2 and r.resultados_mesa["02"]["B"] == 2
    assert r.total == {"A": 2, "B": 3, "BLANCO": 0, "NULO": 0}


def test_consolidacion_detecta_voto_en_dos_mesas_y_mesa_faltante(equipo, tmp_path):
    defi = definicion(["01", "02", "03"])
    # Sin cruce de padrones: el mismo CI se empadronó y votó en las mesas 01 y 02
    p1 = mesa_completa(equipo("op1"), defi, "01", ["4000001", "4000002"], "AB", tmp_path)
    p2 = mesa_completa(equipo("op2"), defi, "02", ["4000001", "4000003"], "AA", tmp_path)
    r = consolidacion.consolidar([p1, p2], FRASE)
    fallidos = {c.nombre: c.detalle for c in r.global_.chequeos if c.ok is False}
    assert "4000001" in fallidos["Ningún CI votó en más de una mesa"]
    assert "03" in fallidos["Están los paquetes de todas las mesas definidas"]
    assert not r.conforme


def test_consolidacion_rechaza_paquete_repetido_y_otra_eleccion(equipo, tmp_path):
    p1 = mesa_completa(equipo("op1"), definicion(["01"]), "01", ["4000001"], "A", tmp_path / "x")
    p2 = mesa_completa(equipo("op2"), definicion(["01", "02"]), "02", ["4000002"], "B", tmp_path / "y")
    r = consolidacion.consolidar([p1, p1], FRASE)
    assert "Mesa 01 entregada una sola vez" in {c.nombre for c in r.global_.chequeos if c.ok is False}
    r = consolidacion.consolidar([p1, p2], FRASE)
    assert "Todas las mesas son de la misma elección y definición" in {
        c.nombre for c in r.global_.chequeos if c.ok is False}
