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


def _puente(args):
    """ClientePuente si se pidió --fabric; termina con un mensaje claro si la red no responde."""
    if not getattr(args, "fabric", False):
        return None
    from votoseguro.blockchain.cliente import ClientePuente, PuenteNoDisponible

    try:
        cliente = ClientePuente()
    except PuenteNoDisponible as e:
        sys.exit(f"Error: {e}")
    if not cliente.disponible():
        sys.exit("Error: el puente no responde. Inicie la red con blockchain/network/up.sh "
                 "y el puente con blockchain/bridge/iniciar.sh")
    return cliente


def _demo(args) -> int:
    from votoseguro.servicios import demo

    puente = _puente(args)
    with conectar(args.dsn, autocommit=True) as conn:
        r = demo.ejecutar(conn, Path(args.salida), votantes=args.votantes, mesas=args.mesas,
                          bits=args.bits, semilla=args.semilla, puente=puente)
        if puente:
            enviados = conn.execute("SELECT count(*) FILTER (WHERE estado = 'ENVIADO'), count(*) "
                                    "FROM blockchain.outbox").fetchone()
            print(f"\nAnclajes en Hyperledger Fabric: {enviados[0]} de {enviados[1]} confirmados")
    print()
    c = r.cruce
    print(f"Cruce de padrones: {c.total_votantes} empadronados en {len(c.mesas)} mesa/s · "
          f"duplicados detectados: {len(c.duplicados)} (inhabilitados: {r.eventos['duplicados_inhabilitados']})")
    print(f"Votos: {r.eventos['votos']} · abstención: {r.eventos['abstencion']} · "
          f"excepciones manuales: {r.eventos['excepciones_manuales']} · "
          f"doble voto rechazado: {r.eventos['doble_voto_rechazado']}")
    print("Tiempos: " + ", ".join(f"{k} {v:.1f} s" for k, v in r.tiempos.items()))
    print()
    for mesa, informe in sorted(r.consolidado.informes_mesa.items()):
        print(f"── Auditoría triple · mesa {mesa} " + "─" * 40)
        print(informe.texto())
        print()
    print(r.consolidado.texto())
    print()
    print(f"Impresiones por mesa: {r.carpeta}/mesaNN/impresiones")
    print(f"USB (definición, resúmenes de padrón, paquetes): {r.carpeta / 'usb'}   (frase: {demo.FRASE_DEMO})")
    return 0 if r.conforme else 1


def _consolidar(args) -> int:
    from votoseguro.servicios import consolidacion

    puente = _puente(args)
    r = consolidacion.consolidar([Path(p) for p in args.paquetes], args.frase,
                                 consultar_ledger=puente.consultar_mesa if puente else None)
    for mesa, informe in sorted(r.informes_mesa.items()):
        if not informe.conforme:
            print(f"── Mesa {mesa} con discrepancias " + "─" * 30)
            print(informe.texto())
            print()
    print(r.texto())
    return 0 if r.conforme else 1


def _verificar(args) -> int:
    from votoseguro.servicios import verificacion

    papel = None
    if args.papel:
        papel = {k: int(v) for k, v in (par.split("=") for par in args.papel.split(","))}
    puente = _puente(args)
    informe = verificacion.verificar_paquete(Path(args.paquete), args.frase, conteo_papel=papel,
                                             huella_esperada=args.huella,
                                             consultar_ledger=puente.consultar_mesa if puente else None)
    print(informe.texto())
    return 0 if informe.conforme else 1


def _sincronizar(args) -> int:
    from votoseguro.blockchain import outbox

    args.fabric = True
    puente = _puente(args)
    with conectar(args.dsn, autocommit=True) as conn:
        r = outbox.sincronizar(conn, puente)
    print(f"Anclajes enviados: {r.enviados} · pendientes: {r.pendientes}")
    if r.error:
        print(f"{'RECHAZADO' if r.rechazado else 'Sin conexión'}: {r.error}", file=sys.stderr)
    return 0 if r.al_dia else 1


def _ledger(args) -> int:
    import json

    args.fabric = True
    puente = _puente(args)
    estado = puente.consultar_mesa(args.eleccion_global, args.mesa)
    if estado is None:
        print("La mesa no está registrada en el ledger.", file=sys.stderr)
        return 1
    print(json.dumps(estado, indent=2, ensure_ascii=False))
    print("\nHistorial de transacciones:")
    for h in puente.historial(args.eleccion_global, args.mesa):
        print(f"  {h['momento']}  {h['estado']:<11} tx {h['tx_id']}")
    return 0


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
    p.add_argument("--mesas", type=int, default=1, help="cantidad de urnas (mesas) a simular")
    p.add_argument("--salida", default="salida_demo", help="carpeta de impresiones y USB")
    p.add_argument("--bits", type=int, default=3072, help="tamaño de la clave RSA de la elección")
    p.add_argument("--semilla", type=int, help="semilla para reproducir la distribución de votos")
    p.add_argument("--fabric", action="store_true", help="anclar los hitos en Hyperledger Fabric")
    p.set_defaults(funcion=_demo)

    p = sub.add_parser("verificar", help="auditoría triple de un paquete exportado (.vsx)")
    p.add_argument("paquete")
    p.add_argument("--frase", required=True, help="frase de paso del paquete")
    p.add_argument("--papel", help="conteo manual de VVPAT, p. ej. A=37,B=30,C=18,BLANCO=5,NULO=4")
    p.add_argument("--huella", help="huella del dispositivo impresa en la zerésima")
    p.add_argument("--fabric", action="store_true", help="comparar también con el ledger de Fabric")
    p.set_defaults(funcion=_verificar)

    p = sub.add_parser("consolidar", help="verifica los paquetes de todas las mesas y suma los resultados")
    p.add_argument("paquetes", nargs="+")
    p.add_argument("--frase", required=True)
    p.add_argument("--fabric", action="store_true", help="comparar también con el ledger de Fabric")
    p.set_defaults(funcion=_consolidar)

    p = sub.add_parser("sincronizar", help="envía a Fabric los anclajes pendientes del outbox")
    p.set_defaults(funcion=_sincronizar)

    p = sub.add_parser("ledger", help="muestra el estado anclado de una mesa y su historial")
    p.add_argument("eleccion_global")
    p.add_argument("mesa")
    p.set_defaults(funcion=_ledger)

    args = parser.parse_args(argv)
    return args.funcion(args)


if __name__ == "__main__":
    sys.exit(main())
