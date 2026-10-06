#!/usr/bin/env bash
# Detiene la red. Con --borrar elimina además el ledger (volúmenes), el material
# criptográfico y el bloque del canal: la próxima ejecución de up.sh crea una red nueva.
set -euo pipefail
source "$(dirname "$0")/entorno.sh"
cd "$RED"
export CHAINCODE_ID=detenido
if [ "${1:-}" = "--borrar" ]; then
  docker compose down -v --remove-orphans
  rm -rf organizations channel-artifacts build
  echo "Red eliminada (ledger, certificados y artefactos)."
else
  docker compose down --remove-orphans
  echo "Red detenida (el ledger se conserva)."
fi
