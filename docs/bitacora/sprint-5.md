---
tipo: sprint
sprint: 5
inicio: 2026-10-05
fin: 2026-10-05
estado: cerrado
---
# Sprint 5 — Interfaces gráficas (PySide6)

## Objetivo del sprint
Construir las interfaces de uso real del sistema (RF15): el **panel de mesa** para administrador,
operador y auditor, y el **kiosco del votante** para la cabina, sobre los servicios de los sprints 2–4.

## Backlog del sprint
- [x] Estilo de alto contraste y letras grandes; estados con color + texto (`ui/estilo.py`)
- [x] Ingreso del personal con Argon2id, bloqueo de 5 min tras 3 intentos y registro en bitácora (`ui/login.py`)
- [x] Primer uso: creación del administrador; llavero del equipo nuevo o existente (`ui/app.py`)
- [x] Panel de mesa con navegación por rol y por estado de la elección (`ui/ventana.py`)
- [x] Página Configuración: crear elección, instalar mesa, exportar/importar definición
- [x] Página Empadronamiento: datos + foto + huella, padrón, inhabilitar, resumen y cruce de padrones
- [x] Página Jornada: apertura con autodiagnóstico; identificación con **foto de registro y foto de hoy**; excepción manual; habilitar cabina; reimpresión; cierre
- [x] Página Escrutinio: partes de custodios, resultados con barras (orden de la boleta), exportación
- [x] Página Auditoría: paquetes, conteo en papel por mesa, huellas, ledger → árbol de comprobaciones y PDF
- [x] Página Usuarios (administrador)
- [x] Kiosco: espera → selección → confirmación → comprobante (7 s); teclas 1–9, Enter, Escape; no se puede cerrar sin contraseña de operador

## Decisiones y hallazgos
- Panel y kiosco son **dos ventanas del mismo proceso**: la mesa entrega al kiosco una `SesionVoto` de un
  solo uso mediante señales Qt. Con dos monitores, el kiosco se ubica en el segundo.
- `jsonb` de PostgreSQL reordena las claves: los resultados se muestran en el **orden de la boleta**.
- Las páginas van dentro de áreas desplazables para pantallas de laptop (1366×768).
- Pruebas sin pantalla (`QT_QPA_PLATFORM=offscreen`): los diálogos modales se sustituyen en las pruebas;
  un diálogo estático no sustituido (`QMessageBox.warning`) colgó una prueba → se sustituyen todos.
- Pendiente para el Sprint 6: el compositor `cage` muestra una sola ventana; con dos monitores (mesa + cabina)
  hay que definir la configuración de salida (ver [[ADR-005-interfaz-kiosco]]).

## Mejoras solicitadas por Diego (revisión del sprint)
- [x] **Sin cierre con la "X"**: la ventana ignora la "X" y Alt+F4; se sale con el botón **Salir**, que pide
  contraseña (bloqueo tras 3 intentos) y registra `SALIDA_SISTEMA` en la bitácora. Según el escritorio, la "X"
  puede seguir dibujada, pero no cierra; en modo kiosco (`--kiosco`, `cage`) no hay decoraciones.
- [x] **Confirmación por teclado** en la cabina: «Presione ENTER para confirmar · ESC o 0 para corregir», también
  en los botones; la tecla **0** corrige.
- [x] **Estilo minimalista**: fondo claro, un solo color de acento, tarjetas blancas, menú lateral claro con
  etiquetas cortas, estados como etiquetas de tono suave; kiosco blanco con tarjetas grandes.

## Pruebas
`pytest` → **113 aprobadas** con la red apagada (más 3 de Fabric real que pasan con la red encendida; 8 de interfaz), cobertura **92 %**; `bandit` 0 hallazgos.
La prueba `test_eleccion_completa_desde_la_interfaz` recorre con clics toda la elección: configuración,
3 empadronados con foto, apertura, voto con ratón, huella fallida + excepción + voto con teclado (con
corrección), doble voto rechazado, cierre, escrutinio con 3 partes, exportación y auditoría CONFORME.

## Evidencias para el informe
Capturas generadas automáticamente en `docs/adjuntos/ui/` (`VOTOSEGURO_CAPTURAS=… pytest tests/test_ui.py`):
configuración, empadronamiento, apertura, identificación, kiosco (selección, confirmación, comprobante),
escrutinio y auditoría → Cap. III §3.2.3 y Manual de usuario.

## Retrospectiva
- Bien: las pruebas de interfaz recorren el flujo real y generan las capturas del informe.
- Mejorar: probar con usuarios reales (SUS) en el Sprint 7; manual de usuario con estas capturas.
