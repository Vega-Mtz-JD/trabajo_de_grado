# SISTEMA DE VOTACIÓN ELECTRÓNICA OFFLINE CON BLOCKCHAIN — Propuesta v5.0

> **Estado:** Diseño corregido / inicio de implementación (v5.1: BD PostgreSQL)
> **Fecha:** 5 de octubre de 2026
> **Modalidad:** Proyecto de Grado — Carrera de Ingeniería de Sistemas, UPEA
> **Postulante:** Diego [Apellidos]
> **Caso de aplicación:** [EMPRESA — por definir]
> **Tutor metodológico / especialista / revisor:** [Pendientes]
> **Repositorio:** [Pendiente — GitHub]
> **Licencia del código:** Apache 2.0
>
> Las marcas **⚠️ VERIFICAR** señalan datos que deben confirmarse con la fuente primaria
> antes de citarlos en el documento final.

---

## TABLA DE CONTENIDOS

0. [Cambios respecto a la v4](#0-cambios-respecto-a-la-v4)
1. [Título](#1-título)
2. [Resumen ejecutivo](#2-resumen-ejecutivo)
3. [Antecedentes](#3-antecedentes)
4. [Planteamiento del problema](#4-planteamiento-del-problema)
5. [Objetivos](#5-objetivos)
6. [Justificación](#6-justificación)
7. [Límites, alcances y aporte](#7-límites-alcances-y-aporte)
8. [Metodología](#8-metodología)
9. [Arquitectura física](#9-arquitectura-física)
10. [Arquitectura de software](#10-arquitectura-de-software)
11. [Diseño de seguridad y secreto del voto](#11-diseño-de-seguridad-y-secreto-del-voto)
12. [Módulo blockchain — Hyperledger Fabric](#12-módulo-blockchain--hyperledger-fabric)
13. [Proceso electoral y flujo de votación](#13-proceso-electoral-y-flujo-de-votación)
14. [Auditoría triple (verificación multinivel)](#14-auditoría-triple-verificación-multinivel)
15. [Base de datos](#15-base-de-datos)
16. [Modelo de amenazas](#16-modelo-de-amenazas)
17. [Hardening del equipo (offline)](#17-hardening-del-equipo-offline)
18. [Manejo de errores y modos de operación](#18-manejo-de-errores-y-modos-de-operación)
19. [Roles](#19-roles)
20. [Stack tecnológico](#20-stack-tecnológico)
21. [Hardware y presupuesto](#21-hardware-y-presupuesto)
22. [Plan de pruebas y calidad](#22-plan-de-pruebas-y-calidad)
23. [Consideraciones éticas, legales y de privacidad](#23-consideraciones-éticas-legales-y-de-privacidad)
24. [Cronograma](#24-cronograma)
25. [Pendientes](#25-pendientes)
26. [Referencias](#26-referencias)

---

## 0. CAMBIOS RESPECTO A LA V4

| # | Problema en la v4 | Corrección en la v5 |
|---|---|---|
| 1 | Se usaba `fabric-sdk-py`, un SDK abandonado que no soporta Fabric 2.5. El código del anexo 26.7 (`from fabric_sdk_py import FabricClient`) no existe. | Un **puente en Go** con el *Fabric Gateway client API* oficial expone una API REST local (`127.0.0.1`). La app Python la consume. Ver ADR-002. |
| 2 | **El secreto del voto se rompía:** `votantes.timestamp_voto` + `votos.timestamp` permiten unir votante y voto por la hora, y registrar cada voto en el ledger con su hora produce el mismo problema. | Los votos se guardan **sin hora y con ID aleatorio**, en una tabla sin orden de inserción. El padrón solo guarda `ya_voto`. Al ledger se envían **checkpoints por lotes** y no votos individuales. Ver §11.3. |
| 3 | El campo `huella_hash` no se puede usar: dos lecturas del mismo dedo nunca producen el mismo hash, porque el *matching* biométrico es aproximado. | Se guarda la **plantilla biométrica cifrada** y la comparación 1:1 la hace el SDK del lector. |
| 4 | Se usaba AES-256 sin definir quién tiene la clave. | Se usa **cifrado híbrido**: AES-256-GCM por voto, con la clave envuelta en RSA-OAEP usando la clave pública de la elección. La clave privada queda **repartida con Shamir (3 de 5)** entre los custodios y solo se reconstruye en el escrutinio. Ver ADR-003. |
| 5 | Se presentaba la blockchain mononodo como "inmutable". | Se presenta con honestidad como **evidencia de manipulación** (*tamper-evidence*), reforzada con un **anclaje externo**: el hash del último bloque y la raíz de Merkle se imprimen en el acta de papel, con código QR, y la firman los delegados. |
| 6 | El plan de pruebas era de aplicación web (XSS, CSRF, OWASP ZAP, Locust) y fijaba una meta de más de 100 TPS. | Pruebas adaptadas a una aplicación de escritorio offline: manipulación de datos, escape del kiosco, secreto del voto, SUS, FAR/FRR y latencia del ledger. La meta de rendimiento es realista: alrededor de 1 voto por minuto. |
| 7 | El hardening incluía SSH, fail2ban y unattended-upgrades, que **suponen una red** y contradicen el diseño offline. | Se aplica un hardening **sin red**: sin servidor SSH, con Wi-Fi y Bluetooth deshabilitados en el kernel, cifrado de disco LUKS, contraseña de BIOS y kiosco con `cage`. |
| 8 | El FPM10A y las impresoras Adafruit/SparkFun son dispositivos **seriales (UART)**, no USB. | Se usa un lector **ZKTeco ZK9500 / SLK20R** con el SDK para Linux y una impresora térmica **USB ESC/POS** genérica de 58 u 80 mm. |
| 9 | PyQt6 tiene licencia GPL, que es incompatible con distribuir el código bajo Apache 2.0. | Se usa **PySide6 (LGPL)**. |
| 10 | El "modo emergencia sin VVPAT" anulaba la auditoría. | Si falla la impresora, **se pausa la votación**. Si no se puede reparar, se pasa a papeleta física y se registra en el acta. |
| 11 | Faltaban el voto blanco/nulo, la "zerésima" de apertura y los objetivos general y específicos. | Se añaden las tres cosas (§5, §13). |
| 12 | El VVPAT incluía fecha y hora. | El VVPAT **no lleva hora ni datos del votante**. Lleva un código de verificación del voto. |
| 13 | Se afirmaba ser el "primer sistema de votación con blockchain de la carrera". | **Es falso.** Existe la tesis TG-0059 (UPEA, 2020). El aporte se reformula en §7.3 para diferenciarse de ella. |
| 14 | Se exigía FAR < 0.1 % y FRR < 1 % sin un método de medición. | Se define un protocolo de medición propio y se reportan los valores observados, sin prometer cifras. |
| 15 | Se citaba ISO 25000 de forma genérica. | Se usa el modelo **ISO/IEC 25010** (características de calidad del producto). |
| 16 | *(v5.1)* La tutora no acepta bases de datos ligeras como SQLite/SQLCipher. | Se usa **PostgreSQL 17** con roles de mínimo privilegio, pgaudit y "mezcla de urna" para proteger el secreto del voto. Ver ADR-008. |

---

## 1. TÍTULO

**SISTEMA DE VOTACIÓN ELECTRÓNICA OFFLINE CON BLOCKCHAIN PARA AUDITORÍA Y VERIFICACIÓN MULTINIVEL DE RESULTADOS**
**CASO: [EMPRESA]**

- Tiene 16 palabras más el caso, siguiendo el formato habitual de la carrera, y un solo sustantivo principal ("Sistema").
- **Subtítulo técnico:** autenticación biométrica 1:1, comprobante en papel verificable (VVPAT), cifrado de umbral, Hyperledger Fabric y auditoría triple (papel, USB y ledger).
- **Nombre del producto:** **VOTO SEGURO**.

---

## 2. RESUMEN EJECUTIVO

VOTO SEGURO es un sistema de votación electrónica presencial que funciona **sin conexión a ninguna red**. Su flujo es el siguiente:

1. El votante se autentica con **CI y huella dactilar (comparación 1:1)**.
2. Elige su opción en una pantalla en **modo kiosco**.
3. Se imprime un **comprobante en papel (VVPAT)**. El votante lo verifica y lo deposita en una urna sellada.
4. El voto se guarda **cifrado con la clave pública de la elección**. La clave privada está repartida entre los custodios del comité electoral y nadie puede leer votos antes del escrutinio.
5. Los hitos de la elección (configuración, apertura en cero, checkpoints, cierre y acta) se anclan en una red **Hyperledger Fabric 2.5** local.
6. Al cierre se generan un **acta firmada digitalmente**, una **memoria USB cifrada** con toda la evidencia y un **verificador** que contrasta papel, USB y ledger.

| Característica | Decisión v5 |
|---|---|
| Autenticación | CI + huella (ZKTeco, SDK Linux). Excepción manual registrada para huellas ilegibles. |
| Interfaz | PySide6 en pantalla completa sobre el compositor kiosco `cage` |
| Comprobante | VVPAT térmico USB ESC/POS, sin hora ni identidad, con código de voto y QR |
| Votos | AES-256-GCM + RSA-OAEP (clave de la elección), clave privada con Shamir 3 de 5 |
| Integridad | SHA3-256, árbol de Merkle, bitácora encadenada, firmas RSA-PSS |
| Blockchain | Fabric 2.5 LTS: 1 CA, 1 orderer (Raft) y 1 peer, con chaincode en Go |
| Integración | Puente Go (Fabric Gateway) ↔ app Python por REST local, con cola *outbox* |
| Base de datos | PostgreSQL 17, solo por socket Unix (sin TCP), roles de mínimo privilegio, triggers *append-only* y pgaudit |
| SO | Debian 13 "Trixie", sin red y con disco cifrado |
| Licencia | Apache 2.0 |

---

## 3. ANTECEDENTES

### 3.1 Internacionales

| País / sistema | Qué es | Qué se adopta |
|---|---|---|
| **Brasil — Urna Eletrônica (desde 1996)** | Máquina offline basada en Linux. Imprime la **"zerésima"** (reporte en cero) al abrir y el **boletim de urna** firmado al cerrar. | Zerésima de apertura, acta firmada digitalmente y sistema operativo Linux |
| **India — EVM + VVPAT** | El VVPAT se muestra unos 7 segundos tras un visor y cae a una caja sellada. Incluye *mock poll* antes de abrir. | VVPAT sin que el votante se lo lleve y simulacro previo |
| **Paraguay — Máquina de votación TSJE (desde 2021)** | Boleta Única Electrónica (MSA): una pantalla táctil imprime una boleta con chip RFID que el elector verifica y deposita en la urna. Los apoderados técnicos auditan el software y el hardware. | Boleta impresa como evidencia principal, verificación por el elector y auditoría previa por delegados |
| **Perú — ONPE, Voto Electrónico Presencial (VEP)** | Separa la estación de identificación de la estación de votación. Los equipos están aislados, sin Wi-Fi ni Bluetooth. Imprime una constancia cotejable por los personeros. | Aislamiento total y separación entre identificación y voto |
| **Portugal / Malasia — investigación con Hyperledger Fabric** | Prototipos académicos de votación con Fabric y medición de rendimiento con Caliper. ⚠️ VERIFICAR: citar los artículos concretos (autor, año, DOI). | Fabric como registro permisionado y métricas de latencia |

### 3.2 Nacionales

| Antecedente | Detalle | Relación con este proyecto |
|---|---|---|
| **Churata Sonco, H. (2020). *Protocolos Blockchain aplicados a un sistema de votación electrónica. Caso: Carrera Ingeniería de Sistemas – UPEA*. Tesis de Grado TG-0059, UPEA.** | Sistema **web** con Flask y MariaDB, blockchain **propia en Python** con prueba de trabajo, SHA-256 y RSA. Metodología UWE, calidad ISO 9126, costos COCOMO. | Es el antecedente más cercano. **Este proyecto se diferencia** en que es offline y presencial, usa biometría, VVPAT, una blockchain permisionada estándar (Fabric) en lugar de una propia, cifrado de umbral y auditoría triple. |
| **Villarpando, B. S. (2017). *Diseño de un modelo de sistema de voto electrónico en proceso de elecciones*. Tesis, UMSA.** | Modelo de voto electrónico con anonimato (citado en TG-0059). ⚠️ VERIFICAR en el repositorio de la UMSA. | Fundamenta el requisito de anonimato |
| **TED Chuquisaca (2018): pruebas de voto electrónico para gobiernos estudiantiles** | Sistema con padrón, registro de frentes, emisión del voto en pantalla táctil y cómputo simultáneo (Correo del Sur, 2018, citado en TG-0059). ⚠️ VERIFICAR la nota original. | Muestra que el OEP ya probó voto electrónico en elecciones no estatales |
| **Desarrolladores cochabambinos (2017): votación con blockchain** | Nota de prensa (Camacho, 2017, citada en TG-0059). ⚠️ VERIFICAR. | Interés local en blockchain |

### 3.3 Código abierto de referencia

- **VotingWorks (EE.UU.):** sistema electoral de código abierto basado en Debian, con boleta en papel como registro oficial.
- **Hyperledger Fabric (LF Decentralized Trust):** blockchain permisionada. La versión 2.5 es la LTS vigente, con parches 2.5.x publicados en 2026.

---

## 4. PLANTEAMIENTO DEL PROBLEMA

> ⚠️ Los datos concretos (número de votantes, duración del conteo, incidentes, costos) deben
> obtenerse de **[EMPRESA]** mediante entrevista y revisión de actas anteriores.

### 4.1 Situación actual (a validar con la empresa)

En [EMPRESA], los procesos de votación (directorio, comité, representantes, etc.) se hacen con papeletas físicas y conteo manual. No existe un registro digital verificable de los resultados ni un mecanismo independiente para comprobar que el resultado proclamado coincide con los votos emitidos.

### 4.2 Problema principal

> **Los procesos de votación de [EMPRESA] carecen de mecanismos que permitan verificar de forma independiente la autenticidad del votante, la integridad de los votos y la exactitud de los resultados, lo que provoca demoras en el conteo, errores humanos y desconfianza en los resultados.**

### 4.3 Problemas secundarios

| # | Problema | Efecto |
|---|---|---|
| 1 | Identificación del votante solo visual, mediante la CI | Riesgo de suplantación y de voto múltiple |
| 2 | Conteo manual de papeletas | Resultados tardíos y errores de conteo |
| 3 | Actas en papel sin protección de integridad | Las actas pueden alterarse sin dejar rastro |
| 4 | No hay evidencia independiente del resultado | Las impugnaciones son difíciles de resolver |
| 5 | Costo de impresión y logística de papeletas en cada proceso | Gasto recurrente para la empresa |

### 4.4 Formulación

> ¿Cómo garantizar la autenticidad del votante, el secreto e integridad del voto y la verificabilidad de los resultados en los procesos de votación de [EMPRESA]?

---

## 5. OBJETIVOS

### 5.1 Objetivo general

**Desarrollar un sistema de votación electrónica offline con autenticación biométrica, comprobante en papel verificable y registro en blockchain Hyperledger Fabric, que permita la auditoría y verificación multinivel de los resultados de los procesos de votación de [EMPRESA].**

### 5.2 Objetivos específicos

1. Analizar el proceso de votación actual de [EMPRESA] y definir los requerimientos funcionales y no funcionales.
2. Diseñar una arquitectura de seguridad, basada en un modelo de amenazas, que garantice el secreto del voto y la integridad de los resultados mediante cifrado de umbral, firmas digitales y bitácora encadenada.
3. Implementar los módulos de empadronamiento biométrico, autenticación 1:1, emisión del voto con comprobante VVPAT y escrutinio.
4. Implementar una red Hyperledger Fabric con un *smart contract* (chaincode) que ancle los hitos del proceso electoral.
5. Implementar un verificador de auditoría triple que contraste el comprobante en papel, el respaldo USB y el ledger.
6. Evaluar el sistema mediante pruebas funcionales, de seguridad y de usabilidad, la calidad según ISO/IEC 25010 y su costo con COCOMO II.

---

## 6. JUSTIFICACIÓN

| Tipo | Justificación |
|---|---|
| **Técnica** | Usa hardware existente (una PC o laptop) y periféricos de bajo costo, con software libre (Debian, Python y Fabric). Funcionar offline elimina los ataques remotos. Fabric es un estándar mantenido por la Linux Foundation. |
| **Económica** | Reduce papeletas, horas-persona de conteo e impugnaciones. Sin costo de licencias. Inversión estimada en periféricos: 250–400 USD (§21). |
| **Social** | Da transparencia, porque el votante ve su comprobante y los delegados firman la zerésima y el acta. Da confianza, porque cualquier auditor puede verificar el resultado. Es inclusivo, con botones grandes y una excepción documentada para huellas ilegibles. |
| **Académica** | Aplica criptografía de umbral, blockchain permisionada y auditoría multinivel, en lugar de una blockchain hecha a medida. Sirve de base reproducible para futuros trabajos. |

---

## 7. LÍMITES, ALCANCES Y APORTE

### 7.1 Alcances

- Un equipo (una mesa) con un padrón de prueba de hasta 500 electores. Las pruebas se hacen con 100.
- Una o varias elecciones por jornada, con candidatos o frentes, voto blanco y voto nulo.
- Empadronamiento biométrico, autenticación 1:1, votación, VVPAT, cierre, escrutinio, acta, exportación a USB y verificación.
- Red Fabric local (mononodo) con chaincode de anclaje.
- Interfaces de votante (kiosco), operador de mesa y auditor.

### 7.2 Límites

- No reemplaza al sistema electoral del OEP ni se aplica a elecciones públicas. La Ley 026 solo contempla el voto electrónico para bolivianos en el exterior (Art. 43.II).
- No es un sistema certificado para producción.
- No hay consolidación automática entre varias mesas. Cada equipo es independiente y la consolidación es manual o externa.
- Una blockchain mononodo **no garantiza inmutabilidad frente a quien controla el equipo**: aporta evidencia de manipulación y depende del anclaje externo en papel.
- No hay voto remoto ni por internet.

### 7.3 Aporte

Un sistema de votación presencial que combina cuatro elementos que el antecedente local (TG-0059) no tiene: **(1)** verificación del votante en papel (VVPAT), **(2)** confidencialidad de umbral (ningún actor individual puede descifrar votos), **(3)** blockchain permisionada estándar con anclaje en papel y **(4)** un procedimiento de auditoría triple reproducible.

---

## 8. METODOLOGÍA

| Aspecto | Método |
|---|---|
| Desarrollo | **SCRUM**, con sprints de 2 a 3 semanas (ver §24) |
| Modelado | **UML 2.5**: casos de uso, clases, secuencia, actividades, estados (máquina de estados de la elección) y despliegue |
| Seguridad | Controles de **ISO/IEC 27001/27002** (control de acceso, criptografía, registro y auditoría), **STRIDE** para amenazas y **MAGERIT v3** para el análisis de riesgos |
| Calidad | **ISO/IEC 25010** |
| Costos | **COCOMO II** (puntos de función → SLOC → esfuerzo) |
| Usabilidad | Cuestionario **SUS** (System Usability Scale) |
| Decisiones técnicas | Registros **ADR** en `docs/decisiones/` |

> ⚠️ Confirmar con el tutor metodológico si la carrera exige otra metodología (p. ej. XP u OpenUP) o una estructura de capítulos específica.

---

## 9. ARQUITECTURA FÍSICA

```
┌──────────────────────────── MESA DE VOTACIÓN ───────────────────────────┐
│                                                                         │
│  [Operador]                    [Cabina del votante, con biombo]         │
│  Teclado + lector de CI        Monitor + mouse (o pantalla táctil)      │
│  Lector de huella ZKTeco       Impresora térmica VVPAT ──► URNA SELLADA │
│        │                              │                                 │
│        └──────────────┬───────────────┘                                 │
│                  PC / LAPTOP (Debian 13, sin red, disco LUKS)           │
│                  Docker: Fabric (CA, orderer, peer)                     │
│                       │                                                 │
│                  UPS ── corriente                                       │
│                                                                         │
│  Puertos sin uso sellados con etiquetas de seguridad                    │
│  USB de exportación: solo al cierre, en presencia de delegados          │
└─────────────────────────────────────────────────────────────────────────┘
```

Siguiendo al VEP peruano, la **identificación** (operador más lector de huella) y la **emisión del voto** (cabina) son puestos físicamente separados, aunque ambos se conecten al mismo equipo.

---

## 10. ARQUITECTURA DE SOFTWARE

### 10.1 Componentes

```
┌──────────────────────── Aplicación Python (votoseguro) ───────────────────────┐
│ ui/        PySide6: kiosco votante · panel operador · panel auditor           │
│ servicios/ empadronamiento · apertura · votación · cierre · escrutinio ·      │
│            exportación · verificación                                         │
│ dominio/   modelos · máquina de estados de la elección · reglas               │
│ cripto/    cifrado híbrido · firmas · SHA3 · Merkle · Shamir                  │
│ auditoria/ bitácora encadenada por hash                                       │
│ datos/     PostgreSQL (psycopg 3) · repositorios · esquemas + roles + triggers│
│ hardware/  LectorHuella {Simulado, ZKTeco} · Impresora {PDF, ESC/POS}         │
│ blockchain/ cliente REST del puente · outbox (cola de reintentos)             │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       │ HTTP en 127.0.0.1 (token local)
┌──────────────────────────────────────▼────────────────────────────────────────┐
│ Puente Go (fabric-gateway)  ── gRPC/TLS ──►  Peer ── Orderer (Raft) ── CA     │
│                                              └─ chaincode "acta" (Go)         │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Máquina de estados de la elección

```
CONFIGURACION ─► EMPADRONAMIENTO ─► LISTA ─(zerésima)─► ABIERTA ─► CERRADA
                                                                     │
                     EXPORTADA ◄── ESCRUTADA ◄─(3 de 5 custodios)────┘
```

Cada transición queda registrada en la bitácora y se ancla en Fabric. Las transiciones no válidas (por ejemplo, votar en estado CERRADA) se rechazan tanto en la aplicación como en el chaincode.

### 10.3 Abstracción de hardware

Los periféricos se usan a través de interfaces. Así se puede desarrollar y probar todo **sin el hardware** y luego conectar el real:

- `LectorHuella`: `capturar() → plantilla`, `comparar(plantilla_guardada, plantilla_viva) → puntaje`. Hay una implementación simulada para pruebas y otra para ZKTeco, que usa `ctypes` sobre `libzkfp.so`.
- `Impresora`: `imprimir_vvpat(...)`, `imprimir_acta(...)`, `estado()`. Hay una implementación que genera PDF (simulada) y otra ESC/POS por USB (`python-escpos`).

---

## 11. DISEÑO DE SEGURIDAD Y SECRETO DEL VOTO

### 11.1 Requisitos de seguridad

| Id | Requisito |
|---|---|
| RS1 | Solo un elector habilitado puede votar, y una sola vez. |
| RS2 | Nadie, ni siquiera el administrador, puede asociar un voto con un votante. |
| RS3 | Nadie puede conocer resultados parciales antes del cierre. |
| RS4 | Cualquier alteración de votos, bitácora o acta es detectable. |
| RS5 | El resultado puede verificarse de forma independiente a partir del papel, del USB y del ledger. |

### 11.2 Gestión de claves (cifrado de umbral)

1. **Configuración.** Se genera el par de claves de la elección (RSA, por defecto de 3072 bits). La clave privada se cifra con una clave aleatoria de 256 bits (KEK). La KEK se divide con **Shamir (k=3, n=5)** y se destruye. Cada custodio (presidente del comité, dos delegados, auditor y representante de la empresa) recibe una **parte impresa con QR** y la guarda en un sobre sellado.
2. **Votación.** Cada voto se cifra con la **clave pública**. El equipo **no puede descifrar** votos durante la jornada (RS3).
3. **Escrutinio.** Al menos 3 custodios presentan sus partes. Se reconstruye la KEK **solo en memoria**, se descifran los votos, se cuentan y se borra la clave.
4. **Firma.** El equipo tiene una clave de dispositivo RSA-2048 (en el TPM si existe, o cifrada con una frase de paso) con la que firma la zerésima, el acta y el manifiesto del USB. Operador y auditor firman además con sus claves personales.

### 11.3 Secreto del voto (RS2)

| Medida | Qué impide |
|---|---|
| Tabla `urna.voto` **sin fecha ni hora**, con clave primaria aleatoria de 128 bits | Ordenar los votos por un campo de la tabla |
| **Mezcla de la urna** en cada checkpoint: dentro de una transacción se hace `TRUNCATE` y se reinsertan los votos en orden aleatorio, verificando que el conteo y la raíz de Merkle no cambien (ADR-008) | Reconstruir el orden de emisión con las columnas internas de PostgreSQL (`xmin`, `ctid`) |
| El padrón solo guarda `ya_voto = 1`, sin hora | Correlacionar votos por tiempo |
| La bitácora registra "voto emitido n.º k" **sin** identificador ni hash del voto | Unir la bitácora con los votos |
| El ledger recibe **checkpoints cada N votos** (N ≥ 10, configurable) con conteo y raíz de Merkle, **no votos individuales** | Unir por hora del bloque. Entre dos checkpoints, el anonimato es de al menos N votantes. |
| Todos los votos cifrados tienen **la misma longitud**, con relleno fijo | Deducir el candidato por el tamaño del texto cifrado |
| El VVPAT **no lleva hora ni datos del votante** y lo deposita el propio votante en la urna | La compra de votos (el votante no se lleva comprobante) |

### 11.4 Integridad (RS4)

- **Bitácora encadenada:** `hash_i = SHA3-256(hash_{i-1} ‖ evento_i)`. Triggers SQL bloquean `UPDATE` y `DELETE`.
- **Árbol de Merkle** sobre los hashes de los votos cifrados, ordenados lexicográficamente. La raíz va al checkpoint, al acta y al ledger.
- **Firmas RSA-PSS** sobre la zerésima, el acta y el manifiesto del USB.
- **Anclaje externo:** el acta impresa lleva la raíz de Merkle, el hash del acta y el hash del último bloque Fabric, en texto y en QR, firmados a mano por los delegados. Para alterar el resultado habría que alterar también esos papeles.

---

## 12. MÓDULO BLOCKCHAIN — HYPERLEDGER FABRIC

### 12.1 Por qué Fabric y no una cadena propia ni Ethereum

| Opción | Razón para descartarla o elegirla |
|---|---|
| Cadena propia en Python (como TG-0059) | Es fácil de reescribir por completo y no aporta un estándar → **descartada** |
| Ethereum público o Besu | Requiere red y gas, y no tiene sentido offline → **descartada** |
| **Fabric 2.5 LTS** | Es permisionada, usa identidades X.509 y endorsement, el chaincode controla las transiciones de estado y la tecnología está documentada y mantenida → **elegida** |

### 12.2 Topología mononodo

Se levantan con `docker compose` y las imágenes **pre-cargadas** (`docker load`), sin necesidad de internet:
- `ca.votoseguro`: Fabric CA (identidades del peer, del orderer, del cliente y del auditor).
- `orderer.votoseguro`: ordering service **Raft de un solo nodo**.
- `peer0.votoseguro`: con base de estado **LevelDB** (más liviana que CouchDB; las consultas ricas no son necesarias).
- Canal `elecciones`, chaincode `acta` (Go).

Con un nodo, Raft **no tolera fallas**. Se usa porque es el único consenso soportado en Fabric 2.5 sin red externa. El modo degradado (§18) cubre el caso de caída.

### 12.3 Chaincode `acta` (Go)

| Función | Datos anclados | Validaciones |
|---|---|---|
| `RegistrarEleccion` | id, hash de la configuración (candidatos), huella de la clave pública de la elección, huella del dispositivo | No debe existir ya |
| `RegistrarApertura` | hash de la zerésima firmada, compromiso del padrón (raíz de Merkle de los CI con sal, sin datos personales) y total del padrón | Estado = LISTA |
| `RegistrarCheckpoint` | n.º de secuencia, conteo acumulado, raíz de Merkle | Estado = ABIERTA y conteo creciente |
| `RegistrarCierre` | total de votos, total de votantes que votaron, raíz final | Estado = ABIERTA. Votos = votantes que votaron. |
| `RegistrarEscrutinio` | resultados por opción, hash del acta | Estado = CERRADA. La suma debe ser igual al total. |
| `RegistrarExportacion` | hash del manifiesto del USB | Estado = ESCRUTADA |
| `ObtenerEleccion` / `ObtenerHistorial` | — | Solo lectura |

> **Nunca** se escriben datos personales en el ledger, porque ahí no pueden borrarse.

### 12.4 Puente Go e integración

- Servicio Go con `github.com/hyperledger/fabric-gateway`, escuchando **solo en 127.0.0.1** y protegido con un token local.
- Expone `POST /tx/{funcion}`, `GET /eleccion/{id}`, `GET /historial/{id}` y `GET /salud`.
- La app Python escribe cada anclaje en una tabla **outbox** y un trabajador lo envía al puente. Si Fabric no responde, la votación **continúa** y los anclajes se envían cuando se recupera, en orden y de forma idempotente.

---

## 13. PROCESO ELECTORAL Y FLUJO DE VOTACIÓN

### 13.1 Fases

| # | Fase | Responsable | Evidencia |
|---|---|---|---|
| 1 | Configuración: elección, opciones, generación de claves y reparto de partes Shamir | Administrador + custodios | Ancla `RegistrarEleccion` |
| 2 | Empadronamiento: CI, nombres y plantilla de huella (cifrada) | Operador | Bitácora |
| 3 | Simulacro (*mock poll*) en una elección de prueba separada | Operador + delegados | Acta de simulacro |
| 4 | Apertura: autodiagnóstico de hardware e impresión de la **zerésima** (0 votos por opción) | Operador + delegados (firman) | Ancla `RegistrarApertura` |
| 5 | Identificación: CI + huella 1:1, con máximo 3 intentos y luego excepción manual justificada | Operador + sistema | Bitácora |
| 6 | Votación: selección, pantalla de confirmación y VVPAT | Votante | Voto cifrado + VVPAT en la urna |
| 7 | Checkpoints automáticos cada N votos | Sistema | Ancla `RegistrarCheckpoint` |
| 8 | Cierre | Operador + delegados | Ancla `RegistrarCierre` |
| 9 | Escrutinio con 3 de 5 custodios, acta firmada e impresa con QR | Custodios + auditor | Ancla `RegistrarEscrutinio` |
| 10 | Exportación a USB cifrado (dos copias) | Operador | Ancla `RegistrarExportacion` |
| 11 | Auditoría triple | Auditor | Informe del verificador |

### 13.2 Flujo del votante

```
Operador ingresa CI ─► ¿habilitado y sin votar? ─NO─► rechazo (bitácora)
        │SÍ
Huella 1:1 ─FALLA (3 intentos)─► excepción manual (motivo + firma del operador, bitácora)
        │OK
Cabina habilitada ─► elige opción (incluye BLANCO) ─► pantalla de confirmación
        │                                              │ "Corregir" vuelve a la selección
        ▼ Confirmar
Transacción atómica: marca ya_voto=1 + inserta el voto cifrado
        ▼
Imprime VVPAT ─► el votante lo verifica y lo deposita en la urna
        ▼
¿Se llegó a N votos desde el último checkpoint? ─► anclar en Fabric (vía outbox)
```

**Atomicidad:** marcar `ya_voto` e insertar el voto se hacen en **una sola transacción SQL**. Si la impresora falla después, el voto ya está registrado: se reimprime el mismo VVPAT (marcado como "REIMPRESIÓN") y queda en la bitácora.

### 13.3 Contenido del VVPAT

```
   VOTO SEGURO — [EMPRESA]
   Elección: Directorio 2026
   Mesa: 01
   ───────────────────────
   OPCIÓN: FRENTE A — Juan Pérez
   ───────────────────────
   Código: 7F3A-91C2        [QR]
```

El código de 8 caracteres hexadecimales se deriva del hash del voto cifrado. Permite cotejar cada papeleta con su voto digital sin revelar la identidad del votante.

### 13.4 Tiempos objetivo

| Paso | Objetivo |
|---|---|
| Identificación (CI + huella) | ≤ 15 s |
| Selección y confirmación | 30–60 s |
| Impresión del VVPAT | ≤ 10 s |
| Cifrado y guardado | < 0,5 s |
| **Total por votante** | **≤ 2 min** |
| Anclaje en Fabric (asíncrono) | ≤ 3 s, sin bloquear al votante |

---

## 14. AUDITORÍA TRIPLE (VERIFICACIÓN MULTINIVEL)

| Nivel | Fuente | Qué contiene | Cómo se verifica |
|---|---|---|---|
| 1 | **Papel**: urna de VVPAT, zerésima y acta firmada | Opción y código de cada voto, totales, hashes y QR | Conteo manual de la urna contra el acta, y cotejo por muestreo de códigos con los votos digitales |
| 2 | **USB cifrado** | Votos cifrados, bitácora, acta, export del ledger, manifiesto SHA3 firmado | El verificador comprueba la firma del manifiesto, los hashes, la bitácora encadenada, la raíz de Merkle y el re-escrutinio |
| 3 | **Ledger Fabric** | Hitos con conteos y raíces de Merkle | El verificador compara cada checkpoint y el cierre con el USB, y el hash del último bloque con el papel |

**Resultado:** si los tres niveles coinciden, el informe dice **CONFORME**. Si no, se emite un informe de discrepancias que indica qué nivel y qué elemento difieren, y **prevalece el papel** (criterio de los sistemas VVPAT).

---

## 15. BASE DE DATOS

**PostgreSQL 17**, instalado como paquete nativo de Debian. Solo acepta conexiones por socket Unix y organiza los datos en **esquemas separados por responsabilidad**, con roles de mínimo privilegio. La justificación completa está en ADR-008. El esquema resumido es el siguiente (el detalle irá en el código, en `app/src/votoseguro/datos/esquema.sql`):

```sql
CREATE SCHEMA eleccion;  CREATE SCHEMA padron;  CREATE SCHEMA urna;
CREATE SCHEMA auditoria; CREATE SCHEMA blockchain;

CREATE TABLE eleccion.eleccion (
  id uuid PRIMARY KEY, nombre text NOT NULL,
  estado text NOT NULL CHECK (estado IN ('CONFIGURACION','EMPADRONAMIENTO','LISTA',
                                         'ABIERTA','CERRADA','ESCRUTADA','EXPORTADA')),
  clave_publica bytea NOT NULL, clave_privada_cifrada bytea NOT NULL,
  umbral smallint NOT NULL, partes smallint NOT NULL,
  checkpoint_cada smallint NOT NULL DEFAULT 10 CHECK (checkpoint_cada >= 10),
  creada_en timestamptz NOT NULL DEFAULT now());

CREATE TABLE eleccion.opcion (
  id serial PRIMARY KEY, eleccion_id uuid NOT NULL REFERENCES eleccion.eleccion,
  codigo text NOT NULL, nombre text NOT NULL, frente text, orden smallint NOT NULL,
  tipo text NOT NULL CHECK (tipo IN ('CANDIDATO','BLANCO','NULO')),
  UNIQUE (eleccion_id, codigo));

CREATE TABLE padron.votante (
  eleccion_id uuid REFERENCES eleccion.eleccion, ci text, nombres text NOT NULL,
  apellidos text NOT NULL, plantilla_cifrada bytea,
  habilitado boolean NOT NULL DEFAULT true,
  ya_voto boolean NOT NULL DEFAULT false,      -- sin hora de voto (RS2)
  PRIMARY KEY (eleccion_id, ci));

CREATE TABLE urna.voto (                         -- sin fecha ni orden; se mezcla (ADR-008)
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  eleccion_id uuid NOT NULL REFERENCES eleccion.eleccion,
  voto_cifrado bytea NOT NULL, hash_voto text NOT NULL UNIQUE);

CREATE TABLE auditoria.bitacora (
  seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, momento timestamptz NOT NULL DEFAULT now(),
  actor text NOT NULL, evento text NOT NULL, detalle jsonb,
  hash_anterior text NOT NULL, hash text NOT NULL UNIQUE);

CREATE TABLE eleccion.checkpoint (eleccion_id uuid, seq int, conteo int NOT NULL,
  raiz_merkle text NOT NULL, PRIMARY KEY (eleccion_id, seq));

CREATE TABLE eleccion.acta (id uuid PRIMARY KEY, eleccion_id uuid NOT NULL,
  tipo text CHECK (tipo IN ('ZERESIMA','CIERRE','ESCRUTINIO')),
  contenido jsonb NOT NULL, hash text NOT NULL, firma bytea NOT NULL);

CREATE TABLE blockchain.outbox (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  funcion text NOT NULL, argumentos jsonb NOT NULL,
  estado text NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE','ENVIADO','ERROR')),
  intentos int NOT NULL DEFAULT 0, tx_id text);

CREATE TABLE eleccion.usuario (nombre text PRIMARY KEY,
  rol text NOT NULL CHECK (rol IN ('ADMIN','OPERADOR','AUDITOR')),
  hash_password text NOT NULL, clave_publica bytea);

-- Append-only: triggers BEFORE UPDATE OR DELETE / BEFORE TRUNCATE → RAISE EXCEPTION
-- en urna.voto (salvo dentro de urna.mezclar()), auditoria.bitacora y eleccion.acta.
-- Privilegios: vs_app NO tiene INSERT en urna.voto ni UPDATE de ya_voto; vota solo con
--              urna.emitir_voto() (SECURITY DEFINER: marca ya_voto + inserta el voto, atómico).
```

| Aspecto | Medida |
|---|---|
| Acceso | Solo socket Unix, sin TCP. Roles `vs_app`, `vs_auditor` y `vs_admin_bd`, con privilegios por esquema y por columna. |
| Cifrado | Disco cifrado con LUKS. Votos y plantillas biométricas cifrados en la aplicación. |
| Integridad | Triggers *append-only*, bitácora encadenada, raíz de Merkle y anclaje en Fabric |
| Auditoría | pgaudit (quién, qué y cuándo a nivel de BD) + bitácora de la aplicación |
| Respaldo | `pg_dump` cifrado al USB al cierre, además del paquete de auditoría |
| Secreto | Mezcla de la urna en cada checkpoint (ADR-008) |

---

## 16. MODELO DE AMENAZAS

### 16.1 STRIDE

| Amenaza | Ejemplo | Mitigación |
|---|---|---|
| **S**poofing (suplantación) | Votar con la CI de otra persona | Huella 1:1. Excepciones registradas y contadas en el acta. |
| **T**ampering (alteración) | Modificar votos o el acta en la BD | Roles de mínimo privilegio, triggers, pgaudit, Merkle, firmas, ledger y anclaje en papel |
| **R**epudiation (repudio) | El operador niega una excepción manual | Bitácora encadenada con actor y firma del acta |
| **I**nformation disclosure (fuga) | Conocer resultados parciales o el voto de alguien | Cifrado de umbral y diseño de secreto (§11.3) |
| **D**enial of service (denegación) | Corte de energía, caída de Fabric o falta de papel | UPS, outbox (modo degradado), alertas de papel y pausa controlada |
| **E**levation of privilege (elevación) | El votante escapa del kiosco | `cage`, usuario sin privilegios, atajos bloqueados y salida con contraseña |

### 16.2 Amenazas del contexto

| Amenaza | Mitigación |
|---|---|
| Compra de votos | El votante no se lleva comprobante y la cabina tiene biombo |
| Voto múltiple | `ya_voto` + huella 1:1 dentro de una transacción atómica |
| Manipulación del USB | Manifiesto firmado y comparación con el ledger y el papel |
| Operador deshonesto | Delegados presentes, cifrado de umbral y bitácora |
| Acceso físico al equipo | Disco LUKS, contraseña de BIOS, etiquetas de seguridad en puertos y carcasa |
| Ingeniería social | Protocolo escrito y capacitación de operadores |

### 16.3 Análisis de riesgos

Se hará con MAGERIT v3: inventario de activos (votos, claves, padrón, plantillas y equipo), valoración en las dimensiones de confidencialidad, integridad, disponibilidad, autenticidad y trazabilidad, amenazas, salvaguardas y riesgo residual. Va en el capítulo de seguridad del documento final.

---

## 17. HARDENING DEL EQUIPO (OFFLINE)

| Medida | Cómo |
|---|---|
| Sin red | Desinstalar NetworkManager y wpa_supplicant, bloquear los módulos de Wi-Fi y Bluetooth en `/etc/modprobe.d/` y no tener cable de red |
| Sin acceso remoto | **No** instalar `openssh-server` |
| Disco cifrado | LUKS al instalar Debian |
| PostgreSQL | `listen_addresses = ''` (solo socket Unix), autenticación `peer`/SCRAM, `archive_mode = off`, `wal_level = minimal`, pgaudit con `log_parameter = off` |
| Arranque | Contraseña de BIOS/UEFI, arranque solo desde disco y Secure Boot si está disponible |
| Kiosco | Usuario `kiosco` sin sudo, inicio automático en `cage -- votoseguro-kiosco` |
| Mínimo software | Instalación *netinst* mínima sin entorno de escritorio en producción |
| USB | Sin montaje automático. El montaje de exportación lo controla la app con el rol de operador. |
| AppArmor + auditd | Perfiles activos y registro de eventos del sistema |
| Docker | Imágenes Fabric pre-cargadas y red Docker interna (`internal: true`) |
| Integridad del software | Hash SHA3 del paquete instalado, impreso en la zerésima, que los delegados pueden comparar con el publicado |

Las actualizaciones se aplican **antes** de la jornada, en una ventana controlada con red y nunca durante el proceso.

---

## 18. MANEJO DE ERRORES Y MODOS DE OPERACIÓN

| Modo | Condición | Comportamiento |
|---|---|---|
| **Normal** | Todo operativo | Flujo completo |
| **Degradado** | Fabric o el puente no responden | La votación continúa y los anclajes se acumulan en el outbox. Aviso al operador. Al recuperarse, se sincroniza en orden. |
| **Pausa** | Falta papel o falla la impresora o el lector | La cabina se bloquea hasta resolverlo, y la bitácora registra la pausa y la reanudación |
| **Contingencia** | La falla no tiene solución en sitio | Se cierra la elección electrónica con acta parcial y se continúa con papeletas físicas según el protocolo de la empresa |
| **Detenido** | Falla crítica (BD o disco) | Se detiene. Se recupera desde la última copia íntegra y la bitácora determina el estado exacto. |

Protocolo ante errores: detectar, registrar en la bitácora, avisar al operador, aplicar la mitigación y escalar al soporte técnico si persiste.

---

## 19. ROLES

| Rol | Responsabilidades |
|---|---|
| Administrador | Configurar elecciones y opciones, y gestionar usuarios |
| Operador de mesa | Empadronar, abrir y cerrar, identificar votantes, autorizar excepciones y exportar |
| Votante | Emitir el voto y verificar su VVPAT |
| Custodio (×5) | Guardar su parte de la clave y presentarla en el escrutinio |
| Delegado | Presenciar y firmar la zerésima y el acta, y comparar hashes |
| Auditor | Ejecutar el verificador y emitir el informe de auditoría triple |
| Soporte técnico | Atender fallas de hardware y software |

---

## 20. STACK TECNOLÓGICO

| Componente | Tecnología |
|---|---|
| Lenguaje principal | Python 3.13 (versión de Debian 13) |
| Interfaz gráfica | PySide6 (Qt 6, LGPL) |
| Kiosco | `cage` (compositor Wayland para kiosco) |
| Criptografía | `cryptography` (AES-GCM, RSA-OAEP/PSS) y `hashlib` (SHA3-256). Shamir propio sobre GF(256), con pruebas. |
| Contraseñas | `argon2-cffi` (Argon2id) |
| Base de datos | **PostgreSQL 17** (paquete Debian) + extensión **pgaudit**, driver **psycopg 3** |
| Huella | ZKFinger SDK Linux (`libzkfp.so`) vía `ctypes` |
| Impresión | `python-escpos` (USB) y `reportlab` (PDF simulado) |
| QR | `qrcode` / `segno` |
| Blockchain | Hyperledger Fabric 2.5.x LTS, chaincode Go con `fabric-contract-api-go` |
| Puente | Go con `fabric-gateway` |
| Contenedores | Docker + Docker Compose |
| Pruebas | `pytest`, `pytest-cov`, `go test` y `bandit`/`pip-audit`/`gosec` (análisis estático y dependencias) |
| Diagramas | PlantUML |
| Documentación | Markdown en el repositorio y documento final en el formato de la UPEA |
| IDE | PyCharm Community / GoLand o VS Code |
| Versionado | Git + GitHub |

---

## 21. HARDWARE Y PRESUPUESTO

> Precios **referenciales en USD**. ⚠️ Cotizar en el mercado local (El Alto / La Paz) y
> convertir al tipo de cambio vigente al presentar el perfil.

| Ítem | Modelo sugerido | USD aprox. |
|---|---|---|
| PC / laptop | Equipo de la empresa o HP ProBook 650 G1 (desarrollo). Mínimo 8 GB de RAM (Docker + Fabric). | Ya disponible |
| Lector de huella | **ZKTeco ZK9500 o SLK20R** (confirmar que incluye el **ZKFinger SDK para Linux**) | 50–90 |
| Impresora térmica | USB ESC/POS de 58 u 80 mm (p. ej. Xprinter) | 35–70 |
| Rollos térmicos | 10 unidades | 10 |
| Monitor para la cabina | 19–22″ HDMI/VGA (o táctil si el presupuesto lo permite) | 70–120 |
| Mouse + teclado | USB | 15 |
| UPS | 600–800 VA | 40–60 |
| Urna acrílica + biombo | — | 20–40 |
| Memorias USB | 2 de 16 GB | 10 |
| Etiquetas de seguridad (*tamper-evident*) | 1 paquete | 5–10 |
| **Total** | | **≈ 255–425** |

**TPM:** es opcional. En el equipo se comprueba con `ls /dev/tpm*`. Si no hay TPM 2.0, la clave del dispositivo se protege con una frase de paso y Argon2id.

---

## 22. PLAN DE PRUEBAS Y CALIDAD

### 22.1 Pruebas

| Tipo | Qué se prueba | Herramienta | Criterio |
|---|---|---|---|
| Unitarias | Criptografía, Shamir, Merkle, bitácora, reglas y máquina de estados | pytest | Cobertura de los módulos núcleo ≥ 80 % |
| Chaincode | Funciones y validaciones de estado | `go test` con stubs | Todas las transiciones inválidas rechazadas |
| Integración | Flujo completo con hardware simulado y 100 votantes sintéticos | pytest + CLI `votoseguro demo` | Verificador CONFORME |
| **Manipulación** | Alterar, borrar o insertar votos, alterar la bitácora, el acta o un archivo del USB, o volver la BD a una copia anterior | Scripts de ataque | 100 % detectado por el verificador |
| **Secreto del voto** | Intentar unir votante y voto a partir de la BD, la bitácora y el ledger | Análisis + script | No hay vínculo por debajo del anonimato de N |
| Escape del kiosco | Atajos de teclado, terminal, cierre de la ventana | Manual (lista de chequeo) | Sin escape |
| Modo degradado | Detener Fabric durante la votación | Script | Votación continua y sincronización completa |
| Rendimiento | Tiempo por votante, escrutinio de 500 votos, latencia de Fabric | Benchmark propio (Caliper opcional) | §13.4. Escrutinio de 500 votos < 30 s. |
| Biometría | FAR/FRR observados (p. ej. 20 personas × 5 intentos genuinos + intentos impostores) | Protocolo propio | Se reportan los valores y su intervalo |
| Usabilidad | Simulacro con personal de [EMPRESA] | Cuestionario SUS (≥ 10 usuarios) | SUS ≥ 68 |
| Estático y dependencias | Código y librerías | `bandit`, `pip-audit`, `gosec` | Sin hallazgos altos |

### 22.2 Calidad — ISO/IEC 25010

Se evalúan la adecuación funcional, la eficiencia de desempeño, la usabilidad, la fiabilidad, la seguridad (confidencialidad, integridad, no repudio, responsabilidad y autenticidad) y la mantenibilidad. Cada una tiene métricas y ponderaciones definidas en el capítulo de calidad.

### 22.3 Costos — COCOMO II

Puntos de función → SLOC (Python y Go) → esfuerzo y tiempo, más los costos de hardware y la comparación con el costo del proceso manual actual.

---

## 23. CONSIDERACIONES ÉTICAS, LEGALES Y DE PRIVACIDAD

| Aspecto | Medida |
|---|---|
| **Marco electoral** | Ley 018 (OEP) y Ley 026 (Régimen Electoral). El voto electrónico solo está previsto para bolivianos en el exterior (Art. 43.II de la Ley 026, modificado por la Ley 1066 de 2018). **Este sistema es para votaciones internas de una empresa u organización, no para elecciones públicas.** ⚠️ VERIFICAR si en [EMPRESA] interviene el OEP (por ejemplo, las cooperativas, según la Ley 356). |
| **Firma digital** | La Ley 164 (2011) y el DS 1793 (2013), Art. 34, reconocen validez jurídica a los documentos con firma digital vinculada a un certificado de una entidad certificadora (ADSIB y otras). En el prototipo, las firmas usan una PKI propia: tienen **valor técnico de integridad, no valor legal**. Como trabajo futuro, se puede firmar el acta con un certificado de ADSIB. |
| **Datos biométricos** | Bolivia **no tiene ley general de protección de datos personales**. Se aplican la CPE (Art. 21 y 130, acción de protección de privacidad) y buenas prácticas internacionales. ⚠️ VERIFICAR si hay normativa nueva al presentar el perfil. Medidas: consentimiento informado y escrito, plantillas (no imágenes) cifradas, nada biométrico en el ledger y **borrado seguro** de las plantillas al terminar el proceso o por solicitud. |
| **Inclusión** | Excepción manual para huellas ilegibles, botones grandes, alto contraste y confirmación explícita |
| **Transparencia** | Código abierto, zerésima pública y verificador disponible para los delegados |

---

## 24. CRONOGRAMA

| Sprint | Semanas | Entregable |
|---|---|---|
| 0 | 1 | Propuesta v5, ADR, repositorio y entorno |
| — | 1–2 | **Perfil de proyecto** para el tutor y carta de la empresa |
| 1 | 2 | Núcleo criptográfico, BD y bitácora, con pruebas |
| 2 | 2–3 | Servicios + CLI: elección completa simulada, acta, USB y verificador |
| 3 | 3 | Red Fabric, chaincode, puente Go, outbox |
| 4 | 3 | Interfaces PySide6 (kiosco, operador y auditor) |
| 5 | 2 | Hardware real (ZKTeco, impresora), kiosco `cage`, hardening |
| 6 | 2 | Pruebas, simulacro en [EMPRESA], SUS, FAR/FRR, ISO 25010, COCOMO II |
| — | 3–4 | Documento final y defensa |
| **Total** | **≈ 20–24 semanas** | |

---

## 25. PENDIENTES

| # | Pendiente | Prioridad |
|---|---|---|
| 1 | Definir **[EMPRESA]** y obtener la carta de aceptación | 🔴 Crítico |
| 2 | Entrevistar a la empresa: tipo de elecciones, número de votantes, problemas reales y costos actuales | 🔴 Crítico |
| 3 | Confirmar el formato del perfil y del documento con el tutor metodológico | 🔴 Crítico |
| 4 | Verificar las fuentes marcadas con ⚠️ | 🔴 Crítico |
| 5 | Comprar el ZKTeco (con SDK Linux) y la impresora térmica | 🟡 Importante |
| 6 | Revisar la RAM y el TPM del equipo de producción | 🟡 Importante |
| 7 | Instalar Go 1.25 o superior (lo exige `fabric-gateway` reciente; Debian 13 trae 1.24) | 🟡 Importante |

---

## 26. REFERENCIAS

- Churata Sonco, H. (2020). *Protocolos Blockchain aplicados a un sistema de votación electrónica*. Tesis de Grado TG-0059, Ingeniería de Sistemas, UPEA. https://repositorio.upea.bo/jspui/handle/123456789/119
- Ley N.º 026 del Régimen Electoral (2010), Art. 43, modificado por la Ley N.º 1066 (2018). https://web.oep.org.bo/wp-content/uploads/2019/07/LEY_026.pdf
- Ley N.º 018 del Órgano Electoral Plurinacional (2010).
- Ley N.º 164 General de Telecomunicaciones, TIC (2011) y DS N.º 1793 (2013), Reglamento. https://www.lexivox.org/norms/BO-RE-DSN1793.html
- ONPE. *Voto Electrónico Presencial*. https://www.onpe.gob.pe/modEducacion/voto-electronico/
- TSJE Paraguay. *Elecciones Municipales 2021 — Dossier informativo*. https://tsje.gov.py/elecciones-municipales-10-de-octubre-2021---dossier-informativo.html
- Hyperledger Fabric 2.5 documentation. https://hyperledger-fabric.readthedocs.io/en/release-2.5/
- Fabric Gateway client API. https://hyperledger.github.io/fabric-gateway/
- ZKTeco. *ZKFinger SDK for Linux*. https://www.zkteco.com/en/Biometrics_Module_SDK/ZKFinger-SDK-for-Linux
- Shamir, A. (1979). How to share a secret. *Communications of the ACM*, 22(11), 612–613.
- ISO/IEC 25010:2023. *Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*.
- Shostack, A. (2014). *Threat Modeling: Designing for Security*. Wiley (STRIDE).
- Ministerio de Hacienda y AA.PP. (España). *MAGERIT v3*.
- Brooke, J. (1996). SUS: A "quick and dirty" usability scale.

---

**Fin del documento — v5.0**
