#!/usr/bin/env bash
# Respaldo CIFRADO de la base de datos (AES-256 con frase, vía gpg) en una carpeta (p. ej. el USB).
#
#   sudo scripts/respaldo_bd.sh /media/usb               # crea votoseguro_AAAAMMDD_HHMM.dump.gpg
#   sudo scripts/respaldo_bd.sh --restaurar ARCHIVO      # restaura en la BD votoseguro_restaurada
#
# El respaldo contiene el padrón (datos personales) y los votos cifrados: se protege con una frase
# que se pide al ejecutar. Las fotos y huellas ya están cifradas con la clave del equipo (llavero).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecutar con sudo"; exit 1; }
command -v gpg >/dev/null || { echo "Falta gpg: sudo apt install gnupg"; exit 1; }

if [ "${1:-}" = "--restaurar" ]; then
  ARCHIVO="${2:?indique el archivo .dump.gpg}"
  sudo -u postgres psql -q -c "DROP DATABASE IF EXISTS votoseguro_restaurada" \
                        -c "CREATE DATABASE votoseguro_restaurada"
  # Sin --no-owner: los objetos deben seguir perteneciendo a vs_propietario (las funciones SECURITY DEFINER,
  # como urna.emitir_voto, dependen de ello). Los roles ya existen en la instancia (roles.sql).
  gpg --decrypt "$ARCHIVO" | (cd / && sudo -u postgres pg_restore -d votoseguro_restaurada)
  sudo -u postgres psql -q -c "GRANT CREATE ON DATABASE votoseguro_restaurada TO vs_propietario"
  sudo -u postgres psql -q -d votoseguro_restaurada -c "SELECT version, nombre FROM meta.migracion ORDER BY 1"
  echo "Restaurado en la BD votoseguro_restaurada. Compruebe los datos antes de reemplazar la original."
  exit 0
fi

DESTINO="${1:?indique la carpeta de destino (p. ej. el USB)}"
[ -d "$DESTINO" ] || { echo "No existe la carpeta $DESTINO"; exit 1; }
ARCHIVO="$DESTINO/votoseguro_$(date +%Y%m%d_%H%M).dump.gpg"
(cd / && sudo -u postgres pg_dump -Fc votoseguro) \
  | gpg --symmetric --cipher-algo AES256 --pinentry-mode loopback -o "$ARCHIVO"
sha256sum "$ARCHIVO" | tee "$ARCHIVO.sha256"
echo "Respaldo cifrado: $ARCHIVO"
