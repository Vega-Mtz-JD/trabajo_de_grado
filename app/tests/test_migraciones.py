"""Pruebas de las migraciones versionadas del esquema (ADR-011)."""

import shutil
from importlib import resources

import psycopg
import pytest

from votoseguro.datos import migraciones
from votoseguro.datos.migraciones import ErrorMigracion

pytestmark = pytest.mark.bd


def carpeta_con_copia(tmp_path):
    """Copia de las migraciones del paquete, para agregar o alterar archivos en la prueba."""
    destino = tmp_path / "migraciones"
    destino.mkdir()
    for f in resources.files("votoseguro.datos").joinpath("migraciones").iterdir():
        if f.name.endswith(".sql"):
            shutil.copy(str(f), destino / f.name)
    return destino


def test_bd_nueva_queda_en_la_ultima_version_y_es_idempotente(bd):
    admin = bd("postgres", autocommit=True)
    assert [e for _, _, e in migraciones.estado(admin)] == ["APLICADA"] * len(migraciones.disponibles())
    assert migraciones.migrar(admin) == []


def test_nueva_migracion_se_aplica_en_orden(bd, tmp_path):
    carpeta = carpeta_con_copia(tmp_path)
    (carpeta / "0002_indice_bitacora_evento.sql").write_text(
        "CREATE INDEX bitacora_evento ON auditoria.bitacora (evento);")
    admin = bd("postgres", autocommit=True)
    assert migraciones.estado(admin, carpeta)[-1] == (2, "indice_bitacora_evento", "PENDIENTE")
    assert migraciones.migrar(admin, carpeta) == ["0002_indice_bitacora_evento"]
    duenio = admin.execute("SELECT tableowner FROM pg_indexes i JOIN pg_tables t USING (schemaname, tablename) "
                           "WHERE indexname = 'bitacora_evento'").fetchone()[0]
    assert duenio == "vs_propietario"


def test_migracion_aplicada_y_modificada_se_rechaza(bd, tmp_path):
    carpeta = carpeta_con_copia(tmp_path)
    archivo = next(carpeta.glob("0001_*.sql"))
    archivo.write_text(archivo.read_text() + "\n-- cambio posterior\n")
    admin = bd("postgres", autocommit=True)
    assert migraciones.estado(admin, carpeta)[0][2] == "MODIFICADA"
    with pytest.raises(ErrorMigracion, match="modificada"):
        migraciones.migrar(admin, carpeta)


def test_migracion_fallida_no_deja_cambios(bd, tmp_path):
    carpeta = carpeta_con_copia(tmp_path)
    (carpeta / "0002_rota.sql").write_text("CREATE TABLE auditoria.temporal (x int); SELECT * FROM no_existe;")
    admin = bd("postgres", autocommit=True)
    with pytest.raises(psycopg.Error):
        migraciones.migrar(admin, carpeta)
    assert admin.execute("SELECT to_regclass('auditoria.temporal')").fetchone()[0] is None
    assert 2 not in migraciones.aplicadas(admin)


def test_numeracion_con_huecos(tmp_path):
    carpeta = carpeta_con_copia(tmp_path)
    (carpeta / "0003_salto.sql").write_text("SELECT 1;")
    with pytest.raises(ErrorMigracion, match="sin huecos"):
        migraciones.disponibles(carpeta)


def test_linea_base_para_bd_instalada_sin_migraciones(bd):
    """Una BD instalada antes del Sprint 6 (sin meta.migracion) se reconoce sin reaplicar nada."""
    admin = bd("postgres", autocommit=True)
    admin.execute("DROP SCHEMA meta CASCADE")
    assert migraciones.migrar(admin) == ["0001_esquema_inicial (línea base)"]
    assert migraciones.estado(admin)[0][2] == "LÍNEA BASE"


def test_admin_bd_migra_pero_no_hereda_privilegios_de_propietario(bd, instancia_pg):
    admin = bd("postgres", autocommit=True)
    admin.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tecnico') "
                  "THEN CREATE ROLE tecnico LOGIN; END IF; END $$")
    admin.execute("GRANT vs_admin_bd TO tecnico")
    tecnico = psycopg.connect(host=instancia_pg["host"], dbname=bd.nombre, user="tecnico", autocommit=True)
    try:
        assert migraciones.migrar(tecnico) == []                      # puede migrar (SET ROLE)…
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            tecnico.execute("SELECT * FROM padron.votante")             # …pero no lee datos en uso normal
    finally:
        tecnico.close()
