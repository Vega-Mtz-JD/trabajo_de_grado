---
tipo: revision
fecha: 2026-10-06
revisor: agente revisor-tg (simula a la tutora metodológica / tribunal)
documento: "[[bitacora/perfil-v1|Perfil v1]] — Cap. I y II"
---
# Revisión del perfil v1 (agente revisor-tg)

> Todas las claves de cita `[@…]` existen en la bibliografía. Marque cada punto al resolverlo.
> 🟦 = lo puede corregir Claude ya · 🟨 = necesita datos de [EMPRESA] o de Diego

## Críticas (riesgo de devolución)

- [ ] **C1** 🟦 Falta el **cronograma de actividades** (Art. 29.a). Agregarlo (tabla o Gantt) en 1.6 y explicar la duración del ciclo de vida.
- [ ] **C2** 🟨 *(Parcial 07/10: E-P-S y DFD nivel 0 y 1 hechos — Figuras 1.1 a 1.3; nota visible quitada; P5 marcado como transversal. Falta validarlos con [EMPRESA].)* Falta el **DFD** de la situación actual (nivel 0 y 1). Quitar la nota visible «debe validarse con la institución» (01:60). Alinear los procesos de 1.3.1 con los 5 problemas: el problema 5 (trazabilidad) no tiene proceso.
- [ ] **C3** 🟨 El problema se afirma **sin datos**: votantes, duración del conteo, incidentes e impugnaciones de [EMPRESA]. Quitar «por lo general» (02:124) o citarlo.
- [ ] **C4** 🟦 **"Registro distribuido"** con un solo nodo es inexacto. Decir «red permisionada Hyperledger Fabric (configuración mononodo)» y precisar en los límites que no garantiza inmutabilidad frente a quien controla el equipo (se apoya en el anclaje en papel).
- [ ] **C5** 🟦 **Afirmaciones absolutas**: «nadie puede conocerlos», «impedir», «sin errores», «elimina la superficie de ataque», «se garantiza». Reformular con matices: ningún custodio individual, reducir o detectar, se busca preservar.
- [ ] **C6** 🟦/🟨 **Shamir con una sola fuente**: agregar una segunda, verificada (p. ej. Menezes et al., *Handbook of Applied Cryptography*, cap. 12). Fortalecer «operación sin conexión» y «escrutinio» con fuentes conceptuales.
- [ ] **C7** 🟦/🟨 *(Parcial 07/10: 44 páginas con las Figuras 1.1–1.5 y los Anexos A y B — árboles de problemas y objetivos. Falta cronograma y presupuesto.)* **Extensión**: 37 páginas exportadas, el mínimo es 40. Se completa con DFD, árboles de problemas y objetivos, cronograma, presupuesto, antecedentes más detallados, marco contextual más amplio y conceptos faltantes.

**Datos de [EMPRESA] que bloquean requisitos:** nombre, misión, visión y organigrama; carta de aceptación (Arts. 46–47); qué se vota, frecuencia y número de votantes; flujo real de la jornada; duración del conteo e incidentes; reglamento electoral interno (¿interviene el OEP o el SIFDE? Ley 356 si es cooperativa); equipo disponible; costo actual por proceso; cargos de los usuarios; responsable que hará de *Product Owner*.

## Importantes

