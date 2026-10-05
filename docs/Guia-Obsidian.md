# Guía rápida: Obsidian en este proyecto

## 1. Abrir el vault (una sola vez)

1. Abre Obsidian. Abajo a la izquierda, haz clic en el ícono del vault → **Administrar bóvedas** (*Manage vaults*).
2. Elige **Abrir carpeta como bóveda** (*Open folder as vault*) y selecciona
   `/home/diego/Proyectos/trabajo_de_grado/docs`.
3. Abre la nota [[00-Inicio]] y fíjala con clic derecho → *Bookmark*. Es tu panel principal.

> El vault es la carpeta `docs/` del repositorio, así que todo lo que escribes queda versionado con git
> junto al código.

## 2. Lo básico que vas a usar

| Acción | Cómo |
|---|---|
| Enlazar una nota | `[[nombre-de-nota]]`. Por ejemplo `[[ADR-008-postgresql]]` |
| Buscar o abrir una nota | `Ctrl + O` |
| Paleta de comandos | `Ctrl + P` |
| Insertar una plantilla | `Ctrl + P` → "Plantillas: insertar plantilla" → `sprint`, `reunion-tutor`, `concepto`, `antecedente` |
| Alternar edición y vista | `Ctrl + E` |
| Ver quién enlaza esta nota | Panel derecho → *Backlinks* |
| Esquema del capítulo | Panel derecho → *Outline* (*Esquema*) |
| Pegar una captura | `Ctrl + V`; se guarda sola en `adjuntos/` |
| Citar bibliografía | Escribe `[@churata2020]`; la cita APA se genera al exportar a Word |

Los comentarios `<!-- GUÍA: ... -->` en `informe/` son las instrucciones de tu tutora. No se ven en
la vista de lectura ni salen en el Word.

## 3. Plugins de la comunidad recomendados

*Configuración → Complementos de la comunidad → Activar → Explorar*:

| Plugin | Para qué |
|---|---|
| **Obsidian Git** | Hace commit y respaldo automático del vault cada X minutos |
| **Zotero Integration** | Inserta citas desde Zotero (opcional, ver §5) |
| **Excalidraw** | Bocetos rápidos: árbol de problemas, diagrama de contexto, mockups |
| **Dataview** | Tablas automáticas, por ejemplo la lista de todos los antecedentes por año |
| **Better Word Count** | Cuenta palabras por sección (te ayuda a llegar a las 40–80 o 90–150 páginas) |

Los diagramas Mermaid funcionan sin ningún plugin (bloque ```` ```mermaid ````). Para los DFD y Bizagi,
exporta una imagen a `adjuntos/` y enlázala con `![[imagen.png]]`.

## 4. Flujo de trabajo (70 % sistema · 30 % informe)

1. **Durante el sprint:** programas con Claude. Las decisiones importantes van a un ADR en `decisiones/`.
2. **Al cerrar el sprint:** en Claude Code escribe `/cerrar-sprint N`. Se genera `bitacora/sprint-N.md`
   y un apartado del Cap. III.
3. **Después de cada reunión con la tutora:** crea una nota con la plantilla `reunion-tutor` en `bitacora/`
   y marca las observaciones como tareas `- [ ]`.
4. **Para redactar:** `/redactar-seccion 1.3.2` en Claude Code. Luego revisas y ajustas en Obsidian.
5. **Antes de entregarle algo a la tutora:** pide "revisa el capítulo I con el agente revisor-tg".
6. **Para generar el Word:** `/exportar-informe perfil` o, desde la terminal,
   `docs/exportar/exportar_word.sh perfil`.

## 5. Bibliografía con Zotero (recomendado)

1. Instala Zotero 7 (zotero.org, versión para Linux) y el complemento **Better BibTeX**.
2. Crea la colección "Voto Seguro" y guarda ahí cada fuente con el conector del navegador.
3. En Zotero: clic derecho en la colección → *Exportar colección* → formato **Better BibLaTeX** →
   marca **Mantener actualizado** (*Keep updated*) → guarda en `docs/referencias/bibliografia.bib`.
4. Desde entonces, cada fuente nueva que guardes aparece sola en el `.bib` y puedes citarla con `[@clave]`.

Mientras no instales Zotero, Claude agrega las entradas al `.bib` manualmente.

## 6. Exportar a Word

Se necesita pandoc una sola vez: `sudo apt install pandoc`.
El script `exportar/exportar_word.sh`:
- une los capítulos de `informe/` en orden;
- aplica `exportar/plantilla_upea.docx` (Carta, Arial 11, interlineado 2, márgenes del reglamento,
  número de página arriba a la derecha, cada capítulo en hoja nueva);
- convierte `[@clave]` a citas APA 7 y arma la lista de referencias.

La carátula, la declaración jurada y los índices de figuras y tablas se terminan en Word, porque
son formatos fijos del anexo del reglamento.
