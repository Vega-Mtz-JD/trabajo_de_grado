# Registro de Decisiones de Arquitectura (ADR)

Cada ADR documenta **una** decisión técnica relevante: contexto, decisión y consecuencias.
Sirven como evidencia del proceso de ingeniería en el documento de Proyecto de Grado.

| # | Decisión | Estado |
|---|---|---|
| [001](ADR-001-blockchain-fabric.md) | Hyperledger Fabric 2.5 mononodo con anclaje en papel | Aceptada |
| [002](ADR-002-puente-go.md) | Integración Python ↔ Fabric mediante puente Go (fabric-gateway) | Aceptada |
| [003](ADR-003-cifrado-umbral.md) | Cifrado híbrido de votos + Shamir 3-de-5 para la clave de elección | Aceptada |
| [004](ADR-004-secreto-del-voto.md) | Secreto del voto: sin timestamps, IDs aleatorios, checkpoints por lotes | Aceptada |
| [005](ADR-005-interfaz-kiosco.md) | PySide6 + compositor `cage` para el modo kiosco | Aceptada |
| [006](ADR-006-abstraccion-hardware.md) | Interfaces de hardware; ZKTeco + ESC/POS, con simuladores | Aceptada |
| [007](ADR-007-leveldb.md) | LevelDB como base de estado de Fabric (en lugar de CouchDB) | Aceptada |
| [008](ADR-008-postgresql.md) | PostgreSQL 17 como BD del sistema (reemplaza SQLite/SQLCipher) + mezcla de urna | Propuesta |
| [009](ADR-009-varias-mesas.md) | Varias urnas: definición exportable, padrón dividido local, foto, consolidación | Aceptada |
| [010](ADR-010-red-fabric-ccaas.md) | Red Fabric: cryptogen, chaincode como servicio, hash del binario en el ciclo de vida | Aceptada |

Plantilla: `Estado · Contexto · Decisión · Consecuencias`.
