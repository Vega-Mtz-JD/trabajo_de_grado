# CAPÍTULO I — MARCO PRELIMINAR

<!-- BORRADOR v1 (2026-10-06). Redactado a partir de la propuesta v5, los ADR y el sistema construido.
     Los datos de la institución están marcados [EMPRESA: …]: completarlos tras la entrevista.
     Reescribir con palabras propias antes de entregar (control de similitud ≤ 20 %, Art. 48). -->

## 1.1. Introducción

La votación es el mecanismo mediante el cual una organización expresa de forma colectiva sus decisiones y elige a sus autoridades. En las últimas dos décadas, distintos países y organizaciones han incorporado tecnologías de información a sus procesos electorales con el propósito de reducir los tiempos de escrutinio, disminuir los errores humanos y fortalecer la confianza en los resultados [@gibson2016]. Entre estas tecnologías, la cadena de bloques (*blockchain*) ha despertado un interés creciente, porque permite mantener registros compartidos cuya alteración posterior resulta detectable [@yaga2018; @jafar2021].

En [EMPRESA: nombre de la institución], los procesos de votación internos se realizan con papeletas físicas y conteo manual. Este procedimiento demanda tiempo y personal, está expuesto a errores de conteo y no ofrece mecanismos que permitan verificar de forma independiente que el resultado proclamado corresponde a los votos emitidos, lo que puede derivar en impugnaciones, pérdida de tiempo productivo y desconfianza entre los participantes.

Para atender esta necesidad, el presente Proyecto de Grado desarrolla un sistema de votación electrónica que opera sin conexión a ninguna red. El votante se identifica con su cédula de identidad, su huella dactilar y una fotografía; emite su voto en una cabina con interfaz accesible; y recibe un comprobante impreso que deposita en una urna física. Los votos se almacenan cifrados de forma que nadie puede conocerlos antes del escrutinio, el cual exige la participación de varios custodios. Los hitos de la elección se registran en una red Hyperledger Fabric y, al cierre, un verificador contrasta tres fuentes independientes de evidencia: el papel, el respaldo digital y el registro distribuido.

El sistema se desarrolló con la metodología ágil SCRUM y modelado UML, empleando Python con la biblioteca PySide6 para las interfaces, PostgreSQL 17 como gestor de base de datos, Hyperledger Fabric 2.5 como plataforma de cadena de bloques, y el lenguaje Go para el contrato inteligente. La calidad se evalúa con el modelo ISO/IEC 25010, la seguridad con el marco de controles ISO/IEC 27002 y el análisis de riesgos MAGERIT, y el costo con el modelo COCOMO II.

## 1.2. Antecedentes

### 1.2.1. Antecedentes institucionales

<!-- Completar con la entrevista y documentos de la institución (guía de la tutora). -->

[EMPRESA: nombre, dirección, rubro y breve reseña histórica].

- **Misión:** [EMPRESA].
- **Visión:** [EMPRESA].
- **Objetivos institucionales:** [EMPRESA].
- **Organigrama:** [EMPRESA: insertar el organigrama y resaltar el área responsable de los procesos de votación (por ejemplo, el comité electoral o la secretaría general)].
- **Procesos de votación que realiza:** [EMPRESA: qué se vota (directorio, representantes, comités), con qué frecuencia y cuántas personas participan].

### 1.2.2. Antecedentes afines al proyecto de grado

#### 1.2.2.1. Antecedentes internacionales

**Ipiales Chasiguano (2022), Universidad Técnica del Norte, Ecuador.** En el trabajo «Implementación de un sistema de votación electrónica para fortalecer el proceso de escrutinio utilizando Blockchain», el autor parte de que la incorporación de la tecnología en los procesos electorales trajo consigo vulnerabilidades y ataques que disminuyen la confianza de los electores, y propone un sistema web de votación basado en una cadena de bloques con contratos inteligentes para fortalecer el escrutinio [@ipiales2022]. Del trabajo se adopta la idea de que el registro distribuido debe respaldar el escrutinio; el presente proyecto se diferencia al operar sin red y al combinar el registro distribuido con un comprobante en papel.

**Banu Stan (2023), Universidad Politécnica de Madrid, España.** El trabajo «Diseño y desarrollo de una aplicación descentralizada para la votación electrónica a través de la tecnología Blockchain» desarrolla una aplicación descentralizada de votación sobre una cadena de bloques [@banu2023]. Su aporte para este proyecto es el análisis de las propiedades que una cadena de bloques ofrece al voto electrónico; a diferencia de una aplicación descentralizada pública, aquí se emplea una red permisionada que no requiere conexión a Internet.

