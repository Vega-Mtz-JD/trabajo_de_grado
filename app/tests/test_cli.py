"""Pruebas de caja negra de la CLI."""

import pytest

from votoseguro import cli
from votoseguro.auditoria import bitacora

pytestmark = pytest.mark.bd


def test_verificar_bitacora_integra(bd, capsys):
    app = bd("vs_app")
    bitacora.registrar(app, "operador1", "APERTURA")
    app.commit()
    assert cli.main(["--dsn", bd.dsn + " user=vs_auditor", "verificar-bitacora"]) == 0
    assert "ÍNTEGRA: 1 entradas" in capsys.readouterr().out


def test_verificar_bitacora_con_ancla_inexistente(bd, capsys):
    app = bd("vs_app")
    bitacora.registrar(app, "operador1", "APERTURA")
    app.commit()
    codigo = cli.main(["--dsn", bd.dsn + " user=vs_auditor", "verificar-bitacora",
                       "--ultimo-hash", "f" * 64])
    assert codigo == 1
    assert "ALTERADA" in capsys.readouterr().err


def test_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "votoseguro 0.1.0" in capsys.readouterr().out


def test_demo_y_verificar_por_cli(bd, tmp_path, capsys):
    dsn = bd.dsn + " user=vs_app"
    assert cli.main(["--dsn", dsn, "demo", "--votantes", "12", "--bits", "2048",
                     "--semilla", "3", "--salida", str(tmp_path)]) == 0
    salida = capsys.readouterr().out
    assert "RESULTADO: CONFORME" in salida
    paquete = next((tmp_path / "usb").glob("*.vsx"))
    assert cli.main(["verificar", str(paquete), "--frase", "demo-votoseguro-2026"]) == 0
    assert cli.main(["verificar", str(paquete), "--frase", "demo-votoseguro-2026",
                     "--papel", "A=999"]) == 1
    assert "DISCREPANCIAS" in capsys.readouterr().out
