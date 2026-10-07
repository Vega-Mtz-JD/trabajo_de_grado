"""Estado compartido de la aplicación gráfica: conexión, llavero, periféricos y usuario."""

from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from votoseguro.cripto.llavero import Llavero
from votoseguro.datos import repositorio as repo
from votoseguro.dominio.modelos import Eleccion, Rol
from votoseguro.hardware.camara import Camara, CamaraSimulada
from votoseguro.hardware.huella import LectorHuella, LectorSimulado
from votoseguro.hardware.impresora import Impresora
from votoseguro.servicios.base import Contexto


@dataclass
class SesionApp:
    conn: psycopg.Connection
    llavero: Llavero
    lector: LectorHuella
    camara: Camara
    impresora: Impresora
    carpeta: Path
    puente: object | None = None
    simulado: bool = True
    usuario: str = ""
    rol: Rol | None = None
    eleccion_id: str | None = None
    _contexto: Contexto | None = field(default=None, repr=False)

    def ctx(self) -> Contexto:
        """Contexto de servicios del usuario actual. Se reutiliza para conservar el estado del
        modo degradado de Fabric entre operaciones."""
        if self._contexto is None or self._contexto.actor != self.usuario:
            self._contexto = Contexto(self.conn, self.llavero, self.lector, self.impresora, self.usuario,
                                      self.camara, self.puente)
        return self._contexto

    def cambiar_camara(self, camara: Camara) -> None:
        """El operador eligió otra cámara (p. ej. una externa USB)."""
        self.camara = camara
        if self._contexto is not None:
            self._contexto.camara = camara

    def cambiar_lector(self, lector: LectorHuella) -> None:
        self.lector = lector
        if self._contexto is not None:
            self._contexto.lector = lector

    def eleccion(self) -> Eleccion | None:
        return repo.obtener_eleccion(self.conn, self.eleccion_id) if self.eleccion_id else None

    def elecciones(self) -> list[tuple[str, str]]:
        """Mesas instaladas en este equipo: (id, descripción), las activas primero."""
        filas = self.conn.execute("""
            SELECT id::text, nombre || ' — mesa ' || mesa || ' (' || estado || ')'
              FROM eleccion.eleccion ORDER BY estado = 'EXPORTADA', creada_en DESC""").fetchall()
        return [(i, d) for i, d in filas]

    def preparar_simulacion(self, persona: str, *, huella_coincide: bool = True) -> None:
        """Con hardware simulado, indica quién está frente a la cámara y con el dedo en el lector."""
        if not self.simulado:
            return
        if isinstance(self.camara, CamaraSimulada):
            self.camara.colocar_persona(persona)
        if isinstance(self.lector, LectorSimulado):
            self.lector.colocar_dedo(persona if huella_coincide else f"otra-persona-{persona}")