**Guadalupe Medina y Lizama Paredes (2025), Universidad Peruana de Ciencias Aplicadas, Perú.** La tesis «Sistema de votación electrónica para eliminar la manipulación de información mediante el uso de tecnologías Blockchain e identificación biométrica» presenta *Boxting*, una solución basada en Internet que incorpora una cadena de bloques Hyperledger e identificación biométrica para reducir el fraude en los procesos electorales [@guadalupe2025]. Es el antecedente más cercano en cuanto a tecnologías; el presente proyecto se diferencia porque funciona de manera presencial y sin conexión, añade el comprobante en papel verificable por el votante y protege el secreto del voto con cifrado de umbral.

#### 1.2.2.2. Antecedentes nacionales

**Fernández Tristán (2021), Universidad Mayor de San Andrés.** La tesis «Sistema de votación electrónica usando tecnología Blockchain para procesos electorales» tiene como objetivo desarrollar un sistema de votación electrónica con tecnología Blockchain para mejorar la seguridad y el registro de las transacciones entre los electores y disminuir el tiempo de entrega de resultados en un proceso electoral transparente [@fernandez2021]. El presente proyecto comparte el objetivo de transparencia, pero agrega la autenticación biométrica, el comprobante en papel y la verificación multinivel.

**Churata Sonco (2020), Universidad Pública de El Alto.** La tesis «Protocolos Blockchain aplicados a un sistema de votación electrónica», con caso de estudio en la Carrera de Ingeniería de Sistemas de la UPEA, construyó un sistema web con una cadena de bloques propia implementada en Python para comprobar la seguridad que la tecnología aporta a los datos electorales [@churata2020]. Este trabajo es el antecedente directo en la carrera; el presente proyecto se diferencia en que no implementa una cadena propia, sino que emplea una plataforma permisionada estándar (Hyperledger Fabric), opera sin red, incorpora biometría, comprobante en papel y cifrado de umbral, y define un procedimiento de auditoría triple.

<!-- ⚠️ VERIFICAR: se recomienda agregar un tercer antecedente nacional de 2020 en adelante (p. ej. en el repositorio de la UMSA). -->

#### 1.2.2.3. Antecedentes locales

**Apaza Alberto (2020), Universidad Pública de El Alto.** La tesis «Modelo de certificación de contratos inteligentes aplicando la tecnología blockchain. Caso: Certificaciones CITES» aplicó contratos inteligentes sobre una cadena de bloques para la certificación de documentos [@apaza2020]. Aunque su dominio no es electoral, muestra la aplicación de contratos inteligentes en la ciudad de El Alto; el presente proyecto utiliza un contrato inteligente (*chaincode*) para validar la secuencia de los hitos electorales.

## 1.3. Planteamiento del problema

### 1.3.1. Descripción del problema

<!-- GUÍA: imprescindible el Esquema Entrada–Proceso–Salida y el DFD de la SITUACIÓN ACTUAL (Bizagi u otra herramienta).
     Insertar el DFD como figura una vez validado con la institución. -->

El proceso de votación actual de [EMPRESA] puede describirse con el siguiente esquema de entrada, proceso y salida, que debe validarse con la institución:

| Entrada | Proceso | Salida |
|---|---|---|
| Lista de habilitados (padrón en papel), papeletas impresas, cédulas de identidad de los votantes | Identificación visual del votante con su cédula; firma en la lista; entrega de la papeleta; voto en un recinto; depósito en el ánfora; conteo manual al cierre; llenado del acta | Acta de resultados en papel, papeletas contadas, lista firmada de votantes |

<!-- FIGURA: DFD de la situación actual (Bizagi). -->

A partir de este esquema se identifican los procesos que dan origen al problema: la identificación de los votantes, que depende únicamente de la verificación visual de la cédula; el conteo, que se realiza de forma manual al cierre de la jornada; la elaboración y custodia del acta, que no cuenta con mecanismos que permitan detectar alteraciones; y la verificación posterior de los resultados, para la cual no existe una fuente de evidencia independiente del acta en papel.

### 1.3.2. Problema principal

Los procesos de votación de [EMPRESA] carecen de mecanismos que permitan verificar de forma independiente la identidad de los votantes, la integridad de los votos y la exactitud de los resultados, lo que provoca demoras en el escrutinio, errores de conteo y desconfianza en los resultados proclamados.

### 1.3.3. Problemas secundarios

1. La identificación del votante se basa solo en la verificación visual de su cédula de identidad, lo que expone el proceso a la suplantación de identidad y al voto múltiple.
2. El conteo manual de las papeletas al cierre de la jornada es lento y propenso a errores humanos, lo que retrasa la entrega de resultados y origina reclamos.
3. Las actas se elaboran y custodian en papel sin ningún mecanismo de integridad, por lo que una alteración posterior no deja rastro.
4. No existe una fuente de evidencia independiente del acta con la cual contrastar los resultados, lo que dificulta resolver impugnaciones.
5. No se registra de forma sistemática quién intervino en cada etapa del proceso ni cuándo, lo que impide realizar una auditoría posterior.

