---
tipo: sprint
sprint: 4
inicio: 2026-10-05
fin: 2026-10-05
estado: cerrado
---
# Sprint 4 — Hyperledger Fabric: red, chaincode, puente y anclaje

## Objetivo del sprint
Levantar la red Hyperledger Fabric 2.5 mononodo, implementar el chaincode `acta` y el puente Go,
anclar todos los hitos electorales desde el outbox y completar el nivel **LEDGER** de la auditoría triple.

## Backlog del sprint
- [x] Go 1.26.8 en `~/.local/go`; binarios e imágenes de Fabric 2.5.16
- [x] Red: `cryptogen`, canal `elecciones` sin canal de sistema, orderer Raft, peer LevelDB (`blockchain/network/`)
- [x] `up.sh` idempotente: crypto, bloque génesis, CCaaS, unión al canal, ciclo de vida con secuencia
- [x] Chaincode `acta` en Go: 6 hitos con validación de la máquina de estados, idempotencia, consulta e historial
- [x] Puente Go con `fabric-gateway`: REST local con token, lista blanca, mapeo de errores 409/503/404
- [x] Cliente Python del puente y sincronizador del outbox (orden estricto, modo degradado, rechazo → ERROR)
- [x] Anclaje automático tras cada hito; bitácora `MODO_DEGRADADO` / `ANCLAJE_RESTABLECIDO` / `ANCLAJE_RECHAZADO`
- [x] Verificador: 6 comprobaciones LEDGER (registro, apertura, checkpoints, cierre, escrutinio, exportación)
- [x] CLI: `--fabric` en demo/verificar/consolidar; comandos `sincronizar` y `ledger`

## Hechos técnicos y hallazgos
- **Chaincode como servicio (CCaaS):** el peer no compila ni descarga nada → operación offline ([[ADR-010-red-fabric-ccaas]]).
- **Hallazgo 1 — paquete no reproducible:** el `tar.gz` del chaincode incluía fechas; cada ejecución daba un
  identificador distinto y el peer quedaba esperando a un chaincode inexistente (consulta colgada). Solución:
  empaquetado reproducible y actualización por **secuencia** del ciclo de vida.
- **Hallazgo 2 — hueco de auditoría:** con CCaaS el paquete no contiene el código, así que cambiar el binario
  no pasaba por el ciclo de vida. Solución: hash SHA-256 del binario en la etiqueta del paquete. Se comprobó:
  la actualización del historial pasó a la **secuencia 3**, registrada en el ledger.
- El contract API exigía en su esquema todos los campos de la respuesta → las consultas devuelven JSON como texto.
- Fabric 2.x entrega el historial del más nuevo al más antiguo → el chaincode lo devuelve cronológico.

## Pruebas
| Conjunto | Resultado |
|---|---|
| Python (`pytest`, incluye `-m fabric` con la red levantada) | **108 aprobadas**, cobertura **94 %** |
| Chaincode Go (`go test`) | 7 aprobadas (lógica + contrato con stub en memoria), 71 % |
| Puente Go (`go test`) | 7 aprobadas (token, lista blanca, errores, consultas), 40 % (el adaptador Fabric se cubre en integración) |
| Integración Fabric real | Elección completa anclada (7 transacciones VALID) y verificada CONFORME con 6/6 LEDGER; rechazo de hitos incoherentes; CLI con 2 mesas |
| `bandit` | 0 hallazgos |

**Rendimiento medido** (20 transacciones, red local): anclaje **0,525 s** de media (p95 0,526 s), consulta 5,7 ms.
Objetivo de la propuesta: ≤ 3 s → cumplido.

## Evidencias para el informe
- `votoseguro ledger <eleccion> <mesa>`: estado anclado + historial de transacciones → Cap. III y IV.
- Salida de `demo --fabric` con las 6 comprobaciones LEDGER en verde → Cap. IV §4.5.
- Tabla de latencia → Cap. IV (eficiencia de desempeño, ISO/IEC 25010).
- Diagrama de despliegue: aplicación ↔ PostgreSQL / puente ↔ peer ↔ orderer ↔ chaincode (pendiente).

## Retrospectiva
- Bien: probar contra la red real destapó dos problemas que las pruebas unitarias no podían ver.
- Mejorar: agregar migraciones versionadas de la BD (pendiente desde el Sprint 3) y el diagrama de despliegue.
