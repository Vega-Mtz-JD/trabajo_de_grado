---
tipo: requerimientos
fuente: Diego (conversaciones de diseño)
actualizado: 2026-10-05
---
# Visión del sistema y requerimientos (según Diego)

> Nota viva: aquí se registra **cómo debe funcionar el sistema** según lo definido por el
> postulante. Alimenta el Cap. III §3.2.1 (Análisis de requerimientos) y las historias de
> usuario del backlog. Cada decisión técnica derivada tiene su ADR.

## Las tres etapas de uso

1. **Empadronamiento**: se registra a todas las personas que votarán con sus **datos personales,
   una foto y su huella**, en el **mismo equipo y sistema** de la urna (no se importan datos
   externos, para evitar datos corruptos o intentos de ataque).
2. **Votación**: el votante se identifica (CI + huella) y se le toma una **foto en la mesa de
   identificación** como evidencia de que asistió y de su estado en ese momento; luego vota en la
   cabina (sin cámara) y deposita su comprobante VVPAT.
3. **Conteo, auditoría y verificación**: escrutinio **en cada mesa** con sus custodios/jurados,
   auditoría triple y comparación con el padrón (quiénes votaron y quiénes **no votaron**).

## Varias urnas (mesas)

- El sistema debe poder **exportarse o duplicarse** para operar varias urnas en la misma elección.
- **Padrón dividido:** cada persona pertenece a una sola mesa (ninguna urna tiene red).
- Se detectan empadronamientos duplicados entre mesas antes de la apertura (cruce de padrones)
  y votos duplicados entre mesas al consolidar.
- Cada mesa escruta sus votos y emite su acta; luego se **consolidan** las actas de todas las mesas.

## Requerimientos funcionales (RF)

| Id | Requerimiento | Estado |
|---|---|---|
| RF01 | Definir una elección (nombre, opciones, mesas) y exportar su definición para otras urnas | ✔ Sprint 3 |
| RF02 | Importar la definición en cada urna y generar su propia clave con custodios de esa mesa | ✔ Sprint 3 |
| RF03 | Empadronar con CI, nombres, apellidos, **foto** y **huella** | ✔ Sprint 2–3 (simulados) |
| RF04 | Cruzar padrones de todas las mesas y detectar duplicados antes de abrir | ✔ Sprint 3 |
| RF05 | Apertura con zerésima firmada | ✔ Sprint 2 |
| RF06 | Identificación con CI + huella 1:1 (3 intentos) y excepción manual justificada | ✔ Sprint 2 |
| RF07 | **Foto de presencia** al identificarse (nunca en la cabina, nunca vinculada al voto) | ✔ Sprint 3 |
| RF08 | Voto cifrado, VVPAT sin hora ni identidad, rechazo de doble voto | ✔ Sprint 2 |
| RF09 | Cierre con acta firmada y **lista de quienes no votaron** | ✔ Sprint 3 |
| RF10 | Escrutinio en cada mesa con 3 de 5 custodios de esa mesa | ✔ Sprint 3 |
| RF11 | Exportación del paquete de auditoría cifrado por mesa | ✔ Sprint 2 |
| RF12 | Auditoría triple por mesa (papel + USB + ledger) | ✔ papel/USB · ledger Sprint 4 |
| RF13 | **Consolidación** de todas las mesas: verificación de cada paquete y cómputo total | ✔ Sprint 3 |
| RF14 | Anclaje de hitos en Hyperledger Fabric | Sprint 4 |
| RF15 | Interfaces gráficas: kiosco del votante, panel del operador, panel del auditor | Sprint 5 |

## Requerimientos no funcionales (RNF)

| Id | Requerimiento |
|---|---|
| RNF01 | Operación 100 % offline (sin red, Wi-Fi ni Bluetooth) |
| RNF02 | Secreto del voto: ningún dato vincula votante y voto (ADR-004, ADR-008) |
| RNF03 | Datos personales (fotos, huellas) cifrados; nunca en el ledger |
| RNF04 | BD robusta: PostgreSQL 17 (exigencia de la tutora) |
| RNF05 | Tiempo por votante ≤ 2 minutos |
| RNF06 | Todo evento auditable: quién, qué y cuándo (bitácora + pgaudit) |

Relacionado: [[propuesta_v5]], [[ADR-009-varias-mesas]], [[bitacora/sprint-2|Sprint 2]].
