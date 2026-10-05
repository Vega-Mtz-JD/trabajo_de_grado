# ADR-005 — PySide6 y compositor `cage` para el modo kiosco

**Estado:** Aceptada · 2026-10-05

## Contexto
La v4 proponía PyQt6, con licencia GPL v3 (o comercial), incompatible con publicar bajo Apache 2.0.
El kiosco basado solo en bloquear atajos dentro de la aplicación es fácil de evadir.

## Decisión
- **PySide6** (Qt for Python oficial, LGPL v3): misma API Qt, licencia compatible.
- Kiosco a nivel de sistema: usuario `kiosco` sin privilegios, auto-login en **`cage`**
  (compositor Wayland de una sola aplicación, en repositorios de Debian), que no ofrece escritorio,
  panel ni atajos de cambio de ventana. La app además ignora cierre y atajos, y la salida requiere
  contraseña de operador (3 intentos → bloqueo 5 min).

## Consecuencias
- (+) Licencia limpia; el votante no tiene un escritorio al que escapar.
- (−) Durante el desarrollo se ejecuta en ventana normal (bandera `--kiosco` para producción).
