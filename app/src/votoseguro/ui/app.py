"""Arranque de la aplicación gráfica: ``votoseguro-ui``.

1. Conecta a PostgreSQL (VOTOSEGURO_DSN). 2. Abre (o crea) el llavero del equipo con su frase.
3. Primer uso: crea el administrador. 4. Ingreso del personal. 5. Abre el panel de mesa y el kiosco
(en el segundo monitor si existe; en pantalla completa con ``--kiosco``).
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QLineEdit, QMessageBox

from votoseguro.cripto.llavero import FraseIncorrecta, Llavero
from votoseguro.datos.conexion import conectar
from votoseguro.hardware.camara import CamaraSimulada
from votoseguro.hardware.huella import LectorSimulado
from votoseguro.hardware.impresora import ImpresoraPDF
from votoseguro.ui.estilo import HOJA
from votoseguro.ui.kiosco import VentanaKiosco
from votoseguro.ui.login import DialogoLogin, DialogoPrimerUso, hay_usuarios
from votoseguro.ui.sesion import SesionApp
from votoseguro.ui.ventana import VentanaPrincipal

LLAVERO_POR_DEFECTO = Path.home() / ".local" / "share" / "votoseguro" / "llavero.vsk"


def abrir_llavero(ruta: Path) -> Llavero | None:
    """Abre el llavero del equipo (3 intentos) o lo crea la primera vez."""
    if not ruta.exists():
        QMessageBox.information(None, "Llavero del equipo",
                                "Este equipo aún no tiene llavero. Se creará uno nuevo con la clave de firma del "
                                "equipo y la clave de los datos personales.\nElija una frase de paso y guárdela.")
        for _ in range(3):
            frase, ok = QInputDialog.getText(None, "Nueva frase del llavero", "Frase (mín. 12 caracteres):",
                                             QLineEdit.EchoMode.Password)
            if not ok:
                return None
            repetida, ok = QInputDialog.getText(None, "Nueva frase del llavero", "Repita la frase:",
                                                QLineEdit.EchoMode.Password)
            if ok and frase == repetida and len(frase) >= 12:
                llavero = Llavero.nuevo()
                llavero.guardar(ruta, frase)
                return llavero
            QMessageBox.warning(None, "Frase inválida", "Las frases no coinciden o tienen menos de 12 caracteres.")
        return None
    for _ in range(3):
        frase, ok = QInputDialog.getText(None, "Llavero del equipo", "Frase del llavero:", QLineEdit.EchoMode.Password)
        if not ok:
            return None
        try:
            return Llavero.abrir(ruta, frase)
        except FraseIncorrecta:
            QMessageBox.warning(None, "Frase incorrecta", "La frase no corresponde a este llavero.")
    return None


def iniciar(argv: list[str] | None = None):
    """Prepara la aplicación (llavero, primer uso, ingreso, ventanas). Devuelve
    ``(qapp, ventana, kiosco)`` o ``None`` si el usuario canceló."""
    parser = argparse.ArgumentParser(prog="votoseguro-ui", description="Panel de mesa y kiosco de VOTO SEGURO")
    parser.add_argument("--dsn", help="cadena de conexión PostgreSQL (o VOTOSEGURO_DSN)")
    parser.add_argument("--llavero", type=Path, default=LLAVERO_POR_DEFECTO)
    parser.add_argument("--salida", type=Path, default=Path("salida_ui"),
                        help="carpeta de la impresora simulada (PDF)")
    parser.add_argument("--kiosco", action="store_true", help="cabina en pantalla completa sin bordes (producción)")
    parser.add_argument("--fabric", action="store_true", help="anclar en Hyperledger Fabric mediante el puente")
    args = parser.parse_args(argv)

    qapp = QApplication.instance() or QApplication(sys.argv[:1])
    qapp.setApplicationName("VOTO SEGURO")
    qapp.setStyleSheet(HOJA)
    conn = conectar(args.dsn, autocommit=True)

    llavero = abrir_llavero(args.llavero)
    if llavero is None:
        return None
    if not hay_usuarios(conn) and DialogoPrimerUso(conn).exec() != QDialog.DialogCode.Accepted:
        return None
    login = DialogoLogin(conn)
    if login.exec() != QDialog.DialogCode.Accepted:
        return None

    puente = None
    if args.fabric:
        from votoseguro.blockchain.cliente import ClientePuente, PuenteNoDisponible
        try:
            puente = ClientePuente()
            if not puente.disponible():
                QMessageBox.warning(None, "Hyperledger Fabric", "El puente no responde: se trabajará en modo "
                                                               "degradado y los anclajes quedarán en cola.")
        except PuenteNoDisponible as e:
            QMessageBox.warning(None, "Hyperledger Fabric", f"{e}\nLos anclajes quedarán en cola.")

    sesion = SesionApp(conn, llavero, LectorSimulado(), CamaraSimulada(), ImpresoraPDF(args.salida / "impresiones"),
                       args.salida, puente, simulado=True, usuario=login.usuario, rol=login.rol)
    kiosco = VentanaKiosco(sesion, pantalla_completa=args.kiosco)
    ventana = VentanaPrincipal(sesion, kiosco)
    pantallas = qapp.screens()
    if len(pantallas) > 1:   # cabina en el segundo monitor
        kiosco.setGeometry(pantallas[1].availableGeometry())
    if args.kiosco:
        kiosco.showFullScreen()
    else:
        kiosco.resize(900, 760)
        kiosco.show()
    ventana.showMaximized()
    return qapp, ventana, kiosco


def main(argv: list[str] | None = None) -> int:
    iniciada = iniciar(argv)
    if iniciada is None:
        return 1
    qapp, _ventana, _kiosco = iniciada
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
