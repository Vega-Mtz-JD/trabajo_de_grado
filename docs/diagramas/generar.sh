#!/usr/bin/env bash
# Regenera todas las figuras del informe (docs/adjuntos/diagramas/*.png y *.svg).
#   docs/diagramas/generar.sh            # todas
#   docs/diagramas/generar.sh fig_1_1    # solo las que empiezan así
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$DIR/../../app/.venv/bin/python"
[ -x "$PY" ] || { echo "Falta el entorno Python del sistema (scripts/instalar_dependencias.sh)"; exit 1; }
cd "$DIR"
for f in ${1:-fig_}*.py; do
  echo "==> $f"
  QT_QPA_PLATFORM=offscreen "$PY" "$f"
done
