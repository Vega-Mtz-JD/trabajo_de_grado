"""Fase 11 — Verificación multinivel (auditoría triple, propuesta §14).

Contrasta las tres fuentes de evidencia:
  1. **Papel:** conteo manual de los VVPAT de la urna física (lo ingresa el auditor) y la
     huella del dispositivo impresa en la zerésima.
  2. **USB:** paquete exportado (firma del manifiesto, hashes, actas, votos, bitácora).
  3. **Ledger:** anclajes en Fabric (se incorpora en el Sprint 3).

Cada comprobación produce un ``Chequeo`` con resultado ✔ / ✘ / — (no evaluado). El informe es
CONFORME solo si ninguna comprobación falla.
"""

import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization

from votoseguro.auditoria.bitacora import verificar_cadena
from votoseguro.cripto import firmas
from votoseguro.cripto.hashing import canonico, hash_canonico, sha3
from votoseguro.cripto.llavero import FraseIncorrecta, descifrar_con_frase, desde_b64
from votoseguro.cripto.merkle import raiz_merkle
from votoseguro.dominio.modelos import codigo_vvpat
from votoseguro.servicios.apertura import compromiso_padron
from votoseguro.servicios.exportacion import CONTEXTO_PAQUETE


@dataclass(frozen=True)
class Chequeo:
    nivel: str          # PAPEL | USB | LEDGER
    nombre: str
    ok: bool | None     # None = no evaluado
    detalle: str = ""


@dataclass
class Informe:
    chequeos: list[Chequeo] = field(default_factory=list)
    expediente: dict[str, Any] | None = field(default=None, repr=False)

    @property
    def conforme(self) -> bool:
        return all(c.ok is not False for c in self.chequeos)

    def agregar(self, nivel: str, nombre: str, ok: bool | None, detalle: str = "") -> bool | None:
        self.chequeos.append(Chequeo(nivel, nombre, ok, detalle))
        return ok

    def texto(self) -> str:
        simbolo = {True: "✔", False: "✘", None: "—"}
        lineas = [f"[{simbolo[c.ok]}] {c.nivel:<6} {c.nombre}" + (f" — {c.detalle}" if c.detalle else "")
                  for c in self.chequeos]
        fallas = sum(c.ok is False for c in self.chequeos)
        lineas.append("")
        lineas.append("RESULTADO: CONFORME" if self.conforme
                      else f"RESULTADO: DISCREPANCIAS ({fallas} comprobaciones fallidas)")
        return "\n".join(lineas)


# --- Apertura del paquete --------------------------------------------------------------------

def abrir_paquete(ruta: Path, frase: str, informe: Informe) -> dict[str, Any] | None:
    """Descifra el paquete, verifica la firma del manifiesto y los hashes de cada archivo."""
    try:
        contenido = descifrar_con_frase(Path(ruta).read_bytes(), frase, CONTEXTO_PAQUETE)
    except FraseIncorrecta:
        informe.agregar("USB", "Descifrado del paquete", False, "frase incorrecta o archivo alterado")
        return None
    informe.agregar("USB", "Descifrado del paquete (AES-256-GCM íntegro)", True)

    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        archivos = {n: z.read(n) for n in z.namelist()}
    hash_manifiesto = sha3(archivos["manifiesto.json"])
    manifiesto = json.loads(archivos.pop("manifiesto.json"))
    firma = archivos.pop("manifiesto.firma")
    dispositivo = json.loads(archivos["dispositivo.json"])
    publica = serialization.load_pem_public_key(dispositivo["clave_publica_pem"].encode())
    informe.agregar("USB", "Firma del manifiesto", firmas.verificar(publica, canonico(manifiesto), firma))

    esperados = manifiesto["archivos"]
    alterados = [n for n, d in archivos.items() if esperados.get(n) != sha3(d)]
    faltantes = sorted(set(esperados) - set(archivos))
    informe.agregar("USB", "Hashes de los archivos del paquete", not alterados and not faltantes,
                    ", ".join(alterados + faltantes))
    expediente = {n: json.loads(d) for n, d in archivos.items()}
    expediente["_hash_manifiesto"] = hash_manifiesto
    return expediente