### 1.3.4. Formulación del problema

¿Cómo verificar de forma independiente la identidad de los votantes, la integridad de los votos y la exactitud de los resultados en los procesos de votación de [EMPRESA], sin comprometer el secreto del voto?

## 1.4. Objetivos

### 1.4.1. Objetivo general

Desarrollar un sistema de votación electrónica sin conexión a red, con autenticación biométrica, comprobante en papel verificable y registro en la cadena de bloques Hyperledger Fabric, que permita la auditoría y verificación multinivel de los resultados de los procesos de votación de [EMPRESA].

### 1.4.2. Objetivos específicos

1. Implementar el empadronamiento con fotografía y huella dactilar, y la identificación del votante mediante comparación biométrica 1:1, para impedir la suplantación de identidad y el voto múltiple.
2. Automatizar el escrutinio mediante votos cifrados con custodia de clave compartida entre varios custodios, para entregar resultados de forma inmediata y sin errores de conteo, sin que nadie pueda conocer resultados parciales.
3. Generar actas firmadas digitalmente y ancladas en un registro distribuido Hyperledger Fabric, para que cualquier alteración posterior de los resultados sea detectable.
4. Implementar un verificador de auditoría triple que contraste el comprobante en papel, el paquete de auditoría cifrado y el registro distribuido, para resolver impugnaciones con evidencia independiente.
5. Registrar en una bitácora encadenada cada acción del proceso con su responsable y momento, para permitir una auditoría completa sin revelar el voto de ninguna persona.

## 1.5. Justificación

### 1.5.1. Justificación técnica

El sistema funciona en una computadora personal o portátil con el sistema operativo Debian 13 y software libre: Python, PostgreSQL, Docker e Hyperledger Fabric. Los periféricos requeridos —lector de huella, impresora térmica, cámara web y un segundo monitor— son de bajo costo y de amplia disponibilidad en el mercado local. Al operar sin conexión a ninguna red, el sistema elimina la superficie de ataque remota, característica que comparten los sistemas de votación presencial de referencia en la región, como el voto electrónico presencial del Perú, cuyos equipos operan aislados de cualquier red [@onpe_vep]. [EMPRESA: indicar si la institución dispone del equipo de cómputo o si acepta adquirirlo].

### 1.5.2. Justificación económica

El uso de software libre elimina el costo de licencias. La inversión en periféricos se estima entre 255 y 425 dólares estadounidenses (ver Capítulo IV), y el equipo puede reutilizarse en todos los procesos de votación posteriores. El sistema reduce el gasto recurrente en la impresión de papeletas, las horas de trabajo del personal dedicado al conteo manual y el tiempo invertido en resolver impugnaciones. [EMPRESA: cuantificar el costo actual de un proceso de votación para la comparación costo-beneficio].

### 1.5.3. Justificación social

Los beneficiarios directos son los votantes de [EMPRESA], que cuentan con un proceso más rápido y verificable, con un comprobante que pueden revisar y una interfaz accesible para personas de todas las edades; el comité electoral y el personal de mesa, que disponen de herramientas para identificar a los votantes, cerrar la mesa y obtener resultados de forma inmediata; y los auditores y delegados, que pueden verificar el resultado con evidencia independiente. Los beneficiarios indirectos son las autoridades de [EMPRESA], cuya legitimidad se fortalece con resultados verificables. [EMPRESA: detallar los cargos de los usuarios directos e indirectos].

## 1.6. Metodología

### 1.6.1. Metodología de desarrollo

Se emplea SCRUM, un marco de trabajo ágil para desarrollar productos complejos en ciclos cortos e incrementales denominados *sprints* [@schwaber2020]. Cada sprint parte de un conjunto de requerimientos priorizados del *product backlog* y concluye con un incremento funcional que se revisa antes de iniciar el siguiente. El modelado se realiza con el Lenguaje Unificado de Modelado (UML) [@booch2005; @omg2017uml], y las decisiones de arquitectura se documentan en registros de decisión (ADR).

### 1.6.2. Ciclo de vida del software

El ciclo de vida adoptado es iterativo e incremental [@sommerville2016; @pressman2020]: el sistema se construyó en sprints sucesivos, cada uno con análisis, diseño, implementación y pruebas, de modo que cada incremento añadió funcionalidad verificada sobre la base del anterior.

### 1.6.3. Métricas de calidad

La calidad del producto se evalúa con el modelo ISO/IEC 25010 [@iso25010], considerando adecuación funcional, eficiencia de desempeño, usabilidad, fiabilidad, seguridad y mantenibilidad. La usabilidad se mide además con el cuestionario SUS [@brooke1996].

