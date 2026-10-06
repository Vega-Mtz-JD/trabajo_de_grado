# ADR-008 — PostgreSQL 17 como base de datos del sistema

**Estado:** Propuesta (pendiente del visto bueno de la tutora metodológica) · 2026-10-05
**Reemplaza:** SQLite + SQLCipher de la propuesta v5 (§15)

## Contexto

La tutora metodológica no acepta bases de datos ligeras (SQLite, entornos tipo phpMyAdmin). Exige
un SGBD robusto, de nivel "semi-empresarial", elegido según el proyecto. Este proyecto tiene
requisitos particulares:

1. Opera **offline** en un solo equipo con Debian 13, que ya ejecuta Docker y Fabric.
2. Necesita **mínimo privilegio real**: la aplicación debe poder *insertar* votos, pero no
   modificarlos ni borrarlos, y solo puede cambiar la columna `ya_voto` del padrón.
3. La guía de la tutora pide poder responder *¿quién, cuándo y a qué hora?* ante un acceso no
   autorizado (ISO/IEC 27000), es decir, **auditoría a nivel de base de datos**.
4. Necesita **licencia libre** compatible con Apache 2.0, sin costo para la empresa.
5. Debe proteger el **secreto del voto** (ADR-004).

## Comparación

| Criterio | **PostgreSQL 17** | Oracle Database Free (ex-XE) | MySQL / MariaDB | SQL Server Express |
|---|---|---|---|---|
| Licencia / costo | PostgreSQL License (libre), 0 USD | Propietaria, gratuita con límites | GPL (MySQL dual-licensed); MariaDB GPL | Propietaria, gratuita con límites |
| Soporte en Debian 13 | **Paquete oficial** (`postgresql-17`) | Solo en contenedor; soporte oficial para Oracle Linux/RHEL | Paquete oficial (MariaDB) | **No soportado** en Debian |
| Límites | Ninguno práctico | ~2 hilos de CPU, 2 GB de RAM, 12 GB de datos | Ninguno | 10 GB por BD |
| Privilegios por columna | Sí | Sí | Sí | Sí |
| Triggers *append-only* y CHECK | Completos | Completos | Más limitados | Completos |
| Auditoría | **pgaudit** (paquete Debian `postgresql-17-pgaudit`) | Unified Auditing | Plugins de auditoría (MariaDB) | SQL Server Audit |
| Row-Level Security | Sí | Sí (VPD, más complejo) | No | Sí |
| Conexión sin red | **Socket Unix + autenticación `peer`** | TCP (listener) | Socket Unix | TCP |
| Percepción académica | SGBD empresarial libre de referencia | Empresarial | A menudo se percibe como "ligera" | Empresarial |
| Consumo de RAM | Bajo o medio | Alto | Bajo | Medio |

## Decisión

Usar **PostgreSQL 17** (paquete nativo de Debian 13, sin Docker), con las siguientes medidas.

### Seguridad de la instancia
- `listen_addresses = ''`: **no abre ningún puerto TCP**. Solo acepta conexiones por socket Unix,
  con autenticación `peer` (la identidad del usuario de Linux), lo que es coherente con el diseño offline.
- Contraseñas SCRAM-SHA-256 para los roles humanos (auditor y administrador de BD).
- Disco cifrado con LUKS. Los datos sensibles ya están cifrados en la aplicación: los votos con la clave
  de umbral (ADR-003) y las plantillas de huella con AES-256-GCM. PostgreSQL comunitario no tiene
  TDE (cifrado transparente), por eso se usa esta combinación.

