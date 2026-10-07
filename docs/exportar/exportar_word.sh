#!/usr/bin/env bash
# Exporta el informe (docs/informe/*.md) a Word con formato UPEA y citas APA 7.
# Uso:  ./exportar_word.sh            → docs/salida/informe.docx
#       ./exportar_word.sh perfil     → solo capítulos I y II (perfil, Art. 30)
#       ./exportar_word.sh manuales   → manual de usuario y manual técnico por separado
set -euo pipefail
cd "$(dirname "$0")"
command -v pandoc >/dev/null || { echo "Falta pandoc: sudo apt install pandoc"; exit 1; }
PY=../../app/.venv/bin/python; [ -x "$PY" ] || PY=python3
[ -f plantilla_upea.docx ] || "$PY" crear_plantilla.py

mkdir -p ../salida
if [ "${1:-}" = "perfil" ]; then
  archivos=(../informe/00-preliminares.md ../informe/01-marco-preliminar.md ../informe/02-marco-teorico.md)
  salida=../salida/perfil.docx
elif [ "${1:-}" = "manuales" ]; then
  # Cada manual como documento independiente (capacitación), sin el rótulo «Anexo X.»
  declare -A titulos=([usuario]="Manual de usuario y guía de capacitación" [tecnico]="Manual técnico")
  for m in usuario tecnico; do
    tmp="$(mktemp --suffix=.md)"
    sed '1s/^# Anexo [AB]\. \(.*\) {\.unnumbered}$/# \1 {.unnumbered}/' "../manuales/manual-$m.md" > "$tmp"
    pandoc "$tmp" --metadata-file=metadata.yaml -M title="VOTO SEGURO — ${titulos[$m]}" -M subtitle="Sistema de votación electrónica offline con blockchain" \
      --resource-path=..:../adjuntos:../manuales --toc --toc-depth=2 \
      --reference-doc=plantilla_upea.docx -o "../salida/manual-$m.docx"
    rm -f "$tmp"
    echo "Generado: $(realpath "../salida/manual-$m.docx")"
  done
  exit 0
else
  archivos=(../informe/0*.md ../manuales/manual-usuario.md ../manuales/manual-tecnico.md)
  salida=../salida/informe.docx
fi
# Las citas solo se procesan en el último archivo con {#refs}; para el perfil se agrega al final.
pandoc "${archivos[@]}" \
  --metadata-file=metadata.yaml \
  --resource-path=..:../adjuntos:../diagramas \
  --citeproc --toc --toc-depth=3 \
  --reference-doc=plantilla_upea.docx \
  -o "$salida"
echo "Generado: $(realpath "$salida")"
