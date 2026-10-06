"""Interfaz de línea de comandos de VOTO SEGURO."""

import argparse
import sys
from pathlib import Path

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


def _demo(args) -> int:
    from votoseguro.servicios import demo

    with conectar(args.dsn, autocommit=True) as conn:
        r = demo.ejecutar(conn, Path(args.salida), votantes=args.votantes, bits=args.bits,
                          semilla=args.semilla)
    print()
    print(f"Elección: {r.eleccion_id}")
    print("Resultados:")
    total = sum(r.resultados.values())
    for codigo, votos in r.resultados.items():
        print(f"  {codigo:<8} {votos:>4}  {100 * votos / total:5.1f} %")
    print(f"Votos: {r.eventos['votos']} · abstención: {r.eventos['abstencion']} · "
          f"excepciones manuales: {r.eventos['excepciones_manuales']} · "
          f"doble voto rechazado: {r.eventos['doble_voto_rechazado']}")
    print("Tiempos: " + ", ".join(f"{k} {v:.1f} s" for k, v in r.tiempos.items()))
    print()
    print(r.informe.texto())
    print()
    print(f"Impresiones (zerésima, actas, partes, urna VVPAT): {r.carpeta / 'impresiones'}")
    print(f"Paquete USB: {r.paquete}   (frase: {demo.FRASE_DEMO})")
    return 0 if r.informe.conforme else 1


def _verificar(args) -> int:
    from votoseguro.servicios import verificacion

    papel = None
    if args.papel:
        papel = {k: int(v) for k, v in (par.split("=") for par in args.papel.split(","))}
    informe = verificacion.verificar_paquete(Path(args.paquete), args.frase, conteo_papel=papel,
                                             huella_esperada=args.huella)
    print(informe.texto())
    return 0 if informe.conforme else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="votoseguro", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"votoseguro {__version__}")
    parser.add_argument("--dsn", help="cadena de conexión PostgreSQL (o variable VOTOSEGURO_DSN)")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("verificar-bitacora", help="recalcula la cadena de hashes de la bitácora")
    p.add_argument("--ultimo-hash", help="hash anclado (acta/ledger) que debe existir en la bitácora")
    p.set_defaults(funcion=_verificar_bitacora)

    p = sub.add_parser("demo", help="simula una elección completa con hardware simulado")
    p.add_argument("--votantes", type=int, default=100)
    p.add_argument("--salida", default="salida_demo", help="carpeta de impresiones y USB")
    p.add_argument("--bits", type=int, default=3072, help="tamaño de la clave RSA de la elección")
    p.add_argument("--semilla", type=int, help="semilla para reproducir la distribución de votos")
    p.set_defaults(funcion=_demo)

    p = sub.add_parser("verificar", help="auditoría triple de un paquete exportado (.vsx)")
    p.add_argument("paquete")
    p.add_argument("--frase", required=True, help="frase de paso del paquete")
    p.add_argument("--papel", help="conteo manual de VVPAT, p. ej. A=37,B=30,C=18,BLANCO=5,NULO=4")
    p.add_argument("--huella", help="huella del dispositivo impresa en la zerésima")
    p.set_defaults(funcion=_verificar)

    args = parser.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    sys.exit(main())