# --- Verificación del expediente -------------------------------------------------------------

def verificar_expediente(exp: dict[str, Any], informe: Informe, *,
                         conteo_papel: dict[str, int] | None = None,
                         huella_esperada: str | None = None,
                         ledger: dict[str, Any] | None = None,
                         motivo_sin_ledger: str = "sin conexión con el ledger") -> Informe:
    """``ledger`` es el estado anclado de la mesa en Fabric (``ConsultarMesa``)."""
    eleccion, actas = exp["eleccion.json"], exp["actas.json"]
    dispositivo = exp["dispositivo.json"]
    publica = serialization.load_pem_public_key(dispositivo["clave_publica_pem"].encode())
    codigos = [o["codigo"] for o in eleccion["opciones"]]

    # Actas: hash y firma
    for tipo in ("ZERESIMA", "CIERRE", "ESCRUTINIO"):
        acta = actas.get(tipo)
        if acta is None:
            informe.agregar("USB", f"Acta {tipo}", False, "no existe")
            continue
        ok = (hash_canonico(acta["contenido"]) == acta["hash"]
              and firmas.verificar(publica, canonico(acta["contenido"]), desde_b64(acta["firma"])))
        informe.agregar("USB", f"Acta {tipo}: hash y firma del dispositivo", ok)
    if any(t not in actas for t in ("ZERESIMA", "CIERRE", "ESCRUTINIO")):
        return informe
    zeresima, cierre, escrutinio = (actas[t]["contenido"] for t in ("ZERESIMA", "CIERRE", "ESCRUTINIO"))

    # Identidad del dispositivo (anclaje en papel)
    informe.agregar("USB", "Huella del dispositivo = la registrada en la zerésima",
                    dispositivo["huella"] == zeresima["huella_dispositivo"])
    if huella_esperada:
        informe.agregar("PAPEL", "Huella del dispositivo = la impresa en la zerésima de papel",
                        dispositivo["huella"] == huella_esperada.strip().lower())
    else:
        informe.agregar("PAPEL", "Huella del dispositivo contra la zerésima de papel", None, "no ingresada")

    # Zerésima
    informe.agregar("USB", "Zerésima: urna vacía al abrir",
                    zeresima["votos_en_urna"] == 0
                    and set(zeresima["votos_por_opcion"]) == set(codigos)
                    and not any(zeresima["votos_por_opcion"].values()))

    # Definición de la elección (común a todas las mesas)
    informe.agregar("USB", "Definición de la elección: hash = configuración registrada en la zerésima",
                    hash_canonico(eleccion["definicion"]) == eleccion["hash_configuracion"]
                    == zeresima["hash_configuracion"]
                    and eleccion["mesa"] in eleccion["definicion"]["mesas"]
                    and [o[0] for o in eleccion["definicion"]["opciones"]] == codigos)

    # Padrón: compromiso, participación y presencia (RF09, ADR-009)
    padron = exp["padron.json"]
    habilitados = [v["ci"] for v in padron if v["habilitado"]]
    votaron = [v for v in padron if v["ya_voto"]]
    informe.agregar("USB", "Padrón = compromiso anclado en la zerésima",
                    compromiso_padron(habilitados, eleccion["sal_padron"]) == zeresima["padron"]["compromiso"],
                    f"{len(habilitados)} habilitados")
    informe.agregar("USB", "Padrón: votantes marcados = votos en urna; ausentes = acta de cierre",
                    len(votaron) == len(exp["votos.json"]) == cierre["votantes_que_votaron"]
                    and len(habilitados) - len(votaron) == cierre["ausentes"],
                    f"votaron {len(votaron)}, no votaron {len(habilitados) - len(votaron)}")
    informe.agregar("USB", "Padrón: todo votante que votó registró presencia (foto en mesa)",
                    all(v["presente"] for v in votaron))

    # Votos
    votos = exp["votos.json"]
    hashes = [v["hash"] for v in votos]
    integros = all(sha3(desde_b64(v["cifrado"])) == v["hash"] for v in votos)
    longitudes = {len(desde_b64(v["cifrado"])) for v in votos}
    informe.agregar("USB", "Votos: hash de cada voto cifrado", integros)
    informe.agregar("USB", "Votos: longitud uniforme (no revela la opción)", len(longitudes) <= 1)
    informe.agregar("USB", "Votos: sin duplicados", len(set(hashes)) == len(hashes))

    # Merkle y checkpoints
    raiz = raiz_merkle(hashes) if len(set(hashes)) == len(hashes) else ""
    cps = exp["checkpoints.json"]
    informe.agregar("USB", "Raíz de Merkle = acta de cierre = acta de escrutinio",
                    raiz == cierre["raiz_merkle"] == escrutinio["raiz_merkle"])
    secuencia = [c["seq"] for c in cps] == list(range(1, len(cps) + 1))
    crecientes = all(a["conteo"] <= b["conteo"] for a, b in zip(cps, cps[1:]))
    ultimo_ok = bool(cps) and cps[-1]["conteo"] == len(votos) and cps[-1]["raiz_merkle"] == raiz
    informe.agregar("USB", "Checkpoints: consecutivos, crecientes y el último = urna final",
                    secuencia and crecientes and ultimo_ok)

    # Conteos
    total_resultados = sum(escrutinio["resultados"].values())
    informe.agregar("USB", "Totales: urna = cierre = escrutinio = votantes marcados",
                    len(votos) == cierre["total_votos"] == escrutinio["total"] == total_resultados
                    == cierre["votantes_que_votaron"],
                    f"{len(votos)} votos")
    informe.agregar("USB", "Escrutinio encadenado al acta de cierre",
                    escrutinio["hash_acta_cierre"] == actas["CIERRE"]["hash"])

    # Boletas (código VVPAT → opción)
    boletas = escrutinio["boletas"]
    informe.agregar("USB", "Boletas: cada código VVPAT corresponde a un voto de la urna",
                    Counter(c for c, _ in boletas) == Counter(codigo_vvpat(h) for h in hashes))
    informe.agregar("USB", "Boletas: el conteo por opción = resultados del acta",
                    dict(Counter(o for _, o in boletas)) == {k: v for k, v in escrutinio["resultados"].items() if v})

    # Bitácora
    entradas = [{**e, "momento": datetime.fromisoformat(e["momento"])} for e in exp["bitacora.json"]]
    r = verificar_cadena(entradas, cierre["ultimo_hash_bitacora"])
    informe.agregar("USB", "Bitácora encadenada íntegra y contiene el hash del acta de cierre", r.integra,
                    f"{r.entradas} entradas" if r.integra else f"entrada {r.primera_falla}: {r.motivo}")
    eventos = {(e["evento"], e["detalle"].get("eleccion")): e["detalle"] for e in exp["bitacora.json"]}
    eid = eleccion["id"]
    informe.agregar("USB", "Bitácora registra apertura, cierre y escrutinio con los hashes de las actas",
                    eventos.get(("APERTURA", eid), {}).get("hash_zeresima") == actas["ZERESIMA"]["hash"]
                    and eventos.get(("CIERRE", eid), {}).get("hash_acta") == actas["CIERRE"]["hash"]
                    and eventos.get(("ESCRUTINIO", eid), {}).get("hash_acta") == actas["ESCRUTINIO"]["hash"])

    # Papel
    if conteo_papel is not None:
        diferencias = {k: (conteo_papel.get(k, 0), v) for k, v in escrutinio["resultados"].items()
                       if conteo_papel.get(k, 0) != v}
        informe.agregar("PAPEL", "Conteo manual de VVPAT = resultados digitales", not diferencias,
                        "; ".join(f"{k}: papel {p} ≠ digital {d}" for k, (p, d) in diferencias.items()))
    else:
        informe.agregar("PAPEL", "Conteo manual de VVPAT", None, "no ingresado")

    # Ledger (Hyperledger Fabric)
    if ledger is None:
        anclajes = [o for o in exp["outbox.json"]
                    if o["funcion"] == "RegistrarCierre"
                    and o["argumentos"].get("eleccion_global") == eleccion["eleccion_global"]
                    and o["argumentos"].get("mesa") == eleccion["mesa"]]
        informe.agregar("LEDGER", "Anclaje del cierre registrado para Fabric",
                        bool(anclajes) and anclajes[-1]["argumentos"]["raiz_merkle"] == cierre["raiz_merkle"])
        informe.agregar("LEDGER", "Comparación con el ledger de Hyperledger Fabric", None, motivo_sin_ledger)
    else:
        verificar_ledger(exp, ledger, informe)
    return informe


