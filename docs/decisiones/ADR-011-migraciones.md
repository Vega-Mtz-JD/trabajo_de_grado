# ADR-011 — Migraciones versionadas del esquema

**Estado:** Aceptada · 2026-10-06

## Contexto
Hasta el Sprint 5, cada cambio de esquema obligaba a recrear la base de datos (`--recrear`), perdiendo
los datos de prueba. En producción eso sería inaceptable: una actualización del sistema no puede borrar
un padrón ya empadronado.

## Decisión
- Los cambios de esquema se escriben como archivos `app/src/votoseguro/datos/migraciones/NNNN_nombre.sql`,
  numerados sin huecos. El esquema anterior pasó a ser `0001_esquema_inicial.sql`.
- `votoseguro bd migrar` aplica las pendientes **en orden**, cada una en **su propia transacción** y con
  `SET LOCAL ROLE vs_propietario` (los objetos siempre pertenecen al propietario). Un error revierte esa
  migración completa.
- `meta.migracion` registra versión, nombre, momento y **SHA3-256 del archivo**. Si una migración ya
  aplicada se modifica, el migrador se detiene (`MODIFICADA`): el esquema real no coincidiría con el revisado.
- **Línea base:** una BD instalada antes de este mecanismo (con el esquema completo del Sprint 3+) se registra
  como versión 1 sin reaplicar nada. Se verificó con una BD con votos: los datos se conservan.
- **Quién migra:** `vs_admin_bd`, que tiene `vs_propietario` con `INHERIT FALSE, SET TRUE` (PostgreSQL 16+):
  puede asumir el rol de dueño para migrar, pero en uso normal **no** hereda sus privilegios (ni siquiera
  puede leer el padrón). En desarrollo, el usuario de Linux es miembro de `vs_admin_bd`.
- Un *advisory lock* impide dos migraciones simultáneas.

## Consecuencias
- (+) Actualizar el sistema ya no borra datos; los cambios de esquema quedan versionados y auditables.
- (+) Las pruebas crean la BD con el mismo migrador que producción.
- (−) Toda modificación de esquema debe escribirse como migración nueva (nunca editar una aplicada).
