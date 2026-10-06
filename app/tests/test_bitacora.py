"""Pruebas de la bitácora encadenada: integridad, detección de manipulación y secreto del voto."""

import psycopg
import pytest

from votoseguro.auditoria import bitacora
from votoseguro.datos.conexion import IntegridadVulnerada

pytestmark = pytest.mark.bd


def _llenar(conn, n=5):
    entradas = [
        bitacora.registrar(conn, "operador1", "VOTANTE_AUTENTICADO", {"n": i, "ci": f"{1000000 + i}"})
        for i in range(n)
    ]
    conn.commit()
    return entradas


def test_cadena_integra(bd):
    app = bd("vs_app")
    entradas = _llenar(app)
    assert entradas[0].hash_anterior == bitacora.HASH_GENESIS
    assert all(b.hash_anterior == a.hash for a, b in zip(entradas, entradas[1:]))
    resultado = bitacora.verificar(app, ultimo_hash_anclado=entradas[-1].hash)
    assert resultado.integra and resultado.entradas == 5


def test_detecta_contenido_alterado_por_superusuario(bd):
    """Simula a un atacante con superusuario que desactiva los triggers y edita una entrada."""
    app = bd("vs_app")
    _llenar(app)
    admin = bd("postgres", autocommit=True)
    admin.execute("ALTER TABLE auditoria.bitacora DISABLE TRIGGER USER")
    admin.execute("""UPDATE auditoria.bitacora SET detalle = '{"n": 2, "ci": "9999999"}' WHERE seq = 3""")
    resultado = bitacora.verificar(app)
    assert not resultado.integra
    assert resultado.primera_falla == 3
    assert resultado.motivo == "contenido alterado"


def test_detecta_entrada_intermedia_eliminada(bd):
    app = bd("vs_app")
    _llenar(app)
    admin = bd("postgres", autocommit=True)
    admin.execute("ALTER TABLE auditoria.bitacora DISABLE TRIGGER USER")
    admin.execute("DELETE FROM auditoria.bitacora WHERE seq = 2")
    resultado = bitacora.verificar(app)
    assert not resultado.integra and resultado.primera_falla == 3


def test_eliminar_las_ultimas_solo_se_detecta_con_el_hash_anclado(bd):
    app = bd("vs_app")
    entradas = _llenar(app)
    admin = bd("postgres", autocommit=True)
    admin.execute("ALTER TABLE auditoria.bitacora DISABLE TRIGGER USER")
    admin.execute("DELETE FROM auditoria.bitacora WHERE seq >= 4")
    assert bitacora.verificar(app).integra  # la cadena restante es consistente…
    resultado = bitacora.verificar(app, ultimo_hash_anclado=entradas[-1].hash)
    assert not resultado.integra             # …pero el ancla externa delata el borrado


def test_la_bd_rechaza_entradas_no_encadenadas(bd):
    app = bd("vs_app")
    _llenar(app, 2)
    with pytest.raises(psycopg.Error) as e:
        app.execute(
            """INSERT INTO auditoria.bitacora (momento, actor, evento, hash_anterior, hash)
               VALUES (now(), 'x', 'FALSO', repeat('0', 64), repeat('f', 64))"""
        )
    assert e.value.sqlstate == "VS102"


def test_la_bd_impide_modificar_la_bitacora(bd):
    app = bd("vs_app")
    _llenar(app, 1)
    admin = bd("postgres")
    with pytest.raises(psycopg.Error) as e:
        admin.execute("UPDATE auditoria.bitacora SET actor = 'otro'")
    assert e.value.sqlstate == "VS100"


@pytest.mark.parametrize("clave", ["voto", "hash_voto", "voto_id", "opcion"])
def test_no_registra_datos_del_voto(bd, clave):
    app = bd("vs_app")
    with pytest.raises(ValueError, match="datos del voto"):
        bitacora.registrar(app, "sistema", "VOTO_EMITIDO", {clave: "x"})


def test_error_de_integridad_se_traduce(bd):
    """El SQLSTATE VS102 de la BD se convierte en la excepción de negocio IntegridadVulnerada."""
    from votoseguro.datos.conexion import traducir_error

    app = bd("vs_app")
    _llenar(app, 1)
    with pytest.raises(psycopg.Error) as e:
        app.execute(
            """INSERT INTO auditoria.bitacora (momento, actor, evento, hash_anterior, hash)
               VALUES (now(), 'x', 'FALSO', repeat('0', 64), repeat('e', 64))"""
        )
    assert isinstance(traducir_error(e.value), IntegridadVulnerada)
