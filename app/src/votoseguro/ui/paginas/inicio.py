"""Resumen de la mesa: estado, padrón, votos, anclajes en Fabric e identidad del equipo."""

from PySide6.QtWidgets import QFormLayout, QGroupBox, QPushButton

from votoseguro.datos import repositorio as repo
from votoseguro.servicios.base import anclar
from votoseguro.ui.comun import ejecutar, etiqueta
from votoseguro.ui.paginas.base import Pagina


class PaginaInicio(Pagina):
    titulo = "Resumen de la mesa"
    menu = "Resumen"

    def __init__(self, sesion_app, ventana):
        super().__init__(sesion_app, ventana)
        caja = QGroupBox("Elección instalada en este equipo")
        self.formulario = QFormLayout(caja)
        self.campos = {}
        for clave in ("Elección", "Mesa", "Estado", "Identificador global", "Padrón", "Votos en urna",
                      "Checkpoints", "Anclajes en Fabric", "Huella del equipo"):
            self.campos[clave] = etiqueta("—")
            self.formulario.addRow(clave + ":", self.campos[clave])
        self.capa.addWidget(caja)
        self.boton_sincronizar = QPushButton("Sincronizar anclajes con Hyperledger Fabric")
        self.boton_sincronizar.clicked.connect(self.sincronizar)
        self.capa.addWidget(self.boton_sincronizar)
        self.capa.addStretch()

    def refrescar(self) -> None:
        c, conn = self.campos, self.app.conn
        c["Huella del equipo"].setText(self.app.llavero.huella_dispositivo)
        enviados, total = conn.execute(
            "SELECT count(*) FILTER (WHERE estado = 'ENVIADO'), count(*) FROM blockchain.outbox").fetchone()
        if self.app.puente is None:
            estado_fabric = "sin conexión configurada (anclajes en cola)"
        else:
            estado_fabric = "conectado" if self.app.puente.disponible() else "NO disponible (modo degradado)"
        c["Anclajes en Fabric"].setText(f"{enviados} de {total} confirmados · {estado_fabric}")
        self.boton_sincronizar.setEnabled(self.app.puente is not None and enviados < total)
        e = self.app.eleccion()
        if e is None:
            for clave in ("Elección", "Mesa", "Estado", "Identificador global", "Padrón", "Votos en urna",
                          "Checkpoints"):
                c[clave].setText("—")
            c["Elección"].setText("No hay elecciones instaladas. Un administrador debe configurarla.")
            return
        padron = repo.conteos_padron(conn, e.id)
        c["Elección"].setText(e.nombre)
        c["Mesa"].setText(e.mesa)
        c["Estado"].setText(e.estado.value)
        c["Identificador global"].setText(e.eleccion_global)
        c["Padrón"].setText(f"{padron['total']} empadronados · {padron['habilitados']} habilitados · "
                            f"{padron['votaron']} votaron")
        c["Votos en urna"].setText(str(repo.contar_votos(conn, e.id)))
        c["Checkpoints"].setText(str(len(repo.checkpoints(conn, e.id))))

    def sincronizar(self) -> None:
        r = ejecutar(self, lambda: anclar(self.app.ctx()))
        if r and r is not True:
            self.ventana.barra(f"Anclajes enviados: {r.enviados}; pendientes: {r.pendientes}")
        self.refrescar()
