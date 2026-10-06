#!/usr/bin/env bash
# Detiene el puente Go.
PUENTE="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$PUENTE/puente.pid" ] && kill "$(cat "$PUENTE/puente.pid")" 2>/dev/null; then
  echo "Puente detenido."
else
  echo "El puente no estaba en ejecución."
fi
rm -f "$PUENTE/puente.pid"
