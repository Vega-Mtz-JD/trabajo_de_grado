---
tipo: entregable
fecha: 2026-10-06
estado: borrador v1
---
# Perfil de Proyecto de Grado — borrador v1 (Cap. I y II)

Exportar: `docs/exportar/exportar_word.sh perfil` → `docs/salida/perfil.docx` (37 págs. con la estructura
del Art. 48; el reglamento exige 40–80 en el perfil: se completará con los datos de la institución,
el DFD, el organigrama y las figuras).

## Qué está hecho
- [[informe/01-marco-preliminar|Cap. I]] completo según el Art. 48 y la guía de la tutora: introducción
  en 4 párrafos, antecedentes (3 internacionales, 2 nacionales, 1 local, **todos 2020+ y verificados**),
  problema con esquema E-P-S, 5 problemas secundarios causa→efecto, objetivo general y 5 específicos
  (uno por problema), justificaciones, metodología, técnicas de recolección, herramientas, límites,
  alcances por módulos y aportes.
- [[informe/02-marco-teorico|Cap. II]]: 18 conceptos con **≥ 2 fuentes** cada uno (salvo Shamir) + concepto
  propio; marcos contextual, metodológico (SCRUM, UML), tecnológico (Python, PySide6, PostgreSQL, Docker,
  pruebas, ISO 27000, ciclo de vida, ISO 25010, COCOMO II) y legal.
- Bibliografía: 53 entradas; los DOI se verificaron en Crossref y las tesis en sus repositorios.
- Citas en APA 7 en español («y» en lugar de «&»).

## Pendiente (lo debe completar Diego)
- [ ] Datos de la institución: buscar `[EMPRESA` en los capítulos (≈ 20 marcadores): nombre, misión,
      visión, organigrama, qué se vota, cuántos votantes, costo actual, cargos de los beneficiarios.
- [ ] DFD de la situación actual (Bizagi) y diagrama de contexto propuesto (marcadores `FIGURA`).
- [ ] Antecedente nacional adicional 2020+ (opcional) y segunda fuente para Shamir (`⚠️ VERIFICAR`).
- [ ] Confirmar los artículos de la CPE sobre privacidad (`⚠️ VERIFICAR`).
- [ ] Reescribir con palabras propias (control de similitud ≤ 20 %) y revisar con la tutora.
- [ ] Carátula del anexo del reglamento, declaración jurada, índices de figuras y tablas (en Word).

## Fuentes de antecedentes verificadas
| Ámbito | Trabajo | Verificación |
|---|---|---|
| Internacional | Ipiales Chasiguano (2022), UTN Ecuador | API del repositorio DSpace |
| Internacional | Banu Stan (2023), UPM España | Metadatos Dublin Core |
| Internacional | Guadalupe Medina y Lizama Paredes (2025), UPC Perú | API del repositorio DSpace |
| Nacional | Fernández Tristán (2021), UMSA | Repositorio espejo (Universidad de Chile) |
| Nacional | Churata Sonco (2020), UPEA | PDF de la tesis |
| Local | Apaza Alberto (2020), UPEA | PDF de la tesis |
