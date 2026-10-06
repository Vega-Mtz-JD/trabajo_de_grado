#!/usr/bin/env bash
# Levanta la red Fabric mononodo de VOTO SEGURO y despliega el chaincode "acta" (CCaaS).
# Idempotente: si algo ya existe, lo reutiliza. No requiere internet si las imágenes ya están.
set -euo pipefail
source "$(dirname "$0")/entorno.sh"
cd "$RED"
paso() { printf '\n==> %s\n' "$*"; }

if [ ! -d organizations ]; then
  paso "Generando material criptográfico (cryptogen)"
  cryptogen generate --config=crypto-config.yaml --output=organizations
fi

if [ ! -f channel-artifacts/$CANAL.block ]; then
  paso "Generando el bloque génesis del canal '$CANAL'"
  mkdir -p channel-artifacts
  FABRIC_CFG_PATH="$RED" configtxgen -profile CanalElecciones -outputBlock channel-artifacts/$CANAL.block \
    -channelID $CANAL 2>&1 | tail -1
fi

paso "Compilando el chaincode (binario Go estático)"
mkdir -p build
(cd ../chaincode/acta && CGO_ENABLED=0 GOOS=linux go build -trimpath -o "$RED/build/acta" .)

paso "Empaquetando el chaincode como servicio (CCaaS)"
TMP="$(mktemp -d)"
cat > "$TMP/connection.json" <<JSON
{"address": "acta.mesa.votoseguro.local:9999", "dial_timeout": "10s", "tls_required": false}
JSON
# La etiqueta incluye el hash del binario: con CCaaS el paquete no contiene el código, así que sin
# esto un cambio de código no pasaría por el ciclo de vida (no quedaría registrado en el ledger).
HASH_BINARIO="$(sha256sum build/acta | cut -c1-16)"
echo "{\"type\": \"ccaas\", \"label\": \"${CC_NOMBRE}_${CC_VERSION}_${HASH_BINARIO}\"}" > "$TMP/metadata.json"
# Empaquetado reproducible: mismo contenido → mismo identificador de paquete en cada ejecución.
tar_fijo() { local dir="$1" salida="$2"; shift 2
  tar -C "$dir" --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -cf - "$@" | gzip -n > "$salida"; }
tar_fijo "$TMP" "$TMP/code.tar.gz" connection.json
tar_fijo "$TMP" build/$CC_NOMBRE.tar.gz metadata.json code.tar.gz
rm -rf "$TMP"
export CHAINCODE_ID="$(peer lifecycle chaincode calculatepackageid build/$CC_NOMBRE.tar.gz)"
echo "Identificador del paquete: $CHAINCODE_ID"

paso "Iniciando contenedores (orderer, peer0, acta)"
docker compose up -d --wait 2>&1 | grep -v "^\s*$" | tail -5
docker compose restart acta >/dev/null   # carga el binario recién compilado del chaincode

paso "Uniendo el orderer al canal (channel participation)"
if ! osnadmin channel list -o localhost:7053 --ca-file "$ORDERER_CA" --client-cert "$ORDERER_TLS/server.crt" \
     --client-key "$ORDERER_TLS/server.key" 2>/dev/null | grep -q "\"$CANAL\""; then
  osnadmin channel join --channelID $CANAL --config-block channel-artifacts/$CANAL.block -o localhost:7053 \
    --ca-file "$ORDERER_CA" --client-cert "$ORDERER_TLS/server.crt" --client-key "$ORDERER_TLS/server.key" >/dev/null
fi

paso "Uniendo el peer al canal"
for i in $(seq 1 10); do peer channel list >/dev/null 2>&1 && break; sleep 1; done
if ! peer channel list 2>/dev/null | grep -qx "$CANAL"; then
  peer channel join -b channel-artifacts/$CANAL.block 2>&1 | tail -1
fi

paso "Instalando, aprobando y confirmando el chaincode '$CC_NOMBRE'"
if ! peer lifecycle chaincode queryinstalled 2>/dev/null | grep -q "$CHAINCODE_ID"; then
  peer lifecycle chaincode install build/$CC_NOMBRE.tar.gz 2>&1 | tail -1
fi
ORDENADOR=(-o localhost:7050 --ordererTLSHostnameOverride orderer.ordenante.votoseguro.local --tls --cafile "$ORDERER_CA")
# Ciclo de vida: si no hay definición confirmada, se usa la secuencia 1; si la confirmada apunta
# a otro paquete (chaincode actualizado), se aprueba y confirma la secuencia siguiente.
SECUENCIA=""
if CONFIRMADA="$(peer lifecycle chaincode querycommitted -C $CANAL -n $CC_NOMBRE 2>/dev/null)"; then
  ACTUAL="$(sed -n 's/.*Sequence: \([0-9]*\).*/\1/p' <<<"$CONFIRMADA")"
  if ! peer lifecycle chaincode queryapproved -C $CANAL -n $CC_NOMBRE --sequence "$ACTUAL" 2>/dev/null \
       | grep -q "$CHAINCODE_ID"; then
    SECUENCIA=$((ACTUAL + 1))
    echo "El paquete cambió: actualizando el chaincode a la secuencia $SECUENCIA"
  fi
else
  SECUENCIA=$CC_SECUENCIA
fi
if [ -n "$SECUENCIA" ]; then
  for i in $(seq 1 15); do   # el orderer necesita unos segundos para elegir líder (Raft)
    peer lifecycle chaincode approveformyorg "${ORDENADOR[@]}" -C $CANAL -n $CC_NOMBRE -v $CC_VERSION \
      --package-id "$CHAINCODE_ID" --sequence "$SECUENCIA" >/dev/null 2>&1 && break
    sleep 2
  done
  peer lifecycle chaincode commit "${ORDENADOR[@]}" -C $CANAL -n $CC_NOMBRE -v $CC_VERSION \
    --sequence "$SECUENCIA" --peerAddresses localhost:7051 --tlsRootCertFiles "$CORE_PEER_TLS_ROOTCERT_FILE" 2>&1 | tail -1
fi
peer lifecycle chaincode querycommitted -C $CANAL -n $CC_NOMBRE 2>&1 | tail -1

paso "Red lista. Puente: blockchain/bridge/iniciar.sh"