### 1.6.4. Costos

El esfuerzo y el costo del software se estiman con el modelo COCOMO II [@boehm2000], a partir de las líneas de código efectivamente desarrolladas.

### 1.6.5. Seguridad

La seguridad se aborda con los controles de la norma ISO/IEC 27002 [@iso27002], el modelo de amenazas STRIDE [@shostack2014] y el análisis de riesgos de la metodología MAGERIT [@magerit2012].

### 1.6.6. Pruebas de software

Se aplican pruebas de caja blanca, pruebas de caja negra, pruebas de estrés y pruebas de accesibilidad [@myers2011], complementadas con pruebas específicas del dominio: manipulación de datos, secreto del voto y verificación contra el registro distribuido.

## 1.7. Métodos de recolección de datos

### 1.7.1. Técnicas de investigación

- **Entrevista** al comité electoral y al personal de [EMPRESA], para conocer el procedimiento actual, los problemas y los requerimientos.
- **Observación** de un proceso de votación o de un simulacro.
- **Revisión documental** de actas, padrones y reglamentos electorales de la institución.
- **Encuesta** de usabilidad (SUS) aplicada al personal y a votantes después del simulacro con el sistema.

## 1.8. Herramientas

| Ámbito | Herramienta |
|---|---|
| Lenguajes | Python 3.13 (aplicación), Go 1.26 (contrato inteligente y servicio puente), SQL |
| Interfaz gráfica | PySide6 (Qt 6) |
| Base de datos | PostgreSQL 17 con la extensión pgaudit |
| Cadena de bloques | Hyperledger Fabric 2.5 (cliente oficial Fabric Gateway) |
| Contenedores | Docker y Docker Compose |
| Criptografía | Biblioteca `cryptography` (AES-256-GCM, RSA-OAEP/PSS), SHA3-256 |
| Pruebas y análisis | pytest, pytest-qt, `go test`, Bandit |
| Sistema operativo | Debian 13 «Trixie» |
| Documentación | Obsidian, pandoc, Zotero, PlantUML, Git y GitHub |

## 1.9. Límites y alcances

### 1.9.1. Límites

- El sistema está dirigido a votaciones internas de [EMPRESA]; no reemplaza al Órgano Electoral Plurinacional ni se aplica a elecciones públicas, para las cuales la Ley 026 solo contempla el voto electrónico de los bolivianos en el exterior [@ley026].
- El sistema es un prototipo funcional y no cuenta con una certificación oficial para producción.
- Las urnas no se comunican entre sí; la consolidación de varias mesas se realiza con los paquetes de auditoría al final del proceso.
- La red Hyperledger Fabric opera en un solo nodo; ofrece evidencia de manipulación respaldada por el anclaje en papel, pero no tolerancia a fallas.
- No se contempla el voto remoto ni por Internet.
- Las firmas digitales del sistema garantizan la integridad técnica, pero no tienen valor legal, que requiere un certificado emitido por una entidad certificadora autorizada [@ds1793].

### 1.9.2. Alcances

El sistema comprende los siguientes módulos, en el orden del proceso electoral:

1. **Configuración:** definición de la elección, sus opciones (incluidos voto blanco y voto nulo) y sus mesas; generación de las claves y reparto entre custodios.
2. **Empadronamiento:** registro de votantes con datos personales, fotografía y huella dactilar; cruce de padrones entre mesas.
3. **Apertura:** autodiagnóstico de periféricos y emisión de la zerésima.
4. **Identificación y votación:** comparación biométrica, fotografía de presencia, cabina de votación accesible y comprobante impreso.
5. **Cierre y escrutinio:** acta de cierre, lista de ausentes y escrutinio con los custodios.
6. **Exportación y auditoría:** paquete cifrado, verificación triple y consolidación de mesas.
7. **Registro distribuido:** anclaje de los hitos en Hyperledger Fabric.
8. **Administración:** usuarios, bitácora, migraciones y respaldos.

<!-- FIGURA: Diagrama de contexto propuesto (guía de la tutora). -->

## 1.10. Aportes

### 1.10.1. Aporte académico

El proyecto integra en un mismo sistema conceptos que suelen estudiarse por separado —criptografía de umbral, cadenas de bloques permisionadas, biometría y auditoría electoral— y documenta las decisiones de diseño, las pruebas y los hallazgos de seguridad, de modo que puede servir de base para trabajos posteriores de la carrera.

### 1.10.2. Aporte del proyecto

Para [EMPRESA], el proyecto aporta un sistema de votación presencial que entrega resultados al cierre de la mesa, impide el voto múltiple y la suplantación, protege el secreto del voto mediante cifrado de umbral y permite verificar los resultados con tres fuentes de evidencia independientes: el papel, el respaldo digital y el registro distribuido.
