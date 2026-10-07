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


def test_vista_en_vivo_sin_ventanas_nativas_y_se_apaga(qapp, qtbot):
    """La imagen en vivo llega como QImage (sin QVideoWidget) y la cámara se apaga al tomar la foto."""
    from votoseguro.hardware.camara_qt import CamaraQt, hay_camara

    if not hay_camara():
        pytest.skip("no hay cámara web")
    camara = CamaraQt()
    cuadros = []
    camara.al_recibir(cuadros.append)
    camara.encender()
    try:
        qtbot.waitUntil(lambda: len(cuadros) >= 3, timeout=8000)
        assert not cuadros[-1].isNull()
        foto = camara.capturar()                  # encendida: usa el cuadro actual
        assert foto[:3] == b"\xff\xd8\xff" and camara.encendida()
    finally:
        camara.apagar()
    assert not camara.encendida()
    assert not [w for w in qapp.topLevelWidgets() if w.isVisible()]     # ninguna ventana suelta


def test_interfaz_elige_camara_simulada_si_se_pide(qapp):
    from votoseguro.hardware.camara import CamaraSimulada
    from votoseguro.ui.app import elegir_camara

    assert isinstance(elegir_camara("simulada"), CamaraSimulada)
