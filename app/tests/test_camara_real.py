"""Cámara web real (Qt Multimedia). Enciende la cámara: solo se ejecuta si se pide explícitamente.

    VOTOSEGURO_PROBAR_CAMARA=1 pytest tests/test_camara_real.py
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.skipif(os.environ.get("VOTOSEGURO_PROBAR_CAMARA") != "1",
                                reason="enciende la cámara web: use VOTOSEGURO_PROBAR_CAMARA=1")


def test_captura_jpeg_de_la_camara_web(qapp):
    from votoseguro.hardware.camara_qt import CamaraQt, hay_camara

    if not hay_camara():
        pytest.skip("no hay cámara web")
    camara = CamaraQt()
    try:
        foto = camara.capturar()
    finally:
        camara.apagar()
    assert foto[:3] == b"\xff\xd8\xff" and len(foto) > 1000      # JPEG


def test_interfaz_elige_camara_simulada_si_se_pide(qapp):
    from votoseguro.hardware.camara import CamaraSimulada
    from votoseguro.ui.app import elegir_camara

    assert isinstance(elegir_camara("simulada"), CamaraSimulada)
