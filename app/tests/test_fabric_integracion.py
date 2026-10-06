"""Integración con la red Hyperledger Fabric real (red local + puente Go).

Se omite si la red no está levantada. Para ejecutarla:
    blockchain/network/up.sh && blockchain/bridge/iniciar.sh
    pytest -m fabric
"""

import pytest

from votoseguro.blockchain.cliente import AnclajeRechazado, ClientePuente, PuenteNoDisponible
from votoseguro.cripto.llavero import Llavero
from votoseguro.hardware.camara import CamaraSimulada
from votoseguro.hardware.huella import LectorSimulado
from votoseguro.hardware.impresora import ImpresoraMemoria
from votoseguro.servicios import verificacion
from votoseguro.servicios.base import Contexto

from .test_blockchain import FRASE, eleccion_completa

pytestmark = [pytest.mark.bd, pytest.mark.fabric]


@pytest.fixture(scope="module")
def puente():
    try:
        cliente = ClientePuente(timeout=60)
    except PuenteNoDisponible:
        pytest.skip("sin token del puente (ejecute blockchain/bridge/iniciar.sh)")
    if not cliente.disponible():
        pytest.skip("la red Fabric / el puente no están en ejecución")
    return cliente


def test_eleccion_anclada_en_fabric_y_verificada(bd, puente, tmp_path):
    ctx = Contexto(bd("vs_app", autocommit=True), Llavero.nuevo(), LectorSimulado(), ImpresoraMemoria(),
                   "operador1", CamaraSimulada(), puente)
    eid, paquete = eleccion_completa(ctx, tmp_path, votantes=12)
    filas = ctx.conn.execute("SELECT estado, tx_id FROM blockchain.outbox ORDER BY id").fetchall()
    assert all(e == "ENVIADO" and len(tx) == 64 for e, tx in filas), filas

    informe = verificacion.verificar_paquete(paquete, FRASE, consultar_ledger=puente.consultar_mesa)
    assert informe.conforme, informe.texto()
    assert sum(c.nivel == "LEDGER" and c.ok for c in informe.chequeos) == 6

    exp = informe.expediente["eleccion.json"]
    historial = puente.historial(exp["eleccion_global"], exp["mesa"])
    assert [h["estado"] for h in historial][-1] == "EXPORTADA" and len(historial) == len(filas)


def test_fabric_rechaza_hitos_incoherentes(bd, puente, tmp_path):
    ctx = Contexto(bd("vs_app", autocommit=True), Llavero.nuevo(), LectorSimulado(), ImpresoraMemoria(),
                   "operador1", CamaraSimulada(), puente)
    _, paquete = eleccion_completa(ctx, tmp_path, votantes=10)
    exp = verificacion.verificar_paquete(paquete, FRASE).expediente["eleccion.json"]
    ancla = {"eleccion_global": exp["eleccion_global"], "mesa": exp["mesa"]}
    with pytest.raises(AnclajeRechazado, match="EXPORTADA"):     # checkpoint después de exportar
        puente.enviar("RegistrarCheckpoint", {**ancla, "seq": 9, "conteo": 1, "raiz_merkle": "a" * 64})
    with pytest.raises(AnclajeRechazado, match="ya está registrada"):  # reescribir el registro
        puente.enviar("RegistrarEleccion", {**ancla, "hash_configuracion": "b" * 64,
                                            "huella_clave_eleccion": "b" * 64, "huella_dispositivo": "b" * 64})


def test_cli_con_fabric(bd, puente, tmp_path, capsys):
    from votoseguro import cli

    dsn = bd.dsn + " user=vs_app"
    assert cli.main(["--dsn", dsn, "demo", "--votantes", "12", "--mesas", "2", "--bits", "2048",
                     "--semilla", "4", "--salida", str(tmp_path), "--fabric"]) == 0
    salida = capsys.readouterr().out
    assert "RESULTADO CONSOLIDADO: CONFORME" in salida and "Anclajes en Hyperledger Fabric:" in salida
    assert "se habilita" not in salida and "no se indicó un ledger" not in salida
    paquetes = sorted(str(p) for p in (tmp_path / "usb").glob("*.vsx"))
    assert cli.main(["verificar", paquetes[0], "--frase", "demo-votoseguro-2026", "--fabric"]) == 0
    assert cli.main(["consolidar", *paquetes, "--frase", "demo-votoseguro-2026", "--fabric"]) == 0
    assert cli.main(["--dsn", dsn, "sincronizar"]) == 0
    capsys.readouterr()
    import json, zipfile, io
    from votoseguro.cripto.llavero import descifrar_con_frase
    from votoseguro.servicios.exportacion import CONTEXTO_PAQUETE
    with zipfile.ZipFile(io.BytesIO(descifrar_con_frase(open(paquetes[0], "rb").read(), "demo-votoseguro-2026",
                                                         CONTEXTO_PAQUETE))) as z:
        eleccion = json.loads(z.read("eleccion.json"))
    assert cli.main(["ledger", eleccion["eleccion_global"], eleccion["mesa"]]) == 0
    assert "EXPORTADA" in capsys.readouterr().out
    assert cli.main(["ledger", eleccion["eleccion_global"], "99"]) == 1
