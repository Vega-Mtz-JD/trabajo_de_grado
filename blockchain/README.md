# Módulo blockchain — Hyperledger Fabric 2.5

| Carpeta | Contenido | Sprint |
|---|---|---|
| `network/` | `compose.yaml`, `configtx.yaml`, scripts `up.sh` / `down.sh` (1 CA, 1 orderer Raft, 1 peer LevelDB, canal `elecciones`) | 3 |
| `chaincode/acta/` | Smart contract en Go: `RegistrarEleccion`, `RegistrarApertura`, `RegistrarCheckpoint`, `RegistrarCierre`, `RegistrarEscrutinio`, `RegistrarExportacion`, consultas | 3 |
| `bridge/` | Servicio Go con `fabric-gateway`, REST en `127.0.0.1` para la app Python | 3 |

Ver `docs/decisiones/ADR-001`, `ADR-002` y `ADR-007`.
