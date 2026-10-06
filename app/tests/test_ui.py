"""Pruebas de la interfaz gráfica (pytest-qt, sin pantalla: QT_QPA_PLATFORM=offscreen).

Recorren la elección completa haciendo clic como lo haría el personal de mesa. Con la variable
``VOTOSEGURO_CAPTURAS=<carpeta>`` guardan además capturas de pantalla para el informe.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton  # noqa: E402

from votoseguro.cripto.llavero import Llavero  # noqa: E402
from votoseguro.datos import repositorio as repo  # noqa: E402
from votoseguro.dominio.modelos import Estado, Rol  # noqa: E402
from votoseguro.hardware.camara import CamaraSimulada  # noqa: E402
from votoseguro.hardware.huella import LectorSimulado  # noqa: E402
from votoseguro.hardware.impresora import ImpresoraMemoria  # noqa: E402
from votoseguro.servicios import usuarios  # noqa: E402
from votoseguro.ui.kiosco import VentanaKiosco  # noqa: E402
from votoseguro.ui.login import BLOQUEO_SEGUNDOS, Bloqueo, DialogoLogin  # noqa: E402
from votoseguro.ui.paginas.auditoria import PaginaAuditoria  # noqa: E402
from votoseguro.ui.paginas.configuracion import PaginaConfiguracion  # noqa: E402
from votoseguro.ui.paginas.empadronamiento import PaginaEmpadronamiento  # noqa: E402
from votoseguro.ui.paginas.escrutinio import PaginaEscrutinio  # noqa: E402
from votoseguro.ui.paginas.jornada import PaginaJornada  # noqa: E402
from votoseguro.ui.sesion import SesionApp  # noqa: E402
from votoseguro.ui.ventana import VentanaPrincipal  # noqa: E402

pytestmark = pytest.mark.bd
FRASE = "frase-de-prueba-larga"
CAPTURAS = os.environ.get("VOTOSEGURO_CAPTURAS")


@pytest.fixture
def dialogos(monkeypatch, tmp_path):
    """Sustituye los diálogos modales: registra los mensajes y responde lo que la prueba indique."""
    registro = {"mensajes": [], "textos": [], "carpeta": str(tmp_path)}
    monkeypatch.setattr(QMessageBox, "exec", lambda self: registro["mensajes"].append(
        (self.windowTitle(), self.text())) or 0)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(
        lambda *a, **k: (registro["textos"].pop(0), True) if registro["textos"] else ("", False)))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: registro["carpeta"]))
    for estatico in ("information", "warning", "critical"):   # diálogos estáticos (modales en C++)
        monkeypatch.setattr(QMessageBox, estatico, staticmethod(
            lambda _padre, titulo, texto, *a, **k: registro["mensajes"].append((titulo, texto))))
    return registro


@pytest.fixture
def sesion(bd, tmp_path):
    def crear(rol=Rol.ADMIN, usuario="admin.prueba"):
        return SesionApp(bd("vs_app", autocommit=True), Llavero.nuevo(), LectorSimulado(), CamaraSimulada(),
                         ImpresoraMemoria(), tmp_path, None, simulado=True, usuario=usuario, rol=rol)
    return crear


def captura(widget, nombre):
    if CAPTURAS:
        Path(CAPTURAS).mkdir(parents=True, exist_ok=True)
        widget.grab().save(str(Path(CAPTURAS) / f"{nombre}.png"))


def boton(widget, texto) -> QPushButton:
    return next(b for b in widget.findChildren(QPushButton) if b.text().startswith(texto))


# --- Ingreso del personal ----------------------------------------------------------------------

def test_login_bloquea_tras_tres_intentos(qtbot, sesion):
    app = sesion()
    usuarios.crear_usuario(app.conn, "operador1", Rol.OPERADOR, "clave-segura-123")
    ahora = [1000.0]
    bloqueo = Bloqueo(reloj=lambda: ahora[0])
    dialogo = DialogoLogin(app.conn, bloqueo)
    qtbot.addWidget(dialogo)
    dialogo.campo_usuario.setText("operador1")
    for _ in range(3):
        dialogo.campo_clave.setText("incorrecta")
        dialogo.intentar()
    assert bloqueo.restante() == BLOQUEO_SEGUNDOS and "Bloqueado" in dialogo.aviso.text()
    dialogo.campo_clave.setText("clave-segura-123")
    dialogo.intentar()                                  # bloqueado aunque la clave sea correcta
    assert dialogo.rol is None and "Espere" in dialogo.aviso.text()
    ahora[0] += BLOQUEO_SEGUNDOS + 1
    dialogo.intentar()
    assert dialogo.rol == Rol.OPERADOR and dialogo.usuario == "operador1"
    eventos = [e["evento"] for e in repo.bitacora_completa(app.conn)]
    assert eventos.count("LOGIN_FALLIDO") == 3 and eventos.count("LOGIN_EXITOSO") == 1


def test_navegacion_segun_rol(qtbot, sesion):
    for rol, visibles in ((Rol.OPERADOR, {"Resumen", "Empadronamiento", "Jornada de votación", "Escrutinio"}),
                          (Rol.AUDITOR, {"Resumen", "Auditoría"})):
        app = sesion(rol, f"{rol.value.lower()}.prueba")
        kiosco = VentanaKiosco(app)
        ventana = VentanaPrincipal(app, kiosco)
        qtbot.addWidget(ventana)
        qtbot.addWidget(kiosco)
        mostradas = {ventana.navegacion.item(i).text() for i in range(ventana.navegacion.count())
                     if not ventana.navegacion.item(i).isHidden()}
        assert mostradas == visibles


def test_kiosco_no_se_cierra_ni_reacciona_sin_sesion(qtbot, sesion):
    kiosco = VentanaKiosco(sesion())
    qtbot.addWidget(kiosco)
    kiosco.show()
    kiosco.close()
    assert kiosco.isVisible()                           # el votante no puede cerrar la cabina
    qtbot.keyClick(kiosco, Qt.Key.Key_1)
    assert kiosco.pila.currentIndex() == 0 and not kiosco.ocupada


# --- Elección completa desde la interfaz -------------------------------------------------------

def test_eleccion_completa_desde_la_interfaz(qtbot, sesion, dialogos, tmp_path):
    app = sesion()
    kiosco = VentanaKiosco(app)
    ventana = VentanaPrincipal(app, kiosco)
    qtbot.addWidget(ventana)
    qtbot.addWidget(kiosco)
    ventana.show()
    kiosco.show()

    # 1. Configuración
    ventana.ir_a(PaginaConfiguracion)
    conf = ventana.pagina_actual()
    conf.nombre.setText("Elección de Directorio 2026")
    for fila, (codigo, nombre, frente) in enumerate([("A", "Ana Choque", "Frente Unidad"),
                                                    ("B", "Carlos Quispe", "Alianza Renovación")]):
        for col, valor in enumerate((codigo, nombre, frente)):
            from PySide6.QtWidgets import QTableWidgetItem
            conf.candidaturas.setItem(fila, col, QTableWidgetItem(valor))
    qtbot.mouseClick(conf.boton_definir, Qt.MouseButton.LeftButton)
    captura(ventana, "01_configuracion")
    qtbot.mouseClick(conf.boton_instalar, Qt.MouseButton.LeftButton)
    eleccion = app.eleccion()
    assert eleccion.estado == Estado.CONFIGURACION and eleccion.mesa == "01"
    partes = [d.qr for d in app.impresora.documentos if d.nombre_archivo.startswith("parte_")]
    assert len(partes) == 5

    # 2. Empadronamiento
    ventana.ir_a(PaginaEmpadronamiento)
    padron = ventana.pagina_actual()
    qtbot.mouseClick(padron.boton_iniciar, Qt.MouseButton.LeftButton)
    for ci, nombres, apellidos in [("4501001", "Rosa", "Mamani Apaza"), ("4501002", "Luis", "Quispe Choque"),
                                   ("4501003", "Elena", "Condori Flores")]:
        padron.ci.setText(ci)
        padron.nombres.setText(nombres)
        padron.apellidos.setText(apellidos)
        qtbot.mouseClick(padron.boton_registrar, Qt.MouseButton.LeftButton)
    assert padron.tabla.rowCount() == 3 and not padron.foto.pixmap().isNull()
    captura(ventana, "02_empadronamiento")
    qtbot.mouseClick(padron.boton_cerrar, Qt.MouseButton.LeftButton)
    assert app.eleccion().estado == Estado.LISTA

    # 3. Apertura
    ventana.ir_a(PaginaJornada)
    jornada = ventana.pagina_actual()
    captura(ventana, "03_apertura")
    qtbot.mouseClick(jornada.boton_abrir, Qt.MouseButton.LeftButton)
    assert app.eleccion().estado == Estado.ABIERTA

    # 4. Votante 1: huella correcta, vota con el ratón
    jornada.ci.setText("4501001")
    qtbot.mouseClick(boton(jornada, "Buscar"), Qt.MouseButton.LeftButton)
    qtbot.mouseClick(jornada.boton_huella, Qt.MouseButton.LeftButton)
    assert jornada.boton_cabina.isEnabled()
    captura(ventana, "04_identificacion")
    qtbot.mouseClick(jornada.boton_cabina, Qt.MouseButton.LeftButton)
    assert kiosco.ocupada and "OCUPADA" in jornada.estado_cabina.text()
    captura(kiosco, "05_kiosco_seleccion")
    qtbot.mouseClick(boton(kiosco, "  1."), Qt.MouseButton.LeftButton)
    captura(kiosco, "06_kiosco_confirmacion")
    qtbot.mouseClick(kiosco.boton_confirmar, Qt.MouseButton.LeftButton)
    assert not kiosco.ocupada and "Código del comprobante" in kiosco.texto_comprobante.text()
    captura(kiosco, "07_kiosco_comprobante")
    kiosco.volver_a_espera()

    # 5. Votante 2: la huella falla 3 veces → excepción manual; vota con el teclado
    jornada.ci.setText("4501002")
    qtbot.mouseClick(boton(jornada, "Buscar"), Qt.MouseButton.LeftButton)
    jornada.simular_falla.setChecked(True)
    qtbot.mouseClick(jornada.boton_huella, Qt.MouseButton.LeftButton)
    assert not jornada.boton_cabina.isEnabled() and "no coincide" in jornada.datos_votante.text()
    dialogos["textos"].append("Huella ilegible; CI y foto verificados en persona")
    qtbot.mouseClick(jornada.boton_excepcion, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(jornada.boton_cabina, Qt.MouseButton.LeftButton)
    qtbot.keyClick(kiosco, Qt.Key.Key_2)
    qtbot.keyClick(kiosco, Qt.Key.Key_Escape)           # corrige
    qtbot.keyClick(kiosco, Qt.Key.Key_3)                # VOTO BLANCO
    qtbot.keyClick(kiosco, Qt.Key.Key_Return)
    kiosco.volver_a_espera()

    # 6. Doble voto rechazado
    jornada.ci.setText("4501001")
    qtbot.mouseClick(boton(jornada, "Buscar"), Qt.MouseButton.LeftButton)
    assert "ya emitió" in jornada.datos_votante.text() and not jornada.boton_huella.isEnabled()

    # 7. Cierre y escrutinio
    qtbot.mouseClick(jornada.boton_cerrar, Qt.MouseButton.LeftButton)
    assert app.eleccion().estado == Estado.CERRADA
    ventana.ir_a(PaginaEscrutinio)
    escr = ventana.pagina_actual()
    for campo, parte in zip(escr.partes, partes[1:4]):
        campo.setText(parte)
    qtbot.mouseClick(escr.boton_escrutar, Qt.MouseButton.LeftButton)
    assert app.eleccion().estado == Estado.ESCRUTADA and escr.tabla.rowCount() == 4
    filas = [(escr.tabla.item(i, 0).text(), int(escr.tabla.item(i, 1).text())) for i in range(4)]
    assert filas == [("Ana Choque", 1), ("Carlos Quispe", 0), ("VOTO BLANCO", 1), ("VOTO NULO", 0)]  # orden de boleta
    captura(ventana, "08_escrutinio")

    # 8. Exportación y auditoría triple desde la interfaz
    dialogos["textos"] += [FRASE, FRASE]
    qtbot.mouseClick(escr.boton_exportar, Qt.MouseButton.LeftButton)
    assert app.eleccion().estado == Estado.EXPORTADA
    paquete = str(next(Path(dialogos["carpeta"]).glob("*.vsx")))
    ventana.ir_a(PaginaAuditoria)
    auditoria = ventana.pagina_actual()
    auditoria.paquetes.append(paquete)
    auditoria.lista.addItem(paquete)
    auditoria.frase.setText(FRASE)
    qtbot.mouseClick(boton(auditoria, "Abrir los paquetes"), Qt.MouseButton.LeftButton)
    from PySide6.QtWidgets import QTableWidgetItem
    conteo = {"A": "1", "B": "0", "BLANCO": "1", "NULO": "0"}
    for i in range(auditoria.tabla_papel.rowCount()):
        auditoria.tabla_papel.setItem(i, 2, QTableWidgetItem(conteo[auditoria.tabla_papel.item(i, 1).text()]))
    auditoria.tabla_huellas.setItem(0, 1, QTableWidgetItem(app.llavero.huella_dispositivo))
    qtbot.mouseClick(auditoria.boton_verificar, Qt.MouseButton.LeftButton)
    assert auditoria.veredicto.text() == "RESULTADO: CONFORME", dialogos["mensajes"]
    captura(ventana, "09_auditoria")
    errores = [m for m in dialogos["mensajes"] if m[0] in ("No se pudo completar la operación",
                                                           "Error de base de datos")]
    assert len(errores) == 1 and "no coincide" in errores[0][1]   # solo la huella fallida


# --- Arranque, primer uso y usuarios -----------------------------------------------------------

def test_arranque_crea_llavero_y_administrador(qtbot, bd, dialogos, monkeypatch, tmp_path):
    from votoseguro.ui import app as modulo_app
    from votoseguro.ui.login import DialogoPrimerUso

    def primer_uso(self):
        self.campo_usuario.setText("admin")
        self.campo_clave.setText("clave-admin-segura")
        self.campo_repetir.setText("clave-admin-segura")
        self.crear()
        return self.result()

    def ingreso(self):
        self.campo_usuario.setText("admin")
        self.campo_clave.setText("clave-admin-segura")
        self.intentar()
        return self.result()

    monkeypatch.setattr(DialogoPrimerUso, "exec", primer_uso)
    monkeypatch.setattr(DialogoLogin, "exec", ingreso)
    dialogos["textos"] += ["frase-del-llavero-1", "frase-del-llavero-1"]     # crear llavero
    llavero = tmp_path / "llavero.vsk"
    iniciada = modulo_app.iniciar(["--dsn", bd.dsn + " user=vs_app", "--llavero", str(llavero),
                                   "--salida", str(tmp_path / "ui")])
    assert iniciada is not None and llavero.exists()
    _, ventana, kiosco = iniciada
    qtbot.addWidget(ventana)
    qtbot.addWidget(kiosco)
    assert ventana.app.usuario == "admin" and ventana.app.rol == Rol.ADMIN
    ventana.close()

    dialogos["textos"] += ["frase-incorrecta-x"] * 3                        # abrir con frase errónea
    assert modulo_app.iniciar(["--dsn", bd.dsn + " user=vs_app", "--llavero", str(llavero)]) is None


def test_pagina_usuarios_crea_operador(qtbot, sesion, dialogos):
    from votoseguro.ui.paginas.usuarios import PaginaUsuarios

    app = sesion()
    kiosco = VentanaKiosco(app)
    ventana = VentanaPrincipal(app, kiosco)
    qtbot.addWidget(ventana)
    qtbot.addWidget(kiosco)
    ventana.ir_a(PaginaUsuarios)
    pagina = ventana.pagina_actual()
    pagina.nombre.setText("operador.mesa1")
    pagina.rol.setCurrentText("OPERADOR")
    pagina.clave.setText("clave-operador-1")
    qtbot.mouseClick(boton(pagina, "Crear usuario"), Qt.MouseButton.LeftButton)
    assert pagina.tabla.rowCount() == 1 and pagina.tabla.item(0, 1).text() == "OPERADOR"
    pagina.nombre.setText("operador.mesa1")                                   # duplicado
    pagina.clave.setText("clave-operador-1")
    qtbot.mouseClick(boton(pagina, "Crear usuario"), Qt.MouseButton.LeftButton)
    assert dialogos["mensajes"][-1][0] == "Error de base de datos"


def test_salir_requiere_contrasena_y_la_x_no_cierra(qtbot, sesion, monkeypatch):
    app = sesion()
    usuarios.crear_usuario(app.conn, "admin.prueba", Rol.ADMIN, "clave-admin-segura")
    kiosco = VentanaKiosco(app)
    ventana = VentanaPrincipal(app, kiosco)
    qtbot.addWidget(ventana)
    qtbot.addWidget(kiosco)
    ventana.show()
    ventana.close()                                     # "X" o Alt+F4
    assert ventana.isVisible() and "Salir" in ventana.statusBar().currentMessage()

    claves = iter(["incorrecta", "clave-admin-segura"])

    def ingreso(self):
        self.campo_clave.setText(next(claves))
        self.intentar()
        return self.result()

    monkeypatch.setattr(DialogoLogin, "exec", ingreso)
    ventana.salir()                                     # contraseña incorrecta: sigue abierta
    assert ventana.isVisible()
    ventana.salir()
    assert not ventana.isVisible() and not kiosco.isVisible()
    eventos = [e["evento"] for e in repo.bitacora_completa(app.conn)]
    assert eventos[-2:] == ["LOGIN_EXITOSO", "SALIDA_SISTEMA"] and "LOGIN_FALLIDO" in eventos


def test_kiosco_tecla_cero_corrige(qtbot, sesion):
    from votoseguro.servicios.votacion import SesionVoto

    app = sesion()
    from votoseguro.servicios import configuracion
    from votoseguro.servicios.configuracion import Candidatura
    creada = configuracion.crear_eleccion(app.ctx(), "Prueba de teclado", [Candidatura("A", "Ana")], bits=2048)
    kiosco = VentanaKiosco(app)
    qtbot.addWidget(kiosco)
    kiosco.habilitar(SesionVoto(creada.eleccion_id, "1234567", "HUELLA"))
    qtbot.keyClick(kiosco, Qt.Key.Key_1)
    assert kiosco.pila.currentIndex() == 2 and "ENTER" in kiosco.findChild(type(kiosco.texto_eleccion), "teclas").text()
    qtbot.keyClick(kiosco, Qt.Key.Key_0)
    assert kiosco.pila.currentIndex() == 1 and kiosco.elegida is None
