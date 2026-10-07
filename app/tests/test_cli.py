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
    assert cli.main(["--dsn", dsn, "demo", "--votantes", "12", "--mesas", "2", "--bits", "2048",
                     "--semilla", "3", "--salida", str(tmp_path)]) == 0
    salida = capsys.readouterr().out
    assert "RESULTADO CONSOLIDADO: CONFORME" in salida and "duplicados detectados: 1" in salida
    paquetes = sorted(str(p) for p in (tmp_path / "usb").glob("*.vsx"))
    assert len(paquetes) == 2
    assert cli.main(["consolidar", *paquetes, "--frase", "demo-votoseguro-2026"]) == 0
    assert cli.main(["consolidar", paquetes[0], "--frase", "demo-votoseguro-2026"]) == 1   # falta la mesa 02
    assert "faltan: 02" in capsys.readouterr().out
    paquete = paquetes[0]
    assert cli.main(["verificar", str(paquete), "--frase", "demo-votoseguro-2026"]) == 0
    assert cli.main(["verificar", str(paquete), "--frase", "demo-votoseguro-2026",
                     "--papel", "A=999"]) == 1
    assert "DISCREPANCIAS" in capsys.readouterr().out


def test_preparar_demo_para_la_interfaz(bd, tmp_path, capsys):
    from votoseguro.cripto.llavero import Llavero

    llavero = tmp_path / "llavero.vsk"
    Llavero.nuevo().guardar(llavero, "frase-del-llavero-1")
    dsn = bd.dsn + " user=vs_app"
    assert cli.main(["--dsn", dsn, "preparar-demo", "--votantes", "3", "--abrir", "--llavero", str(llavero),
                     "--frase", "frase-del-llavero-1", "--salida", str(tmp_path / "ui")]) == 0
    salida = capsys.readouterr().out
    assert "ABIERTA" in salida and "4501003" in salida and salida.count("VS1-") == 5
    assert (tmp_path / "ui" / "impresiones").glob("*constancia_4501001.pdf")
    with pytest.raises(SystemExit):
        cli.main(["--dsn", dsn, "preparar-demo", "--llavero", str(llavero), "--frase", "otra-frase-mala"])
