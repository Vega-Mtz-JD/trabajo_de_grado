---
name: exportar-informe
description: Exporta el informe o el perfil (docs/informe/*.md) a Word con pandoc, citas APA 7 y el formato del Reglamento UPEA, y verifica el resultado (páginas, citas sin resolver). Usar cuando Diego pida "exportar a Word", "generar el perfil" o "/exportar-informe [perfil]".
---

# Exportar informe a Word

1. Ejecutar `docs/exportar/exportar_word.sh` (o `... perfil` para Cap. I–II). Si falta pandoc, pedirle a Diego que ejecute `! sudo apt install pandoc`.
2. Revisar los avisos de pandoc: citas `[@clave]` sin entrada en el `.bib` → listarlas.
3. Convertir a PDF para contar páginas: `soffice --headless --convert-to pdf --outdir docs/salida docs/salida/<archivo>.docx` y luego `pdfinfo`. Comparar con el reglamento: perfil 40–80 págs (Cap. I–II), final 90–150 (sin bibliografía ni anexos).
4. Informar la ruta del `.docx`, el número de páginas, las citas faltantes y los `⚠️ VERIFICAR` pendientes (`grep -rn "VERIFICAR" docs/informe`).
5. Recordar los retoques manuales en Word: carátula (anexo del reglamento), índices de figuras y tablas, declaración jurada de no plagio.
