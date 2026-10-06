---
tipo: sprint
sprint: 3
inicio: 2026-10-05
fin: 2026-10-05
estado: cerrado
---
# Sprint 3 — Varias urnas, foto y auditoría del padrón

## Objetivo del sprint
Incorporar los requerimientos definidos por Diego ([[requerimientos/vision-del-sistema]]):
empadronamiento con foto en la propia urna, foto de presencia en la jornada, lista de quienes no
votaron y operación con **varias urnas** (padrón dividido, escrutinio por mesa y consolidación).
Decisión de diseño: [[ADR-009-varias-mesas]]. El sprint de Fabric pasa a ser el Sprint 4.

## Backlog del sprint
- [x] Esquema: mesa + `eleccion_global` + sal del padrón + definición inmutable; foto de registro; tabla `padron.presencia`
- [x] Definición de elección exportable (`.vsd`): cifrada, firmada, con hoja de control impresa (RF01, RF02)
- [x] Instalación de mesa con clave y custodios propios (RF02, RF10)
- [x] Cámara simulada y foto de registro cifrada (RF03)
- [x] Foto de presencia al identificarse; primera identificación del día; nunca en la cabina (RF07)
- [x] Inhabilitación de votantes con motivo
- [x] Resumen de padrón por mesa (`.vsp`) y **cruce de padrones** (RF04)
- [x] Acta de cierre con ausentes y "presentes sin votar"; **lista impresa de quienes no votaron** (RF09)
- [x] Paquete USB con padrón (sin fotos ni huellas) y definición; verificador del padrón (3 comprobaciones nuevas)
- [x] **Consolidación** de mesas: misma definición, mesas completas, sin CI en dos mesas, suma (RF13)
- [x] CLI: `demo --mesas N` y `consolidar`

## Hecho (resumen técnico)
- El llavero cifra todos los datos personales sensibles con AES-256-GCM y AAD `tipo:elección:CI`: una foto
  o plantilla no se puede copiar a otro votante ni usarse como otro tipo.
- El compromiso del padrón (zerésima) usa la sal de la definición y solo los **habilitados**.
- Los anclajes de Fabric se identifican por `eleccion_global` + `mesa`.
- El auditor (rol `vs_auditor`) no puede leer fotos ni plantillas (privilegios por columna).

## Pruebas
`pytest --cov=votoseguro` → **96 pruebas aprobadas, 0 fallidas, cobertura 96 %** (1666 sentencias).
`bandit -r src` → 0 hallazgos.

| Archivo | Nuevas o cambiadas | Qué verifica |
|---|---|---|
| `test_multimesa.py` | 13 nuevas | Definición (ida y vuelta, otro equipo, frase, archivo alterado), mesa fuera de la definición, clave por mesa, foto cifrada y visible, sin cámara, presencia, ausentes, auditor sin fotos, cruce de padrones, consolidación (conforme, doble voto entre mesas, mesa faltante, paquete repetido, otra elección) |
| `test_servicios.py` | +2 | Demo de 3 mesas con duplicado detectado; padrón alterado en el USB |
| `test_cli.py` | ampliada | `demo --mesas 2` + `consolidar` (y mesa faltante) |

## Evidencias para el informe
- Salida de `votoseguro demo --mesas 3` (cruce de padrones + auditoría por mesa + consolidado) → Cap. IV §4.5.
- Lista impresa de ausentes y hoja de control de la definición → anexos.
- Diagrama de despliegue con varias urnas (pendiente) → Cap. III §3.2.2.

## Retrospectiva
- Bien: los requerimientos nuevos entraron sin romper la seguridad (secreto del voto, mínimo privilegio).
- Mejorar: la BD de desarrollo debe recrearse porque cambió el esquema; en el Sprint 4 conviene
  agregar migraciones versionadas para no perder datos en cambios futuros.
