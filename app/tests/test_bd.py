"""Pruebas de la base de datos PostgreSQL: privilegios, solo-inserción, máquina de estados,
emisión atómica del voto, mezcla de la urna y pgaudit (ADR-004, ADR-008)."""

import secrets

import psycopg
import pytest

from votoseguro.cripto import cifrado_voto as cv
from votoseguro.cripto.hashing import sha3
from votoseguro.cripto.merkle import raiz_merkle
from votoseguro.datos import urna
from votoseguro.datos.conexion import (
    EleccionNoAbierta,
    OperacionProhibida,
    TransicionInvalida,
    VotanteNoHabilitado,
)

pytestmark = pytest.mark.bd

ESTADOS_HASTA_ABIERTA = ["EMPADRONAMIENTO", "LISTA", "ABIERTA"]


def crear_eleccion(conn, votantes=5, clave_publica=b"pub", checkpoint_cada=10) -> str:
    """Crea una elección con opciones y padrón, todavía en EMPADRONAMIENTO."""
    eid = conn.execute(
        """INSERT INTO eleccion.eleccion (eleccion_global, mesa, nombre, sal_padron, hash_configuracion, definicion,
                                          clave_publica, clave_privada_cifrada, umbral, partes, checkpoint_cada)
           VALUES (gen_random_uuid(), '01', 'Directorio 2026', repeat('ab', 16), repeat('c', 64), '{}',
                   %s, %s, 3, 5, %s) RETURNING id::text""",
        (clave_publica, b"cifrada", checkpoint_cada),
    ).fetchone()[0]
    for orden, (codigo, tipo) in enumerate([("A", "CANDIDATO"), ("B", "CANDIDATO"), ("BLANCO", "BLANCO")], 1):
        conn.execute(
            "INSERT INTO eleccion.opcion (eleccion_id, codigo, nombre, orden, tipo) VALUES (%s, %s, %s, %s, %s)",
            (eid, codigo, f"Opción {codigo}", orden, tipo),
        )
    conn.execute("UPDATE eleccion.eleccion SET estado = 'EMPADRONAMIENTO' WHERE id = %s", (eid,))
    for i in range(votantes):
        conn.execute(
            "INSERT INTO padron.votante (eleccion_id, ci, nombres, apellidos) VALUES (%s, %s, 'N', 'A')",
            (eid, f"{1000000 + i}"),
        )
    return eid


def abrir(conn, eid):
    for estado in ESTADOS_HASTA_ABIERTA[1:]:
        conn.execute("UPDATE eleccion.eleccion SET estado = %s WHERE id = %s", (estado, eid))


def voto_falso():
    contenido = secrets.token_bytes(32)
    return contenido, sha3(contenido)


# --- Flujo de votación -----------------------------------------------------------------------

