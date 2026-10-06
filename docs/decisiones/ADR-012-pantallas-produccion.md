# ADR-012 — Pantallas en producción: sway con dos salidas en lugar de cage

**Estado:** Propuesta (validar con el hardware real) · 2026-10-06
**Modifica:** ADR-005

## Contexto
La aplicación tiene dos ventanas: el **panel de mesa** (operador) y la **cabina** (votante). ADR-005 proponía
el compositor `cage`, pero `cage` muestra una sola aplicación maximizada: con una PC y dos monitores no
puede poner cada ventana en su pantalla, y el votante compartiría el puntero con el operador.

## Decisión
Configuraciones de producción, según el equipamiento de la mesa:

| Escenario | Compositor | Configuración |
|---|---|---|
| **A. Una PC, dos monitores** (recomendado) | **sway** (Debian) con una configuración cerrada | Panel a pantalla completa en el monitor de la mesa y cabina a pantalla completa en el monitor de la cabina; el ratón/teclado de la cabina en un **seat** propio confinado a ese monitor (`map_to_output`); sin barra, sin atajos de terminal ni de salida |
| B. Una PC, un monitor (pruebas, laptop) | escritorio normal | La cabina se maximiza al habilitarse y se minimiza al terminar el votante (Sprint 5) |
| C. Dos PCs (mesa y cabina separadas) | `cage` en la PC de la cabina | Requiere comunicación entre equipos: **fuera del alcance** del prototipo |

`scripts/configurar_kiosco.sh` genera la configuración del escenario A: usuario `kiosco` sin privilegios,
inicio automático en tty1 y `sway` con reglas por título de ventana. Los identificadores de los monitores y
de los dispositivos de entrada se completan con `swaymsg -t get_outputs` / `get_inputs` en el equipo real.

## Consecuencias
- (+) El votante no puede alcanzar el panel del operador ni salir de la cabina.
- (+) Una sola PC por mesa (menor costo).
- (−) Requiere dos juegos de ratón/teclado (o solo ratón en la cabina) y configurar los identificadores.
- Se valida en el Sprint 6–7 con el equipo de producción.
