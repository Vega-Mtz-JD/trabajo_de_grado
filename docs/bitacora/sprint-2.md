---
tipo: sprint
sprint: 2
inicio: 2026-10-05
fin: 2026-10-05
estado: cerrado
---
# Sprint 2 — Proceso electoral completo y auditoría triple

## Objetivo del sprint
Implementar todas las fases del proceso electoral (propuesta §13.1) como servicios, con
hardware simulado, y una simulación de punta a punta que termine con la verificación
multinivel del resultado.

## Backlog del sprint
- [x] Modelo de dominio: estados, opciones, roles, comprobante VVPAT (`dominio/modelos.py`)
- [x] Llavero del equipo cifrado con Argon2id + AES-GCM; plantillas biométricas cifradas (`cripto/llavero.py`)
- [x] Lector de huella simulado (1:1, ruido, tasa de rechazo) e impresora simulada en PDF/memoria (`hardware/`)
- [x] Repositorio SQL y outbox de anclajes para Fabric (`datos/repositorio.py`, `blockchain/outbox.py`)
- [x] Configuración con custodia 3 de 5 e impresión de partes con QR (`servicios/configuracion.py`)
- [x] Empadronamiento con huella y cierre del padrón (`servicios/empadronamiento.py`)
- [x] Apertura con autodiagnóstico y zerésima firmada (`servicios/apertura.py`)
- [x] Identificación, huella 1:1 (3 intentos), excepción manual, emisión con VVPAT y checkpoints (`servicios/votacion.py`)
- [x] Cierre con cuadre y acta firmada (`servicios/cierre.py`)
- [x] Escrutinio con reconstrucción de la clave en memoria (`servicios/escrutinio.py`)
- [x] Exportación del paquete USB cifrado con manifiesto firmado (`servicios/exportacion.py`)
- [x] Verificador de auditoría triple: papel + USB + ledger (`servicios/verificacion.py`)
- [x] Usuarios con contraseñas Argon2id (`servicios/usuarios.py`)
- [x] `votoseguro demo` y `votoseguro verificar` (CLI)

## Hecho (resumen técnico)
- Cada servicio delimita sus transacciones (`with conn.transaction()`); las actas se **imprimen
  después del commit** para no producir papeles sin registro.
- Si la impresora falla tras registrar el voto, el voto queda guardado y se reimprime el VVPAT
  marcado "REIMPRESIÓN" (propuesta §13.2).
- El **compromiso del padrón** (raíz de Merkle de los CI con sal aleatoria) se ancla en la apertura
  (no en la configuración, porque el padrón aún no existe). La sal evita fuerza bruta sobre CI.
- El acta de escrutinio incluye la lista `código VVPAT → opción`, ordenada por código, para cotejar
  papeleta por papeleta sin revelar el orden de emisión ([[ADR-004-secreto-del-voto]]).
- En la simulación, los VVPAT se guardan en un solo PDF con páginas **mezcladas**, como en una urna
  física; archivos sueltos revelarían el orden de votación.
- Hallazgo durante la prueba: la demo no era reproducible (el lector usaba azar del sistema) y una
  prueba podía fallar al azar (~8 %). Se inyectó un generador con semilla.

## Pruebas
`pytest --cov=votoseguro` → **81 pruebas aprobadas, 0 fallidas, cobertura 96 %** (1340 sentencias).
`bandit -r src` → 0 hallazgos (uso de `random` en la simulación justificado y marcado).

| Archivo | Funciones de prueba | Qué agrega este sprint |
|---|---|---|
| `test_servicios.py` | 19 | Elección completa CONFORME; VVPAT sin hora ni votante; bitácora sin opción; 3 fallos de huella + excepción; doble voto; sesión reutilizada; opción inválida; falla de impresora + reimpresión; apertura sin lector; fases fuera de orden; escrutinio con 2 partes; Argon2id; **manipulación del USB** (resultado, voto eliminado, bitácora, papel distinto, huella distinta); demo reproducible |
| `test_cli.py` | 4 | `demo` y `verificar` por línea de comandos |

**Demo real** sobre la BD de desarrollo (100 votantes, RSA-3072): 95 votos, 5 abstenciones,
3 excepciones manuales, 1 doble voto rechazado, 329 entradas de bitácora, auditoría **CONFORME**
en 23 comprobaciones; tiempo total ≈ 2 s.

## Evidencias para el informe
- Salida de `votoseguro demo` (informe de auditoría) → Cap. IV §4.5 Resultados.
- `salida_demo/impresiones/`: zerésima, actas, partes de custodio, urna VVPAT → Cap. III y anexos.
- Pruebas de manipulación del USB → Cap. IV §4.3.5 Otras pruebas.
- Datos de la elección demo en pgAdmin (esquemas, bitácora, votos cifrados) → capturas Cap. III.

## Retrospectiva
- Bien: el verificador detecta todas las manipulaciones probadas, incluso con el manifiesto rehecho.
- Mejorar: el anclaje real en Fabric (Sprint 3) completará el nivel LEDGER, hoy "no evaluado".
