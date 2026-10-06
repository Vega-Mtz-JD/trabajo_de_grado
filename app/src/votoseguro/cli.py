"""Interfaz de línea de comandos de VOTO SEGURO.

En el Sprint 2 se agregan los comandos del proceso electoral (configurar, empadronar,
abrir, votar, cerrar, escrutar, exportar, verificar) y la simulación ``demo``.
"""

import argparse
import sys

from votoseguro import __version__
from votoseguro.auditoria import bitacora
from votoseguro.datos.conexion import conectar


def _verificar_bitacora(args) -> int:
    with conectar(args.dsn) as conn:
        r = bitacora.verificar(conn, args.ultimo_hash)
    if r.integra:
        print(f"Bitácora ÍNTEGRA: {r.entradas} entradas verificadas.")
        return 0
    print(f"Bitácora ALTERADA en la entrada {r.primera_falla}: {r.motivo}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="votoseguro", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"votoseguro {__version__}")
    parser.add_argument("--dsn", help="cadena de conexión PostgreSQL (o variable VOTOSEGURO_DSN)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("verificar-bitacora", help="recalcula la cadena de hashes de la bitácora")
    p.add_argument("--ultimo-hash", help="hash anclado (acta/ledger) que debe existir en la bitácora")
    p.set_defaults(funcion=_verificar_bitacora)

    args = parser.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    sys.exit(main())