### Roles (mínimo privilegio)
| Rol | Permisos |
|---|---|
| `vs_propietario` (NOLOGIN) | Dueño de los esquemas y de las funciones `SECURITY DEFINER` |
| `vs_app` | **Sin** `INSERT` directo en `urna.voto` ni `UPDATE` de `ya_voto`: vota solo con la función `urna.emitir_voto()` (`SECURITY DEFINER`, atómica). `INSERT` en bitácora, actas y checkpoints; `UPDATE` solo de columnas puntuales (`estado`, datos del padrón antes de la apertura) |
| `vs_auditor` | Solo lectura en todo |
| `vs_admin_bd` | Mantenimiento y respaldos; no tiene acceso a la clave de la elección |

### Esquemas
`eleccion`, `padron`, `urna`, `auditoria` y `blockchain` (outbox). Separarlos permite otorgar
permisos por esquema y explicar el diseño con claridad en el informe.

### Inmutabilidad
Triggers `BEFORE UPDATE OR DELETE` y `BEFORE TRUNCATE` que lanzan una excepción en
`urna.voto`, `auditoria.bitacora` y `eleccion.acta`. Además, `vs_app` no tiene esos privilegios.

### Auditoría en dos niveles
1. **pgaudit** registra DDL, cambios de roles y escrituras con rol y marca de tiempo.
   Se configura `pgaudit.log_parameter = off` para que **no** queden en el log los valores
   insertados, ya que permitirían unir votante y voto.
2. **Bitácora de la aplicación** encadenada con hashes (ADR-004).

## Consecuencia crítica: el secreto del voto en PostgreSQL

PostgreSQL usa MVCC: cada fila guarda en `xmin` el **ID de la transacción** que la creó, y
cualquier usuario con `SELECT` puede consultarlo (`SELECT xmin, * FROM urna.voto`). El ID crece en
cada transacción, así que **revela el orden de inserción de los votos**. Además, si el voto se
inserta en la misma transacción que marca `ya_voto`, **las dos filas comparten el mismo `xmin`**, lo
que vincula directamente al votante con su voto. La posición física (`ctid`) y el WAL también
conservan el orden.

**Mitigación: mezcla de la urna.** En cada checkpoint (cada N votos), una función
`SECURITY DEFINER urna.mezclar()` hace lo siguiente en **una sola transacción**:
1. Copia los votos a una tabla temporal.
2. Ejecuta `TRUNCATE` sobre la urna, lo que crea un archivo físico nuevo.
3. Reinserta los votos **en orden aleatorio**.
4. Verifica que el conteo y la raíz de Merkle sean idénticos a los de antes de la mezcla. Si no lo son, revierte todo.

Después de la mezcla, todos los votos tienen el mismo `xmin` y un orden físico aleatorio. Esto
cumple el modelo de anonimato k = N de ADR-004. La mezcla queda registrada en la bitácora y se
puede verificar, porque el conteo y la raíz se conservan.

**Riesgo residual (se documenta en el Cap. IV):**
- Los últimos < N votos, antes de la siguiente mezcla, siguen ordenados.
- Los segmentos WAL anteriores conservan el orden hasta que se reciclan. Por eso se configura
  `archive_mode = off` y se aplica `wal_level = minimal`.
- Un superusuario con acceso al disco durante la jornada podría reconstruir el orden.

Contramedidas: custodia de la contraseña del superusuario y presencia de delegados. Al terminar
el proceso, se borra de forma segura el directorio de datos de la instancia, después de exportar.

## Consecuencias

- (+) Cumple el requisito de la tutora con un SGBD empresarial, libre y nativo en Debian.
- (+) Permite mínimo privilegio real (por columna y por esquema) y auditoría pgaudit, que dan
  buen material para el Cap. IV (Seguridad).
- (+) Las pruebas automáticas usan una instancia temporal de PostgreSQL (`initdb` en un directorio
  temporal), sin Docker.
- (−) Hay un servicio más que administrar y respaldar. El manual técnico incluye `pg_dump` y la restauración.
- (−) La mezcla de la urna añade complejidad, aunque también es un aporte técnico que se puede explicar en la defensa.
- Driver de Python: **psycopg 3**. Instalación: `sudo apt install postgresql postgresql-17-pgaudit`.
