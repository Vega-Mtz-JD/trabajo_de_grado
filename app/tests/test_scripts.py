"""Pruebas de los scripts de producción en modo SIMULACIÓN (no requieren root ni modifican nada)."""

import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def ejecutar(nombre, *args):
    r = subprocess.run(["bash", str(SCRIPTS / nombre), *args], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def test_hardening_simula_por_defecto_y_exige_confirmacion():
    codigo, salida = ejecutar("hardening_offline.sh")
    assert codigo == 0 and "SIMULACIÓN" in salida
    for esperado in ("listen_addresses = ''", "pgaudit.log_parameter = off", "peer map=votoseguro",
                     "votoseguro    kiosco        vs_app", "install bluetooth /bin/false", "policy drop",
                     "-k votoseguro_llavero", "Lista de verificación MANUAL"):
        assert esperado in salida, esperado
    assert "flush ruleset" not in salida.replace('NO se usa "flush ruleset"', "")   # respetar reglas de Docker
    codigo, salida = ejecutar("hardening_offline.sh", "--aplicar")
    assert codigo == 2 and "--confirmo-equipo-de-votacion" in salida


@pytest.mark.parametrize("opcion", ["--desconocida"])
def test_opciones_desconocidas(opcion):
    assert ejecutar("hardening_offline.sh", opcion)[0] == 2
    assert ejecutar("configurar_kiosco.sh", opcion)[0] == 2


def test_kiosco_genera_sway_con_dos_monitores_y_seat_de_cabina():
    codigo, salida = ejecutar("configurar_kiosco.sh", "--salida-mesa", "eDP-1", "--salida-cabina", "HDMI-A-1",
                              "--entrada-cabina", "1133:49970:Mouse")
    assert codigo == 0 and "SIMULACIÓN" in salida
    for esperado in ('seat cabina attach "1133:49970:Mouse"', 'map_to_output HDMI-A-1',
                     "Panel de mesa\\$\"] move container to output eDP-1, fullscreen enable",
                     "Cabina de votación\\$\"] move container to output HDMI-A-1, fullscreen enable",
                     "--autologin kiosco", "votoseguro-ui --kiosco --fabric", "votoseguro-puente.service",
                     "User=kiosco", "VOTOSEGURO_SIN_COMPILAR=1"):
        assert esperado.replace("\\$", "$") in salida, esperado


def test_titulos_de_ventana_coinciden_con_las_reglas_de_sway():
    """Las reglas de sway buscan las ventanas por título: deben coincidir con los de la aplicación."""
    codigo, salida = ejecutar("configurar_kiosco.sh")
    ui = Path(__file__).resolve().parents[1] / "src/votoseguro/ui"
    assert '"VOTO SEGURO — Panel de mesa"' in (ui / "ventana.py").read_text()
    assert '"VOTO SEGURO — Cabina de votación"' in (ui / "kiosco.py").read_text()
    assert "VOTO SEGURO — Panel de mesa$" in salida and "VOTO SEGURO — Cabina de votación$" in salida
