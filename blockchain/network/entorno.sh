# Variables comunes de la red (se carga con "source"). Rutas relativas a blockchain/network.
RED="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$RED/bin:$HOME/.local/go/bin:$PATH"
export GOTOOLCHAIN=local
export FABRIC_CFG_PATH="$RED/config"          # core.yaml para el CLI "peer"
CANAL=elecciones
CC_NOMBRE=acta
CC_VERSION=1.0
CC_SECUENCIA=1
ORG_ORD="$RED/organizations/ordererOrganizations/ordenante.votoseguro.local"
ORG_MESA="$RED/organizations/peerOrganizations/mesa.votoseguro.local"
ORDERER_CA="$ORG_ORD/tlsca/tlsca.ordenante.votoseguro.local-cert.pem"
ORDERER_TLS="$ORG_ORD/orderers/orderer.ordenante.votoseguro.local/tls"

# Identidad de administrador de la mesa para el CLI "peer"
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID=MesaMSP
export CORE_PEER_ADDRESS=localhost:7051
export CORE_PEER_TLS_ROOTCERT_FILE="$ORG_MESA/peers/peer0.mesa.votoseguro.local/tls/ca.crt"
export CORE_PEER_MSPCONFIGPATH="$ORG_MESA/users/Admin@mesa.votoseguro.local/msp"
