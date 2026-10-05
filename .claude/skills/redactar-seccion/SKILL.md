---
name: redactar-seccion
description: Redacta o mejora una sección del informe de Proyecto de Grado (docs/informe/*.md) cumpliendo el Reglamento UPEA (Art. 48), la guía de la tutora y APA 7, usando como fuente el código, los ADR y la propuesta v5. Usar cuando Diego pida escribir, completar o corregir un apartado del informe (p. ej. "redacta 1.3.2 problema principal", "/redactar-seccion 2.5 marco tecnológico").
---

# Redactar una sección del informe

Argumento: número y/o nombre de la sección (p. ej. `1.6.1 Metodología de desarrollo`).

## Pasos
1. Leer la sección destino en `docs/informe/` (incluidos los comentarios `<!-- GUÍA ... -->`, que son las instrucciones de la tutora).
2. Leer los requisitos que aplican en `docs/normativa/guia_tutora.txt` y `docs/normativa/reglamento_proyecto_grado.txt`.
3. Reunir los hechos de `docs/propuesta_v5.md`, `docs/decisiones/`, `docs/bitacora/` y del código (`app/`, `blockchain/`). Para describir el sistema, **solo** lo que existe o está decidido.
4. Redactar en español formal académico, en tercera persona e impersonal ("se desarrolló", "el sistema permite"), con párrafos de 4 a 8 líneas y sin viñetas excesivas (la tutora espera prosa).
5. Citas en APA 7 como `[@clave]` o `@clave`. Si la fuente no está en `docs/referencias/bibliografia.bib`:
   - si se tiene la fuente verificada (URL consultada), agregar la entrada BibTeX;
   - si no, escribir `⚠️ VERIFICAR: <qué falta>`. **Nunca inventar autores, años, páginas ni DOI.**
6. Datos de la empresa no disponibles → `[EMPRESA: dato a obtener en entrevista]`.
7. Marco teórico: por cada concepto, ≥ 2 autores + "concepto propio" (plantilla `docs/plantillas/concepto.md`).
8. Conservar la numeración de títulos existente. No borrar los comentarios GUÍA hasta que la sección esté completa; después, reemplazarlos.
9. Al final, informar: qué se escribió, qué citas faltan y qué datos debe conseguir Diego.
