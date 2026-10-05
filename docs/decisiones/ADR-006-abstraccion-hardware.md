# ADR-006 — Abstracción de hardware: ZKTeco y ESC/POS con simuladores

**Estado:** Aceptada · 2026-10-05

## Contexto
El hardware aún no se ha comprado. La v4 proponía FPM10A (UART, no USB) y "huella_hash" (no
viable: el matching biométrico es difuso). Las impresoras Adafruit/SparkFun también son seriales.

## Decisión
- Interfaces `LectorHuella` (`capturar`, `comparar`) e `Impresora` (`imprimir_vvpat`,
  `imprimir_acta`, `estado`).
- Implementaciones: `LectorSimulado` y `ImpresoraPDF` para desarrollo y pruebas automáticas;
  `LectorZKTeco` (ctypes sobre `libzkfp.so` del ZKFinger SDK Linux; modelos ZK9500/SLK20R) e
  `ImpresoraEscPos` (python-escpos, USB) para producción.
- Se almacena la **plantilla** biométrica cifrada en la BD y la comparación 1:1 la hace el SDK
  (`ZKFPM_DBMatch`), con umbral configurable.

## Consecuencias
- (+) Todo el sistema se desarrolla y prueba sin hardware.
- (−) Dependencia del SDK propietario de ZKTeco (binario); el resto del sistema sigue siendo libre.
- Verificar al comprar que el vendedor entrega el SDK para Linux.
