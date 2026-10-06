# Módulo blockchain — Hyperledger Fabric 2.5.16

| Carpeta | Contenido |
|---|---|
| `network/` | `crypto-config.yaml`, `configtx.yaml`, `compose.yaml`, `up.sh`, `down.sh`, `entorno.sh` |
| `chaincode/acta/` | Chaincode Go: `RegistrarEleccion`, `RegistrarApertura`, `RegistrarCheckpoint`, `RegistrarCierre`, `RegistrarEscrutinio`, `RegistrarExportacion`, `ConsultarMesa`, `ConsultarHistorial` |
| `bridge/` | Puente Go (`fabric-gateway`): REST en `127.0.0.1:8770`, `iniciar.sh`, `detener.sh` |

## Uso

```bash
blockchain/network/up.sh          # red + canal + chaincode (idempotente; actualiza el chaincode si cambió)
blockchain/bridge/iniciar.sh      # puente Go en segundo plano (token en ~/.config/votoseguro/puente.token)
votoseguro demo --mesas 2 --fabric
votoseguro ledger <eleccion_global> <mesa>
blockchain/bridge/detener.sh
blockchain/network/down.sh        # detiene (conserva el ledger);  --borrar  elimina todo
```

Requisitos: Docker, Go ≥ 1.25 (`~/.local/go`), binarios de Fabric en `network/bin` e imágenes
`hyperledger/fabric-{peer,orderer,baseos}:2.5.16`. Pruebas: `go test ./...` en `chaincode/acta` y `bridge`;
integración: `pytest -m fabric` (en `app/`).

Ver `docs/decisiones/ADR-001`, `ADR-002`, `ADR-007` y `ADR-010`.
