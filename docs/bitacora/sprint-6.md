---
tipo: sprint
sprint: 6
inicio: 2026-10-06
fin: 2026-10-06
estado: parcial (hardware real pendiente de compra)
---
# Sprint 6 — Producción sin hardware: migraciones, kiosco, endurecimiento, respaldos y manuales

## Objetivo del sprint
Preparar todo lo que no depende del lector ZKTeco ni de la impresora (aún no comprados): evolución de la
base de datos sin perder datos, modo kiosco de producción, endurecimiento sin red, respaldos y manuales.

## Backlog del sprint
- [x] Cabina al frente al habilitarla y devolución de la pantalla al panel (observación de Diego)
- [x] Migraciones versionadas del esquema con línea base, hash y rol `vs_admin_bd` ([[ADR-011-migraciones]])
- [x] `votoseguro bd estado|migrar`; script de instalación basado en migraciones (sin borrar datos)
- [x] Producción con dos monitores: sway con seat de la cabina confinado ([[ADR-012-pantallas-produccion]])
- [x] `configurar_kiosco.sh`: usuario kiosco, inicio automático, sway, Fabric y puente como servicios systemd
- [x] `hardening_offline.sh`: PostgreSQL solo por socket, pg_hba/pg_ident, sysctl, auditd, nftables, sin Wi-Fi/Bluetooth/SSH
- [x] `respaldo_bd.sh`: respaldo cifrado (gpg AES-256) y restauración de prueba
- [x] Manual de usuario y manual técnico (Anexos A y B) con capturas
- [ ] Drivers reales: ZKTeco (ctypes + libzkfp), impresora ESC/POS, cámara web → cuando llegue el hardware

## Hallazgos (problemas encontrados y corregidos)
1. **La cabina aparecía detrás o minimizada** con un solo monitor: en Wayland una aplicación solo puede
   activar una ventana como respuesta a una acción del usuario. Ahora se activa en el clic de «Habilitar la
   cabina» y, al terminar el votante, se minimiza y el panel vuelve al frente. *Pendiente: confirmación de
   Diego en su escritorio.*
2. **`flush ruleset` en nftables habría borrado las reglas de Docker** (red interna de Fabric): se reemplaza
   solo la tabla propia.
3. **Restaurar con `--no-owner` rompía la votación** (las funciones `SECURITY DEFINER` dejaban de pertenecer a
   `vs_propietario`): se restaura conservando dueños; verificado con una demo CONFORME en la BD restaurada.
4. **Secuencias del chaincode innecesarias:** Go incrusta el commit de git en el binario, así que cada commit
   cambiaba su hash. Se compila con `-buildvcs=false` (binario reproducible).
5. **`cage` no sirve para dos monitores** → sway con configuración cerrada (ADR-012).
6. Al migrar, el rol técnico no podía leer `meta.migracion` fuera de la transacción → permiso solo de lectura.

## Pruebas
`pytest` → **125 aprobadas** + 3 de Fabric real (aprobadas con la red encendida); cobertura **92 %**; `bandit` 0.
Nuevas: 7 de migraciones (BD nueva, nueva migración, modificada, fallida sin efectos, numeración, línea base,
rol técnico sin herencia), 4 de scripts en simulación, 1 de comportamiento de la cabina.
Verificaciones manuales: migración de una BD anterior con votos (sin pérdida de datos) y respaldo/restauración.

## Evidencias para el informe
- Anexos A (Manual de usuario) y B (Manual técnico) → ya redactados en `informe/06-anexos.md`.
- Salidas de `hardening_offline.sh` y `configurar_kiosco.sh` en simulación → Cap. IV §4.2 Seguridad.

## Retrospectiva
- Bien: probar los procedimientos de producción (migrar, restaurar) destapó dos fallas graves antes de usarlos.
- Pendiente: hardware real y validación de ADR-012 en el equipo de producción.
