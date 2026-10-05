---
name: cerrar-sprint
description: Cierra un sprint SCRUM del proyecto - ejecuta pruebas y cobertura, resume lo implementado, escribe la nota del sprint en el vault de Obsidian (docs/bitacora/sprint-N.md) y deja apuntes para el Cap. III del informe. Usar cuando Diego diga "cerrar sprint", "terminamos el sprint N" o "/cerrar-sprint N".
---

# Cerrar sprint

Argumento: número de sprint.

1. Ejecutar `cd app && . .venv/bin/activate && pytest --cov=votoseguro --cov-report=term` y, si existe código Go, `go test ./...` en `blockchain/chaincode/acta` y `blockchain/bridge`. Guardar las cifras reales (pruebas, fallos, cobertura). **No maquillar resultados**: si algo falla, reportarlo.
2. Revisar `git log` y `git diff --stat` desde el cierre anterior para listar lo implementado.
3. Crear o actualizar `docs/bitacora/sprint-N.md` con la plantilla `docs/plantillas/sprint.md`: objetivo, backlog (marcando lo cumplido), resumen técnico con enlaces `[[ADR-...]]`, pruebas, evidencias y retrospectiva breve.
4. Agregar en `docs/informe/03-marco-aplicativo.md`, dentro de §3.2.3 Implementación, un subapartado "Sprint N" con 1–2 párrafos de prosa académica y una tabla del backlog. Dejar indicaciones `<!-- CAPTURA: ... -->` donde convenga una imagen.
5. Actualizar el enlace del sprint en `docs/00-Inicio.md` (sección Bitácora).
6. Proponer el mensaje de commit (sin hacer commit salvo que Diego lo pida).
7. Si en el sprint se tomó una decisión de diseño nueva, crear el ADR correspondiente.
