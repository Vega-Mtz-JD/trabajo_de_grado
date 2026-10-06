"""Cliente HTTP del puente Go (ADR-002). El puente solo escucha en 127.0.0.1.

Configuración: ``VOTOSEGURO_PUENTE_URL`` (por defecto http://127.0.0.1:8770) y el token en
``VOTOSEGURO_PUENTE_TOKEN`` o en ``~/.config/votoseguro/puente.token`` (lo crea iniciar.sh).
"""

import os
from pathlib import Path
from typing import Any

import requests

URL_POR_DEFECTO = "http://127.0.0.1:8770"
ARCHIVO_TOKEN = Path.home() / ".config" / "votoseguro" / "puente.token"


class PuenteNoDisponible(Exception):
    """Fabric o el puente no responden: la votación sigue en modo degradado."""


class AnclajeRechazado(Exception):
    """El chaincode rechazó el hito por ser incoherente con lo ya anclado (posible manipulación)."""


class ClientePuente:
    def __init__(self, url: str | None = None, token: str | None = None, timeout: float = 90.0):
        self.url = (url or os.environ.get("VOTOSEGURO_PUENTE_URL", URL_POR_DEFECTO)).rstrip("/")
        if token is None:
            token = os.environ.get("VOTOSEGURO_PUENTE_TOKEN")
        if token is None and ARCHIVO_TOKEN.exists():
            token = ARCHIVO_TOKEN.read_text().strip()
        if not token:
            raise PuenteNoDisponible("no hay token del puente (ejecute blockchain/bridge/iniciar.sh)")
        self._sesion = requests.Session()
        self._sesion.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

    def _solicitar(self, metodo: str, ruta: str, **kwargs) -> requests.Response:
        try:
            r = self._sesion.request(metodo, self.url + ruta, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise PuenteNoDisponible(f"el puente no responde: {e}") from e
        if r.status_code == 409:
            raise AnclajeRechazado(r.json().get("error", r.text))
        if r.status_code in (502, 503, 504):
            raise PuenteNoDisponible(r.json().get("error", r.text) if r.content else str(r.status_code))
        return r

    def disponible(self) -> bool:
        try:
            return self._sesion.get(self.url + "/salud", timeout=3).ok
        except requests.RequestException:
            return False

    def enviar(self, funcion: str, argumentos: dict[str, Any]) -> str:
        """Ancla un hito y espera su confirmación en un bloque. Devuelve el ID de transacción."""
        r = self._solicitar("POST", f"/tx/{funcion}", json=argumentos)
        r.raise_for_status()
        return r.json()["tx_id"]

    def consultar_mesa(self, eleccion_global: str, mesa: str) -> dict[str, Any] | None:
        r = self._solicitar("GET", f"/mesa/{eleccion_global}/{mesa}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def historial(self, eleccion_global: str, mesa: str) -> list[dict[str, Any]]:
        r = self._solicitar("GET", f"/historial/{eleccion_global}/{mesa}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()