- [ ] **I1** 🟦 **Tiempos verbales**: el perfil propone. Usar futuro («se desarrollará», «se evaluará») o declarar el avance con evidencia.
- [ ] **I2** 🟦 **Contradicción económica**: el VVPAT también imprime papel. Justificar el ahorro en horas de conteo e impugnaciones, no en papeletas.
- [ ] **I3** 🟦 **«Software libre»**: el SDK de ZKTeco es propietario. Precisarlo y no afirmar «amplia disponibilidad» sin cotización.
- [ ] **I4** 🟦 **Presupuesto incoherente**: falta la cámara web en la tabla; la propuesta dice 250–400 y 255–425 USD; el texto remite a un «Cap. IV» que el perfil no tiene. Incluir la tabla de costos como anexo del perfil.
- [ ] **I5** 🟦 **Objetivos medibles**: agregar criterios (simulacro de N votantes CONFORME, ≤ 2 min por votante, SUS ≥ 68) y el título completo en el objetivo general.
- [ ] **I6** 🟦 Alinear la evaluación (ISO 25010, COCOMO II, SUS) con los objetivos e igualar el «secreto del voto» entre 1.3.2 y 1.3.4.
- [ ] **I7** 🟦 **Antecedentes**: orden cronológico (Churata 2020 antes que Fernández 2021); describir metodología, tecnologías, resultados y limitaciones de cada uno; buscar un tercer nacional y un local electoral (Apaza no es de votación).
- [ ] **I8** 🟦 **Metodología**: agregar el **método científico** y el **método de ingeniería**; ajustar los roles de SCRUM a un solo desarrollador; duración de los sprints; umbrales de ISO 25010; alinear las pruebas de estrés y accesibilidad con la propuesta; población y muestra (≥ 10 para SUS).
- [ ] **I9** 🟦 **Límites**: volumen (hasta 500 votantes, pruebas con 100), excepción manual, hardware simulado hasta la compra (FAR/FRR y tiempos reales después), razones de cada límite; actualizar la propuesta v5 §7 (varias mesas, ADR-009); diagrama de contexto.
- [ ] **I10** 🟦 **Conceptos faltantes**: bitácora encadenada, cifrado híbrido, cifrado de umbral, zerésima, kiosco, SGBD/ACID, usabilidad y accesibilidad, mezcla de la urna. Corregir «huella» del hash (usar «resumen») y la frase «la clave pública cifra los votos» (el esquema es híbrido).
- [ ] **I11** 🟦/🟨 **Marco legal con artículos**: CPE Art. 26 (sufragio), Arts. 21 y 130 (privacidad, ⚠️ verificar); Ley 026 Art. 43.II; DS 1793 Art. 34; Ley 018 (artículos); Ley 1066 en la bibliografía; fila de protección de datos y consentimiento informado.
- [ ] **I12** 🟦 **Fuentes mal atribuidas**: Go citado a la documentación de Fabric (usar la documentación de Go); pgaudit citado a PostgreSQL (usar la fuente de pgaudit); accesibilidad atribuida a Sommerville (verificar o usar WCAG/ISO); segunda fuente para pruebas y COCOMO II; herramientas de 1.8 que faltan en 2.5.
- [ ] **I13** 🟦 **«Fuentes independientes»**: el USB y el ledger salen del mismo equipo; decir «complementarias» y que prevalece el papel.
- [ ] **I14** 🟦 **Marco metodológico**: relacionar los sprints 0–7 con los eventos de SCRUM.

## Menores

- [ ] **M1** 🟦 Citas narrativas en APA: «Laudon y Laudon (2020) definen…» con `@clave`; «et al.» desde 3 autores; no repetir el año.
- [ ] **M2** 🟦 Bibliografía: «s. f.» o el año correcto en las fuentes web; título de la ONPE; mayúsculas del título de Churata.
- [ ] **M3** 🟦 Terminología: «urna» (no «ánfora»); auditoría triple = verificación multinivel; definir outbox, checkpoint, chaincode y zerésima; completar las siglas.
- [ ] **M4** 🟦 Suavizar «interfaz accesible para personas de todas las edades» (se evaluará con SUS).
- [ ] **M5** 🟦 Problema principal: describir primero el síntoma y luego la causa (hoy contiene la solución).
- [ ] **M6** 🟦 Diferenciar los problemas secundarios 3 y 4.
- [ ] **M7** 🟦 Justificación científica breve (opcional).
- [ ] **M8** 🟦 Herramientas: hardware, Bizagi o PlantUML; Go 1.26 en la propuesta §25.
- [ ] **M9** 🟨 Confirmar con la tutora el nombre del capítulo («Marco preliminar» o «Marco referencial») y el título del trabajo (≤ 30 palabras).
- [ ] **M10** 🟨 Reescribir con palabras propias (similitud ≤ 20 %).
- [ ] **M11** 🟨 Declaración jurada de vigencia y autoría (Art. 14) como anexo.
- [ ] **M12** 🟦 Marco contextual: Brasil, India, TED Chuquisaca (si se verifica), OEP.
- [ ] **M13** 🟦 Que ningún «⚠️ VERIFICAR» quede visible fuera de un comentario (02:182).