def test_emision_atomica_marca_votante_e_inserta_voto(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    abrir(app, eid)
    voto, h = voto_falso()
    assert urna.emitir_voto(app, eid, "1000000", voto, h) == 1
    app.commit()
    ya_voto = app.execute(
        "SELECT ya_voto FROM padron.votante WHERE eleccion_id = %s AND ci = '1000000'", (eid,)
    ).fetchone()[0]
    assert ya_voto is True
    assert urna.hashes_votos(app, eid) == [h]


def test_doble_voto_rechazado_y_sin_efectos(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    abrir(app, eid)
    urna.emitir_voto(app, eid, "1000000", *voto_falso())
    app.commit()
    with pytest.raises(VotanteNoHabilitado):
        urna.emitir_voto(app, eid, "1000000", *voto_falso())
    app.rollback()
    assert urna.huella(app).conteo == 1


@pytest.mark.parametrize("ci", ["9999999", "1000001"])
def test_votante_inexistente_o_inhabilitado(bd, ci):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    app.execute("UPDATE padron.votante SET habilitado = false WHERE ci = '1000001'")
    abrir(app, eid)
    with pytest.raises(VotanteNoHabilitado):
        urna.emitir_voto(app, eid, ci, *voto_falso())


def test_no_se_vota_si_la_eleccion_no_esta_abierta(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    with pytest.raises(EleccionNoAbierta):
        urna.emitir_voto(app, eid, "1000000", *voto_falso())


# --- Máquina de estados y padrón -------------------------------------------------------------

def test_transicion_invalida(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    app.commit()
    with pytest.raises(psycopg.Error) as e:
        app.execute("UPDATE eleccion.eleccion SET estado = 'ESCRUTADA' WHERE id = %s", (eid,))
    assert e.value.sqlstate == "VS003"


def test_padron_cerrado_despues_de_lista(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    app.execute("UPDATE eleccion.eleccion SET estado = 'LISTA' WHERE id = %s", (eid,))
    with pytest.raises(psycopg.Error) as e:
        app.execute(
            "INSERT INTO padron.votante (eleccion_id, ci, nombres, apellidos) VALUES (%s, '7777777', 'X', 'Y')",
            (eid,),
        )
    assert e.value.sqlstate == "VS003"


def test_datos_criptograficos_inmutables(bd):
    admin = bd("postgres")
    eid = crear_eleccion(admin)
    with pytest.raises(psycopg.Error) as e:
        admin.execute("UPDATE eleccion.eleccion SET clave_publica = 'otra' WHERE id = %s", (eid,))
    assert e.value.sqlstate == "VS100"


# --- Mínimo privilegio -----------------------------------------------------------------------

@pytest.mark.parametrize("sentencia", [
    "INSERT INTO urna.voto (eleccion_id, voto_cifrado, hash_voto) VALUES (%(e)s, 'x', repeat('a', 64))",
    "UPDATE padron.votante SET ya_voto = true WHERE eleccion_id = %(e)s",
    "DELETE FROM urna.voto",
    "DELETE FROM auditoria.bitacora",
    "TRUNCATE urna.voto",
])
def test_vs_app_no_tiene_privilegios_directos(bd, sentencia):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    abrir(app, eid)
    app.commit()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app.execute(sentencia, {"e": eid})


@pytest.mark.parametrize("sentencia", [
    "UPDATE urna.voto SET voto_cifrado = 'alterado'",
    "DELETE FROM urna.voto",
    "TRUNCATE urna.voto",
])
def test_ni_el_superusuario_modifica_votos_sin_desactivar_triggers(bd, sentencia):
    admin = bd("postgres")
    eid = crear_eleccion(admin)
    abrir(admin, eid)
    urna.emitir_voto(admin, eid, "1000000", *voto_falso())
    admin.commit()
    with pytest.raises(psycopg.Error) as e:
        admin.execute(sentencia)
    assert e.value.sqlstate == "VS100"


def test_auditor_solo_lectura_y_sin_plantillas(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app)
    app.commit()
    auditor = bd("vs_auditor")
    assert auditor.execute("SELECT count(*) FROM padron.votante WHERE ya_voto").fetchone()[0] == 0
    auditor.rollback()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        auditor.execute("SELECT plantilla_cifrada FROM padron.votante")
    auditor.rollback()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        auditor.execute(
            "INSERT INTO padron.votante (eleccion_id, ci, nombres, apellidos) VALUES (%s, '1', 'x', 'y')", (eid,)
        )


# --- Secreto del voto: vulnerabilidad de xmin y mezcla de la urna ---------------------------

def _emitir_n(conn, eid, n):
    """Emite n votos, uno por transacción (como en la jornada real). Devuelve los hashes en
    el orden en que se emitieron."""
    orden = []
    for i in range(n):
        voto, h = voto_falso()
        urna.emitir_voto(conn, eid, f"{1000000 + i}", voto, h)
        conn.commit()
        orden.append(h)
    return orden


def test_sin_mezcla_xmin_revela_orden_y_vincula_votante(bd):
    """Demuestra el riesgo que motiva la mezcla (ADR-008)."""
    app = bd("vs_app")
    eid = crear_eleccion(app, votantes=20)
    abrir(app, eid)
    app.commit()
    orden = _emitir_n(app, eid, 20)
    admin = bd("postgres")
    por_xmin = [r[0] for r in admin.execute(
        "SELECT hash_voto FROM urna.voto ORDER BY xmin::text::bigint").fetchall()]
    assert por_xmin == orden  # el orden de emisión es recuperable
    vinculo = admin.execute(
        """SELECT count(*) FROM urna.voto v JOIN padron.votante p ON p.xmin = v.xmin
            WHERE p.ya_voto""").fetchone()[0]
    assert vinculo == 20      # cada votante queda unido a su voto por xmin


def test_mezcla_borra_orden_y_vinculo_sin_alterar_contenido(bd):
    app = bd("vs_app")
    eid = crear_eleccion(app, votantes=30)
    abrir(app, eid)
    app.commit()
    orden = _emitir_n(app, eid, 30)
    antes = urna.huella(app)
    raiz_antes = raiz_merkle(urna.hashes_votos(app, eid))

    despues = urna.mezclar(app)
    app.commit()

    assert despues == antes                                     # mismo contenido
    assert raiz_merkle(urna.hashes_votos(app, eid)) == raiz_antes
    admin = bd("postgres")
    assert admin.execute("SELECT count(DISTINCT xmin::text) FROM urna.voto").fetchone()[0] == 1
    fisico = [r[0] for r in admin.execute("SELECT hash_voto FROM urna.voto ORDER BY ctid").fetchall()]
    assert fisico != orden                                      # orden físico aleatorio
    vinculo = admin.execute(
        "SELECT count(*) FROM urna.voto v JOIN padron.votante p ON p.xmin = v.xmin").fetchone()[0]
    assert vinculo == 0


def test_votos_cifrados_reales_y_raiz_de_merkle(bd):
    clave = cv.generar_clave_eleccion(2048)
    app = bd("vs_app")
    eid = crear_eleccion(app, votantes=3, clave_publica=cv.publica_a_pem(clave.public_key()))
    abrir(app, eid)
    app.commit()
    elegidos = [b"A", b"B", b"A"]
    for i, opcion in enumerate(elegidos):
        cifrado = cv.cifrar_voto(clave.public_key(), eid, opcion)
        urna.emitir_voto(app, eid, f"{1000000 + i}", cifrado, sha3(cifrado))
        app.commit()
    urna.mezclar(app)
    app.commit()
    filas = app.execute("SELECT voto_cifrado, hash_voto FROM urna.voto").fetchall()
    assert all(sha3(bytes(v)) == h for v, h in filas)
    assert sorted(cv.descifrar_voto(clave, eid, bytes(v)) for v, _ in filas) == sorted(elegidos)


# --- pgaudit ---------------------------------------------------------------------------------

def test_pgaudit_registra_escrituras_sin_parametros(bd, instancia_pg):
    app = bd("vs_app")
    eid = crear_eleccion(app, votantes=1)
    abrir(app, eid)
    app.commit()
    ci = "1000000"
    urna.emitir_voto(app, eid, ci, *voto_falso())
    app.commit()
    log = instancia_pg["log"].read_text(errors="replace")
    assert "AUDIT: SESSION" in log
    assert "padron.votante" in log
    assert f"'{ci}'" not in log  # el CI (parámetro) no queda en el log
