#!/usr/bin/env bash
# Exporta el informe (docs/informe/*.md) a Word con formato UPEA y citas APA 7.
# Uso:  ./exportar_word.sh            → docs/salida/informe.docx
#       ./exportar_word.sh perfil     → solo capítulos I y II (perfil, Art. 30)
set -euo pipefail
cd "$(dirname "$0")"
command -v pandoc >/dev/null || { echo "Falta pandoc: sudo apt install pandoc"; exit 1; }
PY=../../app/.venv/bin/python; [ -x "$PY" ] || PY=python3
[ -f plantilla_upea.docx ] || "$PY" crear_plantilla.py

if [ "${1:-}" = "perfil" ]; then
  archivos=(../informe/00-preliminares.md ../informe/01-marco-preliminar.md ../informe/02-marco-teorico.md)
  salida=../salida/perfil.docx
else
  archivos=(../informe/0*.md)
  salida=../salida/informe.docx
fi
mkdir -p ../salida
# Las citas solo se procesan en el último archivo con {#refs}; para el perfil se agrega al final.
pandoc "${archivos[@]}" \
  --metadata-file=metadata.yaml \
  --resource-path=..:../adjuntos:../diagramas \
  --citeproc --toc --toc-depth=3 \
  --reference-doc=plantilla_upea.docx \
  -o "$salida"
echo "Generado: $(realpath "$salida")"
