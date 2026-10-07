#!/usr/bin/env bash
# Inicia VOTO SEGURO (interfaz gráfica) en el equipo de desarrollo o de demostración.
#
#   scripts/iniciar_votoseguro.sh                     # interfaz, cámara web si existe
#   scripts/iniciar_votoseguro.sh --fabric            # además levanta Fabric y el puente y ancla
#   scripts/iniciar_votoseguro.sh --camara-simulada   # sin usar la cámara web
#
# Antes (una sola vez): scripts/instalar_dependencias.sh  y  sudo scripts/instalar_bd_desarrollo.sh
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ARGS=(--camara auto)
FABRIC=false
for opcion in "$@"; do
  case "$opcion" in
    --fabric) FABRIC=true ;;
    --camara-simulada) ARGS=(--camara simulada) ;;
    *) echo "Opción desconocida: $opcion"; exit 2 ;;
  esac
done

[ -x "$RAIZ/app/.venv/bin/votoseguro-ui" ] || { echo "Falta el entorno Python: ejecute scripts/instalar_dependencias.sh"; exit 1; }
pg_isready -q || { echo "PostgreSQL no está en ejecución. Inícielo con:  sudo systemctl start postgresql"; exit 1; }
export VOTOSEGURO_DSN="${VOTOSEGURO_DSN:-dbname=votoseguro}"
if "$RAIZ/app/.venv/bin/votoseguro" bd estado 2>/dev/null | grep -qE "PENDIENTE|MODIFICADA" \
   || ! "$RAIZ/app/.venv/bin/votoseguro" bd estado >/dev/null 2>&1; then
  echo "La base de datos no está instalada o le faltan migraciones. Ejecute:"
  echo "  sudo scripts/instalar_bd_desarrollo.sh"
  exit 1
fi

if $FABRIC; then
  if ! curl -sf --max-time 3 http://127.0.0.1:8770/salud >/dev/null; then
    echo "==> Levantando Hyperledger Fabric y el puente…"
    "$RAIZ/blockchain/network/up.sh" >/dev/null
    "$RAIZ/blockchain/bridge/iniciar.sh"
  fi
  ARGS+=(--fabric)
fi

echo "==> Iniciando VOTO SEGURO (impresiones simuladas en $RAIZ/salida_ui/impresiones)"
cd "$RAIZ"
exec "$RAIZ/app/.venv/bin/votoseguro-ui" "${ARGS[@]}" --salida "$RAIZ/salida_ui"
