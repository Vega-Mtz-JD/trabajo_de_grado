# ADR-007 — LevelDB como base de estado de Fabric

**Estado:** Aceptada · 2026-10-05

## Contexto
La v4 incluía CouchDB para "consultas ricas". El chaincode solo accede por clave
(`ELECCION~id`, `CHECKPOINT~id~seq`), y el historial se obtiene con `GetHistoryForKey`.

## Decisión
Usar **LevelDB** (embebida en el peer, valor por defecto de Fabric).

## Consecuencias
- (+) Un contenedor menos, menor consumo de RAM, arranque más rápido en equipos modestos.
- (−) Sin consultas JSON ricas; no se necesitan. Si en el futuro se requieren, el cambio es de
  configuración del peer.
