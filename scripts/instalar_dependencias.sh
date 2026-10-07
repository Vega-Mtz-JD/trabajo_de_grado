#!/usr/bin/env bash
# Instala TODO lo necesario para VOTO SEGURO en un Debian 13 recién instalado (requiere Internet).
# Es idempotente: lo que ya está instalado se salta. Ejecutar como usuario normal (pide sudo para apt).
#
#   scripts/instalar_dependencias.sh                 # todo
#   scripts/instalar_dependencias.sh --sin-sistema   # sin apt (paquetes del sistema ya instalados)
#
# Pasos: 1) paquetes Debian  2) entorno Python de la aplicación  3) Go en ~/.local/go
#        4) binarios e imágenes de Hyperledger Fabric 2.5.16
# Después: sudo scripts/instalar_bd_desarrollo.sh  y  blockchain/network/up.sh
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
GO_VERSION=1.26.8
GO_SHA256=d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b
FABRIC_VERSION=2.5.16
SISTEMA=true
[ "${1:-}" = "--sin-sistema" ] && SISTEMA=false
[ "$(id -u)" -ne 0 ] || { echo "Ejecutar como usuario normal (no con sudo): el script pide sudo cuando lo necesita."; exit 1; }
paso() { printf '\n==> %s\n' "$*"; }

if $SISTEMA; then
  paso "1. Paquetes del sistema (Debian 13)"
  sudo apt-get update
  PAQUETES=(python3 python3-venv python3-dev build-essential git curl gnupg postgresql postgresql-17-pgaudit
            pandoc libreoffice-writer poppler-utils libxcb-cursor0 libgl1)
  # Docker: solo si no existe (un docker-ce ya instalado chocaría con docker.io de Debian)
  command -v docker >/dev/null 2>&1 || PAQUETES+=(docker.io docker-compose)
  sudo apt-get install -y "${PAQUETES[@]}"
  if ! id -nG "$USER" | grep -qw docker; then
    sudo usermod -aG docker "$USER"
    echo "  Se agregó $USER al grupo docker: CIERRE SESIÓN y vuelva a entrar antes del paso 4."
  fi
else
  paso "1. Paquetes del sistema: omitido (--sin-sistema)"
fi

paso "2. Entorno Python de la aplicación (app/.venv)"
if [ ! -x "$RAIZ/app/.venv/bin/python" ]; then
  python3 -m venv "$RAIZ/app/.venv"
fi
"$RAIZ/app/.venv/bin/pip" install -q --upgrade pip
"$RAIZ/app/.venv/bin/pip" install -q -e "$RAIZ/app[ui,dev,docs]"
"$RAIZ/app/.venv/bin/votoseguro" --version

paso "3. Go $GO_VERSION en ~/.local/go (para compilar el chaincode y el puente)"
if [ -x "$HOME/.local/go/bin/go" ] && "$HOME/.local/go/bin/go" version | grep -q "go$GO_VERSION"; then
  echo "  Ya instalado: $("$HOME/.local/go/bin/go" version)"
else
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/go.tgz" "https://go.dev/dl/go$GO_VERSION.linux-amd64.tar.gz"
  echo "$GO_SHA256  $TMP/go.tgz" | sha256sum -c -
  mkdir -p "$HOME/.local/go-$GO_VERSION"
  tar -xzf "$TMP/go.tgz" -C "$HOME/.local/go-$GO_VERSION" --strip-components=1
  ln -sfn "$HOME/.local/go-$GO_VERSION" "$HOME/.local/go"
  rm -rf "$TMP"
  "$HOME/.local/go/bin/go" version
fi

paso "4. Hyperledger Fabric $FABRIC_VERSION: binarios (blockchain/network/bin) e imágenes Docker"
RED="$RAIZ/blockchain/network"
if [ -x "$RED/bin/peer" ] && "$RED/bin/peer" version | grep -q "v$FABRIC_VERSION"; then
  echo "  Binarios ya instalados ($("$RED/bin/peer" version | sed -n 's/ *Version: //p'))"
else
  curl -fsSL "https://github.com/hyperledger/fabric/releases/download/v$FABRIC_VERSION/hyperledger-fabric-linux-amd64-$FABRIC_VERSION.tar.gz" \
    | tar -xz -C "$RED" bin/ config/
fi
for imagen in peer orderer baseos; do
  if docker image inspect "hyperledger/fabric-$imagen:$FABRIC_VERSION" >/dev/null 2>&1; then
    echo "  Imagen fabric-$imagen:$FABRIC_VERSION ya descargada"
  else
    docker pull -q "hyperledger/fabric-$imagen:$FABRIC_VERSION"
  fi
done

cat <<FIN

==> Dependencias listas. Siguientes pasos:
  1. sudo scripts/instalar_bd_desarrollo.sh        (roles, base de datos y migraciones)
  2. blockchain/network/up.sh && blockchain/bridge/iniciar.sh   (Fabric + puente; opcional)
  3. cd app && . .venv/bin/activate && export VOTOSEGURO_DSN='dbname=votoseguro' && votoseguro-ui
Para operar SIN Internet en producción, conserve las imágenes con:
  docker save hyperledger/fabric-{peer,orderer,baseos}:$FABRIC_VERSION -o fabric-imagenes.tar
FIN