def verificar_ledger(exp: dict[str, Any], ledger: dict[str, Any], informe: Informe) -> None:
    """Compara lo anclado en Fabric con el paquete USB: si alguien modificó la base de datos y
    regeneró actas y paquete, no puede modificar el ledger (ADR-001)."""
    eleccion, actas = exp["eleccion.json"], exp["actas.json"]
    zeresima, cierre, escrutinio = (actas[t]["contenido"] for t in ("ZERESIMA", "CIERRE", "ESCRUTINIO"))
    huella_clave = firmas.huella(serialization.load_pem_public_key(eleccion["clave_publica_pem"].encode()))
    checkpoints = [{"seq": c["seq"], "conteo": c["conteo"], "raiz_merkle": c["raiz_merkle"]}
                   for c in exp["checkpoints.json"]]
    comprobaciones = [
        ("Registro: definición, clave de la elección y equipo",
         ledger.get("hash_configuracion") == eleccion["hash_configuracion"]
         and ledger.get("huella_clave_eleccion") == huella_clave
         and ledger.get("huella_dispositivo") == exp["dispositivo.json"]["huella"]),
        ("Apertura: hash de la zerésima y compromiso del padrón",
         ledger.get("hash_zeresima") == actas["ZERESIMA"]["hash"]
         and ledger.get("compromiso_padron") == zeresima["padron"]["compromiso"]),
        ("Checkpoints anclados = checkpoints del paquete", ledger.get("checkpoints") == checkpoints),
        ("Cierre: totales, raíz de Merkle y hash del acta",
         ledger.get("total_votos") == cierre["total_votos"]
         and ledger.get("raiz_merkle") == cierre["raiz_merkle"]
         and ledger.get("hash_acta_cierre") == actas["CIERRE"]["hash"]),
        ("Escrutinio: resultados y hash del acta",
         ledger.get("resultados") == escrutinio["resultados"]
         and ledger.get("hash_acta_escrutinio") == actas["ESCRUTINIO"]["hash"]),
        ("Exportación: hash del manifiesto del paquete USB",
         ledger.get("estado") == "EXPORTADA" and ledger.get("hash_manifiesto") == exp.get("_hash_manifiesto")),
    ]
    for nombre, ok in comprobaciones:
        informe.agregar("LEDGER", nombre, ok)
    return informe


