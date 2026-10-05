# ADR-004 — Diseño para el secreto del voto

**Estado:** Aceptada · 2026-10-05

## Contexto
En la v4, `votantes.timestamp_voto` y `votos.timestamp` permitían unir votante y voto. Registrar
cada voto como transacción individual en Fabric produce el mismo efecto con la hora del bloque.

## Decisión
1. Tabla `urna.voto` sin columnas de tiempo, PK aleatoria de 128 bits; el orden físico y `xmin`
   de PostgreSQL se borran con la **mezcla de urna** en cada checkpoint (ver ADR-008).
2. `votante` solo guarda `ya_voto` (booleano), sin hora.
3. La bitácora registra "voto emitido n.º k" sin identificador ni hash del voto.
4. A Fabric solo se envían **checkpoints cada N votos** (N ≥ 10, configurable) con conteo y raíz
   de Merkle de los hashes de votos ordenados lexicográficamente.
5. VVPAT sin hora ni datos del votante; el votante lo deposita en la urna.

## Consecuencias
- (+) No existe columna ni orden que vincule votante y voto.
- (−) Entre dos checkpoints consecutivos, un observador con acceso a bitácora + BD puede acotar
  el voto de un votante a un lote de N → anonimato k = N. Se documenta como riesgo residual;
  N es configurable según el tamaño del padrón.
- (−) El cotejo papel-digital se hace por código de voto, no por orden.
