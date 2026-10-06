#!/usr/bin/env bash
# Compila e inicia el puente Go en segundo plano (solo escucha en 127.0.0.1:8770).
# El token compartido con la aplicación se genera una vez en ~/.config/votoseguro/puente.token.
set -euo pipefail
PUENTE="$(cd "$(dirname "$0")" && pwd)"
source "$PUENTE/../network/entorno.sh"
TOKEN_ARCHIVO="$HOME/.config/votoseguro/puente.token"
if [ ! -f "$TOKEN_ARCHIVO" ]; then
  mkdir -p "$(dirname "$TOKEN_ARCHIVO")"
  (umask 077 && head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$TOKEN_ARCHIVO")
fi
if [ -f "$PUENTE/puente.pid" ] && kill -0 "$(cat "$PUENTE/puente.pid")" 2>/dev/null; then
  echo "El puente ya está en ejecución (PID $(cat "$PUENTE/puente.pid"))."; exit 0
fi
(cd "$PUENTE" && go build -trimpath -o puente .)
USUARIO="$ORG_MESA/users/User1@mesa.votoseguro.local/msp"
VOTOSEGURO_PUENTE_TOKEN="$(cat "$TOKEN_ARCHIVO")" \
FABRIC_TLS_CA="$ORG_MESA/peers/peer0.mesa.votoseguro.local/tls/ca.crt" \
FABRIC_CERT="$(ls "$USUARIO"/signcerts/*.pem)" \
FABRIC_KEYSTORE="$USUARIO/keystore" \
  nohup "$PUENTE/puente" >> "$PUENTE/puente.log" 2>&1 &
echo $! > "$PUENTE/puente.pid"
for i in $(seq 1 20); do
  curl -sf http://127.0.0.1:8770/salud >/dev/null 2>&1 && { echo "Puente listo en http://127.0.0.1:8770 (PID $!)"; exit 0; }
  sleep 0.5
done
echo "El puente no respondió; revise $PUENTE/puente.log"; exit 1