def obtener_ledger(consultar_ledger, eleccion_json: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Consulta el estado anclado de la mesa. Devuelve (estado, motivo si no se pudo)."""
    if consultar_ledger is None:
        return None, "no se indicó un ledger (use --fabric)"
    from votoseguro.blockchain.cliente import PuenteNoDisponible

    try:
        estado = consultar_ledger(eleccion_json["eleccion_global"], eleccion_json["mesa"])
    except PuenteNoDisponible as e:
        return None, f"ledger no disponible: {e}"
    return estado, "la mesa no está registrada en el ledger"


def verificar_paquete(ruta: Path, frase: str, *, conteo_papel: dict[str, int] | None = None,
                      huella_esperada: str | None = None, consultar_ledger=None) -> Informe:
    """``consultar_ledger(eleccion_global, mesa)`` devuelve el estado anclado (p. ej.
    ``ClientePuente.consultar_mesa``)."""
    informe = Informe()
    expediente = abrir_paquete(ruta, frase, informe)
    if expediente is not None:
        ledger, motivo = obtener_ledger(consultar_ledger, expediente["eleccion.json"])
        if consultar_ledger is not None and ledger is None and "no está registrada" in motivo:
            informe.agregar("LEDGER", "La mesa está registrada en el ledger", False)
        verificar_expediente(expediente, informe, conteo_papel=conteo_papel, huella_esperada=huella_esperada,
                             ledger=ledger, motivo_sin_ledger=motivo)
        informe.expediente = expediente
    return informe
