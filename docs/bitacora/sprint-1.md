---
tipo: sprint
sprint: 1
inicio: 2026-10-05
fin: 2026-10-05
estado: cerrado
---
# Sprint 1 — Núcleo criptográfico, base de datos y bitácora

## Objetivo del sprint
Construir y probar los componentes de seguridad de los que depende todo el sistema: primitivas
criptográficas, base de datos PostgreSQL con mínimo privilegio y bitácora de auditoría encadenada.

## Backlog del sprint
- [x] Hash SHA3-256 y serialización canónica (`cripto/hashing.py`)
- [x] Árbol de Merkle independiente del orden, con prefijos de dominio (`cripto/merkle.py`)
- [x] Shamir sobre GF(2⁸): dividir, combinar, formato imprimible con verificación (`cripto/shamir.py`)
- [x] Cifrado híbrido de votos AES-256-GCM + RSA-OAEP, longitud fija y custodia de clave 3 de 5 (`cripto/cifrado_voto.py`)
- [x] Firmas RSA-PSS y claves privadas protegidas con frase de paso (`cripto/firmas.py`)
- [x] Roles PostgreSQL y esquema con 5 esquemas, triggers de solo inserción y máquina de estados (`datos/roles.sql`, `datos/esquema.sql`)
- [x] Emisión atómica del voto `urna.emitir_voto()` y mezcla de urna `urna.mezclar()` (`datos/urna.py`)
- [x] Bitácora encadenada con verificación y ancla externa (`auditoria/bitacora.py`)
- [x] Instancia PostgreSQL temporal con pgaudit para pruebas (`tests/conftest.py`)
- [x] Script de instalación de la BD de desarrollo (`scripts/instalar_bd_desarrollo.sh`) y CLI mínima

## Hecho (resumen técnico)
- La BD pasó de SQLite a **PostgreSQL 17** por exigencia de la tutora → [[ADR-008-postgresql]].
- **Hallazgo de seguridad:** la columna interna `xmin` de PostgreSQL revela el orden de inserción y
  une votante y voto (comparten transacción). Se demostró con una prueba y se corrigió con la
  **mezcla de urna** (TRUNCATE + reinserción aleatoria verificada) → [[ADR-008-postgresql]], [[ADR-004-secreto-del-voto]].
- **Cambio de diseño:** `vs_app` ya no tiene `INSERT` en la urna ni `UPDATE` de `ya_voto`; solo puede
  votar mediante la función `SECURITY DEFINER` `urna.emitir_voto()` (mínimo privilegio más estricto
  que el de la propuesta original).
- La bitácora encadenada no detecta por sí sola el borrado de las *últimas* entradas; se resolvió
  exigiendo el hash anclado externamente (acta/ledger).
- Cifrado y custodia según [[ADR-003-cifrado-umbral]].

## Pruebas
`pytest --cov=votoseguro` → **61 pruebas aprobadas, 0 fallidas, cobertura 95 %** (344 sentencias).

| Archivo | Pruebas | Qué verifica |
|---|---|---|
| `test_cripto.py` | 26 | Vector NIST SHA3, Merkle (orden, alteración, duplicados), Shamir (todas las combinaciones 3 de 5, k-1 no revela), votos (longitud fija, AAD, alteración), custodia, firmas |
| `test_bd.py` | 21 | Emisión atómica, doble voto, estados, padrón cerrado, privilegios de `vs_app`, triggers frente al superusuario, auditor sin plantillas, **vulnerabilidad `xmin` y mezcla**, votos reales cifrados, pgaudit sin parámetros |
| `test_bitacora.py` | 11 | Cadena íntegra, alteración/borrado por superusuario, ancla externa, rechazo en BD, secreto del voto |
| `test_cli.py` | 3 | Verificación de bitácora por línea de comandos |

Análisis estático `bandit -r src`: **0 hallazgos**.
Validación de las pruebas: se introdujeron fallas a propósito (trigger desactivado, mezcla sin
reordenar) y las pruebas las detectaron.

## Evidencias para el informe
- Tabla de pruebas anterior → Cap. IV §4.3.1 (caja blanca).
- Prueba `test_sin_mezcla_xmin_revela_orden_y_vincula_votante` → Cap. IV §4.2 Seguridad (riesgo y mitigación).
- Pendiente: diagrama del esquema de BD (DBeaver → ER) en `adjuntos/`.

## Retrospectiva
- Bien: las pruebas con una instancia real de PostgreSQL detectaron un riesgo de privacidad que no
  aparecía en el diseño original.
- Mejorar: falta definir [EMPRESA] para los requerimientos del Sprint 2; la tutora debe aprobar ADR-008.
