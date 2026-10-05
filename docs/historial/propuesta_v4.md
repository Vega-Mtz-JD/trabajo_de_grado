# 📘 SISTEMA DE VOTACIÓN ELECTRÓNICA OFFLINE CON BLOCKCHAIN
## Documento de Propuesta — Versión 4.0

> **Estado:** En diseño / pre-implementación
> **Última actualización:** Octubre 2026
> **Autor:** Estudiante de Ingeniería de Sistemas — UPEA
> **Tutor Metodológico:** [Pendiente]
> **Especialista:** [Pendiente]
> **Directores de Empresa:** [Pendiente]
> **Repositorio:** [Pendiente — GitHub]
> **Licencia:** Apache 2.0 (heredada de Hyperledger Fabric)

---

## 📑 TABLA DE CONTENIDOS

1. [Título del Proyecto](#1-título-del-proyecto)
2. [Resumen Ejecutivo](#2-resumen-ejecutivo)
3. [Problema Identificado](#3-problema-identificado)
4. [Justificación](#4-justificación)
5. [Antecedentes](#5-antecedentes)
6. [Alcance y Proyección](#6-alcance-y-proyección)
7. [Arquitectura Física (Externa)](#7-arquitectura-física-externa)
8. [Arquitectura de Software (Interna)](#8-arquitectura-de-software-interna)
9. [Módulo Blockchain — Hyperledger Fabric Mononodo](#9-módulo-blockchain--hyperledger-fabric-mononodo)
10. [Fases del Proceso de Votación](#10-fases-del-proceso-de-votación)
11. [Flujo Completo de Votación](#11-flujo-completo-de-votación)
12. [Seguridad — Capas y Hardening](#12-seguridad--capas-y-hardening)
13. [Verificación Multinivel (Auditoría Triple)](#13-verificación-multinivel-auditoría-triple)
14. [Base de Datos](#14-base-de-datos)
15. [Stack Tecnológico](#15-stack-tecnológico)
16. [Hardware: PC/Laptop](#16-hardware-pclaptop)
17. [Manejo de Errores](#17-manejo-de-errores)
18. [Roles y Responsabilidades](#18-roles-y-responsabilidades)
19. [Alternativas Consideradas y Justificación](#19-alternativas-consideradas-y-justificación)
20. [Consideraciones Éticas y de Privacidad](#20-consideraciones-éticas-y-de-privacidad)
21. [Modelo de Sostenibilidad](#21-modelo-de-sostenibilidad)
22. [Plan de Pruebas](#22-plan-de-pruebas)
23. [Presupuesto](#23-presupuesto)
24. [Pendientes y Vacíos por Resolver](#24-pendientes-y-vacíos-por-resolver)
25. [Próximos Pasos](#25-próximos-pasos)
26. [Anexo — Instalación de Hyperledger Fabric en Debian 13](#26-anexo--instalación-de-hyperledger-fabric-en-debian-13)

---

## 1. TÍTULO DEL PROYECTO

### Título oficial (v4.0)
> **"Sistema de Votación Electrónica Offline con Blockchain para Auditoría y Verificación Multinivel de Resultados"**

### Análisis del título

| Componente | Qué aporta | ✅/❌ |
|------------|------------|------|
| **Sistema** | Sustantivo técnico principal | ✅ |
| **de Votación Electrónica** | Qué es | ✅ |
| **Offline** | Característica clave de seguridad | ✅ |
| **con Blockchain** | Tecnología emergente | ✅ |
| **para Auditoría** | Uso específico del blockchain | ✅ |
| **y Verificación Multinivel** | Triple auditoría | ✅ |
| **de Resultados** | Propósito | ✅ |

**Verificaciones:**
- ✅ Un solo sustantivo principal (Sistema)
- ✅ Sin verbos
- ✅ ≤ 30 palabras (16 palabras)
- ✅ Sin palabras prohibidas
- ✅ Sin "electorales" (abierto a cualquier tipo de votación)
- ✅ Sin "Prototipo" (suena a inacabado)

### Subtítulo
*"Autenticación biométrica (CI + huella dactilar), cifrado AES-256, firma digital RSA-2048, blockchain Hyperledger Fabric mononodo y auditoría triple (papel + USB + cadena de bloques)"*

### Nombre corto para feria
**"VOTO SEGURO: Blockchain para Elecciones Transparentes"**

---

## 2. RESUMEN EJECUTIVO

El proyecto consiste en el **diseño e implementación de un sistema de votación electrónica** que permite emitir el voto de forma **biométrica, cifrada y auditable**, operando **100% offline** durante todo el proceso (sin internet, sin Bluetooth, sin Wi-Fi) y utilizando **Hyperledger Fabric en modo mononodo** para el registro inmutable de actas y la verificación multinivel de resultados.

### Características principales

| Característica | Descripción |
|----------------|-------------|
| **Autenticación** | CI + huella dactilar (validación 1:1) |
| **Votación** | Monitor + mouse (o teclado) |
| **Comprobante** | VVPAT impreso que cae en caja sellada |
| **Almacenamiento** | Cifrado AES-256 |
| **Acta de cierre** | Firmada digitalmente con RSA-2048 |
| **Blockchain** | Hyperledger Fabric mononodo (1 CA + 1 orderer + 1 peer) |
| **Auditoría** | Triple: papel (VVPAT) + USB cifrado + blockchain local |
| **Sistema operativo** | Debian 13 Trixie |
| **Licencia** | Código abierto (Apache 2.0) |
| **Hardware** | PC o laptop (sin Raspberry Pi) |

### Filosofía del proyecto

1. **Offline por diseño:** Todo el proceso ocurre sin conexión. Se eliminan vectores de ataque remotos.
2. **Blockchain local:** Registro inmutable de actas y eventos, con encadenamiento de bloques.
3. **Código abierto:** Auditoría independiente, reducción de costos, confianza institucional.
4. **Auditable:** Triple verificación (VVPAT + USB + blockchain).
5. **Profesional:** Hyperledger Fabric, estándar empresarial para blockchain permisionado.

### Escalabilidad

El sistema está diseñado para **una sola máquina**. Si la institución desea usarlo en varias mesas, cada equipo es **independiente** (con su propio padrón, votaciones y blockchain local). La verificación final se realiza comparando los resultados de cada equipo de forma manual o externa.

---

## 3. PROBLEMA IDENTIFICADO

### Situación actual

Las votaciones en empresas, instituciones y universidades bolivianas suelen realizarse con **papeletas físicas o sistemas rudimentarios**, lo que presenta:

| Aspecto | Situación actual |
|---------|------------------|
| **Costos** | Altos costos de impresión, distribución y conteo manual |
| **Trazabilidad** | Limitada: el conteo manual es propenso a errores humanos |
| **Velocidad** | El conteo manual tarda horas o días |
| **Seguridad** | Sin mecanismos criptográficos de verificación |
| **Auditoría** | Sin registro inmutable de resultados |
| **Confianza** | Desconfianza en resultados por falta de transparencia |

### Problema principal (redactado en positivo)

> **"Las instituciones y empresas bolivianas requieren modernizar sus mecanismos de votación, conteo y auditoría para reducir costos, eliminar errores humanos y fortalecer la transparencia, mediante la incorporación de tecnología electoral verificable y blockchain."**

### Problemas secundarios (máx. 5, causa-efecto)

| # | Problema secundario | Causa | Efecto |
|---|---------------------|-------|--------|
| 1 | Altos costos logísticos | Impresión y distribución de papeletas | Gasto institucional elevado |
| 2 | Conteo manual lento | Procesamiento humano de votos | Resultados tardíos |
| 3 | Errores humanos en conteo | Fatiga, mala iluminación, etc. | Resultados impugnables |
| 4 | Falta de trazabilidad | Sin registro digital verificable | Dificultad para auditar |
| 5 | Riesgo de manipulación | Sin mecanismos criptográficos | Desconfianza en resultados |

### Formulación en pregunta

> **"¿Cómo diseñar e implementar un sistema de votación electrónica offline con blockchain Hyperledger Fabric mononodo que garantice autenticación biométrica, registro inmutable de actas y verificación multinivel para procesos de votación institucionales auditables?"**

---

## 4. JUSTIFICACIÓN

### 4.1 Justificación Técnica

| Aspecto | Justificación |
|---------|---------------|
| **Viabilidad** | Hardware accesible (PC o laptop existente) |
| **Software** | Linux (Debian 13) + Python + Hyperledger Fabric + Docker |
| **Portabilidad** | El sistema funciona en cualquier máquina con Linux |
| **Blockchain** | Hyperledger Fabric es el estándar empresarial para redes permisionadas |
| **Offline** | No requiere conexión a internet, eliminando ataques remotos |

### 4.2 Justificación Económica

| Aspecto | Justificación |
|---------|---------------|
| **Reducción de costos** | Menos papeletas, menos logística, menos personal de conteo |
| **Inversión inicial** | Baja (~$150-$250 USD en periféricos, si la PC ya existe) |
| **Retorno** | A largo plazo, ahorro significativo vs. sistema actual |
| **Código abierto** | Sin costos de licencias |

### 4.3 Justificación Social

| Aspecto | Justificación |
|---------|---------------|
| **Transparencia** | Auditoría triple + blockchain + VVPAT |
| **Confianza** | El votante ve su comprobante impreso |
| **Inclusión** | Diseño accesible (monitor + mouse o teclado) |

### 4.4 Justificación Académica

| Aspecto | Justificación |
|---------|---------------|
| **Aporte UPEA** | Primer sistema de votación con blockchain de la carrera |
| **Publicación** | Posible paper en congreso o revista |
| **Transferencia** | Base para futuras tesis |

---

## 5. ANTECEDENTES

### 5.1 Antecedentes Internacionales (mín. 2)

#### 🇧🇷 Brasil (urnas electrónicas desde 1996)

| Aspecto | Detalle |
|---------|---------|
| **Sistema** | Urna Eletrônica Brasileira |
| **Características** | Offline total, sin internet, Bluetooth ni Wi-Fi |
| **Auditoría** | Boletín de urna impreso, conteo comienza en la mesa |
| **Seguridad** | Firma digital de cada archivo de resultado |
| **Energía** | Batería interna para 10 horas sin electricidad |
| **SO** | Linux (Uenux) |

**Adoptamos:** Boletín de urna impreso + verificación de firma digital + Linux.

#### 🇮🇳 India (EVM + VVPAT desde 2013)

| Aspecto | Detalle |
|---------|---------|
| **Sistema** | Electronic Voting Machine (EVM) + VVPAT |
| **VVPAT** | Muestra nombre y símbolo del candidato por 7 segundos |
| **Seguridad** | Doble aleatorización de máquinas, mock poll obligatorio |
| **Trazabilidad** | GPS tracking del traslado, Form 17C firmado |

**Adoptamos:** Mock poll + formulario de cierre firmado + VVPAT.

#### 🇵🇹 Portugal (investigación en blockchain para votación)

| Aspecto | Detalle |
|---------|---------|
| **Sistema** | Hyperledger Fabric para sistema electoral portugués |
| **Características** | Red permisionada, privacidad del votante, integridad del voto |
| **Blockchain** | Hyperledger Fabric con smart contracts |
| **Aportes** | Automatización y seguridad de procedimientos de votación |

**Adoptamos:** Hyperledger Fabric como framework blockchain + smart contracts.

#### 🇲🇾 Malasia (investigación en escalabilidad de blockchain para votación)

| Aspecto | Detalle |
|---------|---------|
| **Sistema** | Arquitectura blockchain permisionada para votación en línea |
| **Blockchain** | Hyperledger Fabric con red de hasta 5 peers |
| **Pruebas** | Hyperledger Caliper para métricas de rendimiento |
| **Resultados** | Red de 5 peers es óptima para votación en línea |

**Adoptamos:** Hyperledger Caliper para pruebas de rendimiento.

### 5.2 Antecedentes Nacionales (mín. 2) — 🔴 PENDIENTE

| # | Antecedente | Estado |
|---|-------------|--------|
| 1 | Experiencias de voto electrónico en universidades bolivianas | ❌ Por investigar |
| 2 | Pruebas del TSE con voto electrónico | ❌ Por investigar |
| 3 | Proyectos de la UPEA relacionados | ❌ Por investigar |
| 4 | Legislación boliviana sobre voto electrónico | ⚠️ Parcial (verificar) |

### 5.3 Antecedentes de Código Abierto

| Proyecto | País | Características |
|----------|------|-----------------|
| **VotingWorks** | EE.UU. | Basado en Debian, open source |
| **Uenux** | Brasil | Sistema de urnas brasileñas, Linux |
| **Hyperledger Fabric** | Linux Foundation | Framework blockchain permisionado |

---

## 6. ALCANCE Y PROYECCIÓN

### 6.1 Alcance del sistema (honesto y realista)

| Aspecto | Alcance |
|---------|---------|
| **Equipos** | 1 equipo (PC o laptop) |
| **Padrón** | 100 electores de prueba |
| **Autenticación** | CI + huella dactilar (lector real o simulado) |
| **Votación** | Monitor + mouse (o teclado) |
| **Comprobante** | VVPAT impreso |
| **Cierre** | Acta firmada digitalmente |
| **Blockchain** | Hyperledger Fabric mononodo (1 CA + 1 orderer + 1 peer) |
| **Auditoría** | Triple: papel + USB + blockchain |
| **SO** | Debian 13 Trixie |
| **Hardware** | PC o laptop de la empresa |

### 6.2 Proyección de escalabilidad

| Nivel | Contexto | Equipos | Votantes | Notas |
|-------|----------|---------|----------|-------|
| 1 | Empresa o institución pequeña | 1 | 500 | Sistema completo en un equipo |
| 2 | Universidad o institución mediana | N | 10,000 | Cada equipo independiente |
| 3 | Municipal | N | 100,000 | Proyección documentada |
| 4 | Nacional | N | 7,000,000 | Proyección documentada |

**Nota:** Si se usan varios equipos, cada uno es independiente y tiene su propio padrón, votaciones y blockchain local. La consolidación final se hace manualmente o con un sistema externo.

### 6.3 Lo que el proyecto NO hace

- ❌ No reemplaza el sistema electoral boliviano
- ❌ No es un sistema de producción certificado
- ❌ No resuelve el problema del padrón biométrico nacional
- ❌ No garantiza el 100% de seguridad (ningún sistema lo hace)
- ❌ No usa Raspberry Pi (descartado por completo)

---

## 7. ARQUITECTURA FÍSICA (EXTERNA)

### 7.1 Diagrama de la mesa de votación

```
┌─────────────────────────────────────────────────────────────┐
│                    MESA DE VOTACIÓN                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   MONITOR    │    │   MOUSE      │    │  IMPRESORA   │  │
│  │   HDMI/VGA   │    │   USB        │    │   VVPAT      │  │
│  │              │    │              │    │   (USB)      │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│                    ┌────────┴────────┐                     │
│                    │   PC / LAPTOP   │                     │
│                    │                 │                     │
│                    │  - CPU          │                     │
│                    │  - RAM          │                     │
│                    │  - Almacenamiento│                    │
│                    │  - TPM 2.0      │                     │
│                    │  - Docker       │                     │
│                    └────────┬────────┘                     │
│                             │                              │
│                    ┌────────┴────────┐                     │
│                    │   UPS / BATERÍA │                     │
│                    │   (respaldo)    │                     │
│                    └─────────────────┘                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           CAJA SELLADA (VVPAT)                      │   │
│  │  - Comprobantes impresos                            │   │
│  │  - Acceso restringido                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Componentes físicos

| Componente | Función | Conexión |
|------------|---------|----------|
| **CPU** | Procesamiento | PC o laptop de la empresa |
| **Monitor** | Interfaz de votación | HDMI/VGA |
| **Mouse** | Entrada del votante | USB |
| **Teclado** | Entrada del operador | USB |
| **Lector de huella** | Autenticación biométrica | USB |
| **Impresora térmica** | Comprobante VVPAT | USB |
| **UPS/Batería** | Respaldo de energía | Conexión directa |
| **TPM 2.0** | Almacenamiento seguro de claves | Interno o USB |
| **Caja sellada** | Depósito de VVPAT | Física |

### 7.3 Diagrama de contexto propuesto

```
┌─────────────────────────────────────────────────────────────┐
│                  SISTEMA DE VOTACIÓN                        │
│                                                             │
│  ┌─────────────┐                                           │
│  │   VOTANTE   │──────┐                                    │
│  └─────────────┘      │                                    │
│                       │                                    │
│  ┌─────────────┐      │      ┌──────────────────────┐     │
│  │  OPERADOR   │──────┼─────▶│   PC / LAPTOP        │     │
│  │  DE MESA    │      │      │                      │     │
│  └─────────────┘      │      │  - Empadronamiento   │     │
│                       │      │  - Autenticación     │     │
│  ┌─────────────┐      │      │  - Votación          │     │
│  │  AUDITOR    │──────┘      │  - VVPAT             │     │
│  └─────────────┘             │  - Cifrado           │     │
│                              │  - Blockchain local  │     │
│                              └──────────┬───────────┘     │
│                                         │                  │
│                                         ▼                  │
│                              ┌──────────────────────┐     │
│                              │   SALIDAS            │     │
│                              │  - VVPAT (papel)     │     │
│                              │  - USB cifrado       │     │
│                              │  - Blockchain local  │     │
│                              └──────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. ARQUITECTURA DE SOFTWARE (INTERNA)

### 8.1 Capas del sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                     │
│  - Interfaz para votante (monitor + mouse)                  │
│  - Interfaz para operador de mesa                           │
│  - Interfaz para auditor                                     │
│  - Modo kiosco (sin acceso al escritorio)                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA DE NEGOCIO                │
│  - Gestión de empadronamiento                               │
│  - Gestión de autenticación                                 │
│  - Gestión de votación                                      │
│  - Gestión de cierre                                        │
│  - Gestión de auditoría                                     │
│  - Cliente blockchain (Fabric SDK)                          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE SEGURIDAD                        │
│  - Cifrado AES-256                                          │
│  - Firma digital RSA-2048                                   │
│  - Hash SHA-3                                               │
│  - Gestión de claves (TPM)                                  │
│  - Hardening de Debian (CIS Level 1)                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                            │
│  - Base de datos cifrada (SQLite + SQLCipher)               │
│  - Logs de auditoría (append-only)                          │
│  - Actas firmadas                                           │
│  - Exportación a USB                                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE BLOCKCHAIN                       │
│  - Hyperledger Fabric mononodo                              │
│  - CA, Orderer, Peer (Docker)                               │
│  - Chaincode (Go o JavaScript)                              │
│  - CouchDB (estado del ledger)                              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE HARDWARE                         │
│  - PC o laptop                                              │
│  - Lector de huella                                         │
│  - Impresora térmica                                        │
│  - Monitor + mouse + teclado                                │
│  - UPS                                                      │
│  - TPM 2.0                                                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Módulos del sistema

| Módulo | Función | Tecnología |
|--------|---------|------------|
| **Empadronamiento** | Registrar votantes | Python + SQLCipher |
| **Autenticación** | Validar CI + huella | Python + libfprint |
| **Votación** | Interfaz de selección | Python + PyQt6/PySide6 |
| **VVPAT** | Generar comprobante | Python + python-escpos |
| **Cifrado** | Proteger datos | AES-256 + RSA-2048 |
| **Auditoría** | Registrar eventos | Logs + SQLite |
| **Blockchain** | Registro inmutable | Hyperledger Fabric SDK Python |
| **Cierre** | Acta digital | RSA-2048 + SHA-3 |
| **Exportación** | USB cifrado | AES-256 |

### 8.3 Modo kiosco (sin acceso al escritorio)

El sistema arranca directamente en la aplicación de votación. El votante no puede:

- Cerrar la aplicación
- Acceder al escritorio
- Abrir terminal
- Modificar archivos

Para lograrlo:
1. La aplicación se inicia automáticamente en el arranque del entorno gráfico.
2. Se deshabilitan los atajos de teclado (Alt+F4, Ctrl+Alt+T, etc.).
3. Se puede usar `unclutter` para ocultar el cursor del mouse después de un tiempo de inactividad.
4. Se implementa un botón de cierre que solicita contraseña (con bloqueo de 5 minutos tras 3 intentos fallidos).

---

## 9. MÓDULO BLOCKCHAIN — HYPERLEDGER FABRIC MONONODO

### 9.1 ¿Por qué Hyperledger Fabric?

| Criterio | Hyperledger Fabric | Hyperledger Besu |
|----------|-------------------|------------------|
| **Origen** | Creado para empresas | Cliente de Ethereum |
| **Consenso** | Modular (Raft) | Proof of Authority (PoA) |
| **Smart Contracts** | Chaincode en Go, JavaScript, Java | Solidity |
| **Privacidad** | Alta: canales privados | Media |
| **Control de acceso** | Granular (X.509, MSP, RBAC) | Menos granular |
| **Ideal para** | **Votación, gobierno, empresas** | Finanzas, Ethereum |
| **Complejidad** | Media-alta | Media |
| **Rendimiento** | Alto, optimizado | Alto |

**Hyperledger Fabric es la mejor opción para votación** porque:
1. **Privacidad granular:** Canales separados por nivel.
2. **Control de acceso por identidades:** Cada nodo tiene certificado X.509.
3. **Sin criptomonedas:** Red permisionada, sin minado, sin gas.
4. **Modularidad:** Consenso adaptable.
5. **Cumplimiento normativo:** Facilita protección de datos.

### 9.2 Arquitectura mononodo

```
┌─────────────────────────────────────────────────────────────┐
│              HYPERLEDGER FABRIC MONONODO                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              CONTENEDOR DOCKER 1                    │   │
│  │         Certificate Authority (CA)                  │   │
│  │  - Emite certificados X.509                         │   │
│  │  - Gestiona identidades                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              CONTENEDOR DOCKER 2                    │   │
│  │         Ordering Service (Orderer)                  │   │
│  │  - Ordena transacciones                             │   │
│  │  - Crea bloques                                     │   │
│  │  - Consenso Raft                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              CONTENEDOR DOCKER 3                    │   │
│  │         Peer Node                                   │   │
│  │  - Mantiene el ledger                               │   │
│  │  - Ejecuta chaincode                                │   │
│  │  - Valida transacciones                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              CONTENEDOR DOCKER 4                    │   │
│  │         CouchDB (State Database)                    │   │
│  │  - Almacena el estado actual del ledger             │   │
│  │  - Permite consultas ricas                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SDK Python
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              APLICACIÓN PYTHON (VOTACIÓN)                   │
│  - Interfaz gráfica (PyQt6/PySide6)                         │
│  - Autenticación biométrica                                 │
│  - Cifrado AES-256 / RSA-2048                               │
│  - Impresión VVPAT                                          │
│  - Lógica de votación                                       │
│  - Cliente Fabric (fabric-sdk-py)                           │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Flujo de datos

```
1. VOTANTE VOTA
   ↓
2. APLICACIÓN PYTHON
   - Cifra el voto (AES-256)
   - Genera hash (SHA-3)
   - Firma el acta (RSA-2048)
   ↓
3. SDK FABRIC (Python)
   - Envía transacción al peer
   ↓
4. PEER
   - Valida la transacción
   - Ejecuta el chaincode
   ↓
5. ORDERER
   - Ordena la transacción
   - Crea un bloque
   ↓
6. PEER (nuevamente)
   - Añade el bloque al ledger
   ↓
7. COUCHDB
   - Actualiza el estado
   ↓
8. AUDITORÍA
   - Verifica la cadena de bloques
```

### 9.4 Nodos y roles (mononodo)

| Componente | Rol | Dónde corre |
|------------|-----|-------------|
| **CA** | Emite certificados | Contenedor Docker |
| **Orderer** | Ordena transacciones | Contenedor Docker |
| **Peer** | Mantiene ledger | Contenedor Docker |
| **CouchDB** | Estado del ledger | Contenedor Docker |

### 9.5 Stack blockchain

| Componente | Tecnología | Justificación |
|------------|------------|---------------|
| **Framework** | Hyperledger Fabric 2.5+ | Estándar empresarial |
| **Chaincode** | Go o JavaScript | Rendimiento |
| **SDK cliente** | Python (fabric-sdk-py) | Coherente con el sistema |
| **Consenso** | Raft | Eficiente, tolerante a fallos |
| **Base de datos** | CouchDB | Consultas ricas, historial |
| **Contenedores** | Docker + Docker Compose | Obligatorio para Fabric |

---

## 10. FASES DEL PROCESO DE VOTACIÓN

| Fase | Descripción | Responsable |
|------|-------------|-------------|
| **1. Configuración** | Cargar candidatos, padrón inicial | Administrador |
| **2. Empadronamiento** | Registrar votantes (CI + huella) | Operador |
| **3. Apertura** | Iniciar votación | Operador de mesa |
| **4. Autenticación** | Validar CI + huella | Sistema |
| **5. Votación** | Seleccionar candidato | Votante |
| **6. VVPAT** | Imprimir comprobante | Sistema |
| **7. Cifrado** | Cifrar voto (AES-256) | Sistema |
| **8. Blockchain** | Registrar evento en ledger | Sistema |
| **9. Cierre** | Finalizar votación | Operador de mesa |
| **10. Acta** | Firmar digitalmente (RSA-2048) | Operador + auditor |
| **11. Exportación** | Copiar a USB cifrado | Operador |
| **12. Auditoría** | Verificar VVPAT + USB + blockchain | Auditor |

---

## 11. FLUJO COMPLETO DE VOTACIÓN

### 11.1 Diagrama de flujo

```
┌─────────────┐
│   INICIO    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ FASE 1: EMPADRONAMIENTO │
│ - Registrar votantes  │
│ - Capturar huella     │
│ - Guardar en BD       │
│ - Generar bloque génesis │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ FASE 2: APERTURA    │
│ - Operador inicia   │
│ - Verifica hardware │
│ - Carga candidatos  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Votante se acerca    │
│ - Presenta CI        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Autenticación        │
│ - Escanea CI         │
│ - Escanea huella     │
│ - Valida 1:1         │
└──────┬──────────────┘
       │
       ├─── ❌ FALLA ───▶ ┌─────────────────────┐
       │                  │ Reintentar (máx. 3)  │
       │                  └──────────┬──────────┘
       │                             │
       │                             ▼
       │                  ┌─────────────────────┐
       │                  │ Registrar intento    │
       │                  │ fallido (auditoría)  │
       │                  └─────────────────────┘
       │
       ▼ ✅ ÉXITO
┌─────────────────────┐
│ Habilitar votación   │
│ - Monitor + mouse    │
│ - Mostrar candidatos │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Votante selecciona   │
│ - Confirma voto      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Generar VVPAT        │
│ - Imprimir           │
│ - Mostrar al votante │
│ - Caer en caja       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Cifrar voto          │
│ - AES-256            │
│ - Guardar en BD      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Registrar en Blockchain │
│ - Enviar transacción │
│ - Peer valida        │
│ - Orderer ordena     │
│ - Bloque creado      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ¿Más votantes?       │
└──────┬──────────────┘
       │
       ├─── SÍ ───▶ (volver a "Votante se acerca")
       │
       ▼ NO
┌─────────────────────┐
│ FASE 3: CIERRE      │
│ - Operador cierra   │
│ - Generar acta      │
│ - Firmar RSA-2048   │
│ - Hash SHA-3        │
│ - Bloque de cierre  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Exportar a USB       │
│ - Datos cifrados     │
│ - Logs               │
│ - Acta               │
│ - Cadena de bloques  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Auditoría Multinivel │
│ - VVPAT (papel)      │
│ - USB cifrado        │
│ - Blockchain local   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   FIN                │
└─────────────────────┘
```

### 11.2 Tiempos estimados

| Fase | Tiempo estimado |
|------|-----------------|
| Autenticación | 10-15 segundos |
| Votación | 30-60 segundos |
| VVPAT | 5-10 segundos |
| Cifrado | < 1 segundo |
| Blockchain | 1-2 segundos |
| **Total por votante** | **~1-2 minutos** |

---

## 12. SEGURIDAD — CAPAS Y HARDENING

### 12.1 Las capas de seguridad

| Capa | Nombre | Descripción | Tecnología |
|------|--------|-------------|------------|
| **1** | **Física** | Protección del hardware | Caja sellada, carcasa, TPM |
| **2** | **Autenticación** | Validar identidad | CI + huella dactilar |
| **3** | **Cifrado** | Proteger datos | AES-256 |
| **4** | **Firma digital** | Garantizar integridad | RSA-2048 + SHA-3 |
| **5** | **Auditoría** | Registrar y verificar | Logs + VVPAT + blockchain |
| **6** | **Hardening** | Endurecer SO | CIS Level 1, ANSSI-BP-028 |

### 12.2 Hardening de Debian 13 Trixie

| Medida | Comando/Acción |
|--------|----------------|
| **Actualizar sistema** | `sudo apt update && sudo apt upgrade -y` |
| **Crear usuario no-root** | `sudo adduser usuario` |
| **Deshabilitar root SSH** | `PermitRootLogin no` en `/etc/ssh/sshd_config` |
| **Usar claves SSH (Ed25519)** | `ssh-keygen -t ed25519` |
| **Deshabilitar login por contraseña** | `PasswordAuthentication no` |
| **Firewall (UFW)** | `sudo apt install ufw && sudo ufw enable` |
| **Fail2ban** | `sudo apt install fail2ban` |
| **Deshabilitar Bluetooth/Wi-Fi** | `sudo systemctl disable bluetooth` |
| **Servicios innecesarios** | `sudo systemctl disable <servicio>` |
| **AppArmor** | `sudo apt install apparmor apparmor-profiles` |
| **Actualizaciones automáticas** | `sudo apt install unattended-upgrades` |

**Referencia:** Guía de hardening para Debian 13 disponible en GitHub.

### 12.3 Threat Model (STRIDE)

| Amenaza | Descripción | Mitigación |
|---------|-------------|------------|
| **Spoofing** | Alguien se hace pasar por otro | Autenticación biométrica 1:1 |
| **Tampering** | Modificar software o datos | Firma digital, hash, TPM |
| **Repudiation** | Negar haber votado | VVPAT + logs firmados |
| **Information Disclosure** | Filtrar información | Cifrado AES-256 |
| **Denial of Service** | Bloquear el sistema | UPS, modo offline |
| **Elevation of Privilege** | Obtener permisos | Linux hardened, mínimo privilegio |

### 12.4 Amenazas específicas del contexto boliviano

| Amenaza | Descripción | Mitigación |
|---------|-------------|------------|
| **Suplantación de identidad** | Votar por otro | Biometría 1:1 |
| **Compra de votos** | Pagar por votos | Voto secreto, VVPAT |
| **Voto múltiple** | Votar varias veces | Padrón único en el equipo |
| **Manipulación del USB** | Alterar resultados | Cifrado + firma digital |
| **Acceso físico** | Robar o modificar el equipo | Caja sellada + TPM |
| **Corte de energía** | Interrumpir votación | UPS + batería |
| **Ingeniería social** | Convencer al operador | Capacitación + protocolos |

---

## 13. VERIFICACIÓN MULTINIVEL (AUDITORÍA TRIPLE)

### 13.1 Los 3 niveles de auditoría

| Nivel | Nombre | Descripción | Verificación |
|-------|--------|-------------|--------------|
| **1** | **Papel (VVPAT)** | Comprobante impreso | Visual, manual |
| **2** | **USB cifrado** | Respaldo digital | Digital, con firma |
| **3** | **Blockchain** | Cadena de bloques local | Digital, con hash |

### 13.2 Nivel 1: VVPAT (Papel)

| Aspecto | Detalle |
|---------|---------|
| **Función** | Comprobante físico que ve el votante |
| **Contenido** | Nombre del candidato, símbolo, fecha, hora |
| **Duración** | Visible por 7 segundos |
| **Destino** | Caja sellada |
| **Auditoría** | Conteo manual vs. digital |

### 13.3 Nivel 2: USB cifrado

| Aspecto | Detalle |
|---------|---------|
| **Función** | Respaldo digital para transporte |
| **Contenido** | Votos cifrados, logs, acta, cadena de bloques |
| **Cifrado** | AES-256 |
| **Firma** | RSA-2048 |
| **Verificación** | Con clave pública |

### 13.4 Nivel 3: Blockchain (Hyperledger Fabric)

| Aspecto | Detalle |
|---------|---------|
| **Función** | Registro inmutable de resultados |
| **Contenido** | Bloques con hash, actas, firmas |
| **Integridad** | Hash SHA-3 + encadenamiento |
| **Acceso** | Nodos autorizados (auditores) |
| **Verificación** | Recalculo de hashes + comparación con USB y VVPAT |

### 13.5 Proceso de verificación

```
1. Al cierre de votación:
   - VVPAT va a caja sellada
   - USB se cifra y firma
   - Acta se hashea (SHA-3)
   - Bloque de cierre se encadena

2. En la auditoría:
   - Se descifra USB
   - Se verifica firma RSA
   - Se verifica la cadena de bloques
   - Se compara con VVPAT

3. Resultado:
   - Si los 3 coinciden: OK
   - Si no: investigar
```

### 13.6 Ventajas de la verificación multinivel

| Ventaja | Descripción |
|---------|-------------|
| **Transparencia** | Cualquiera puede verificar |
| **Redundancia** | Si falla un nivel, quedan otros |
| **Confianza** | Múltiples fuentes de verdad |
| **Auditabilidad** | Trazabilidad completa |
| **Inmutabilidad** | Blockchain no permite alteraciones |

---

## 14. BASE DE DATOS

### 14.1 Esquema de la base de datos

```sql
-- Tabla: candidatos
CREATE TABLE candidatos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    partido TEXT,
    simbolo TEXT,
    orden INTEGER
);

-- Tabla: votantes (padrón)
CREATE TABLE votantes (
    ci TEXT PRIMARY KEY,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    huella_hash TEXT,
    habilitado BOOLEAN DEFAULT TRUE,
    ya_voto BOOLEAN DEFAULT FALSE,
    timestamp_voto DATETIME
);

-- Tabla: votos (cifrados)
CREATE TABLE votos (
    id INTEGER PRIMARY KEY,
    voto_cifrado BLOB NOT NULL,
    hash_voto TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: auditoría (logs append-only)
CREATE TABLE auditoria (
    id INTEGER PRIMARY KEY,
    evento TEXT NOT NULL,
    descripcion TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario TEXT
);

-- Tabla: actas
CREATE TABLE actas (
    id INTEGER PRIMARY KEY,
    total_votantes INTEGER,
    total_votos INTEGER,
    firma_digital BLOB,
    hash_acta TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: bloques blockchain (local)
CREATE TABLE bloques (
    id INTEGER PRIMARY KEY,
    hash_anterior TEXT,
    hash_actual TEXT NOT NULL,
    acta_hash TEXT NOT NULL,
    firma_operador BLOB,
    firma_auditor BLOB,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 14.2 Seguridad de la base de datos

| Aspecto | Medida |
|---------|--------|
| **Cifrado** | SQLCipher (AES-256) |
| **Acceso** | Solo usuario del sistema |
| **Backup** | USB cifrado |
| **Integridad** | Hash SHA-3 por registro |
| **Logs** | Append-only (solo agregar) |

---

## 15. STACK TECNOLÓGICO

### 15.1 Sistema Operativo

| Máquina | SO | Entorno |
|---------|-----|---------|
| **HP ProBook (desarrollo)** | Debian 13 Trixie | GNOME |
| **Equipo de la empresa (producción)** | Debian 13 Trixie | GNOME o XFCE |

### 15.2 Lenguajes y Frameworks

| Componente | Tecnología | Justificación |
|------------|------------|---------------|
| **Lenguaje principal** | Python 3.13+ | Fácil, librerías, SDK Fabric |
| **IDE** | PyCharm Community | Especializado en Python, profesional |
| **Interfaz gráfica** | PyQt6 o PySide6 | Nativo en Linux, profesional |
| **Base de datos** | SQLite + SQLCipher | Ligero, cifrado |
| **Blockchain** | Hyperledger Fabric 2.5+ | Estándar empresarial |
| **SDK Fabric** | fabric-sdk-py | Python SDK para Fabric |
| **Biometría** | libfprint | Open source |
| **Impresión** | python-escpos | Estándar para térmicas |
| **Cifrado** | cryptography (Python) | AES-256, RSA-2048 |
| **Hash** | hashlib (SHA-3) | Integridad |
| **Contenedores** | Docker + Docker Compose | Obligatorio para Fabric |
| **Empaquetado** | PyInstaller o .deb | Distribución |

### 15.3 Herramientas de desarrollo

| Herramienta | Uso |
|-------------|-----|
| **PyCharm** | IDE principal |
| **Git + GitHub** | Control de versiones |
| **Docker** | Contenedores Fabric |
| **pytest** | Pruebas unitarias |
| **Hyperledger Caliper** | Pruebas de rendimiento blockchain |
| **Sphinx** | Documentación |

### 15.4 Dependencias del sistema

```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip python3-venv \
    libfprint-2-2 fprintd libsqlcipher0 \
    libusb-1.0-0 cups \
    docker.io docker-compose \
    build-essential git curl
```

---

## 16. HARDWARE: PC/LAPTOP

### 16.1 Opciones de CPU

| Opción | Precio | Ventajas | Desventajas |
|--------|--------|----------|-------------|
| **PC de escritorio** | Ya disponible | Potente, ampliable | Ocupa espacio |
| **Laptop** | Ya disponible | Portátil, todo en uno | Menos ampliable |
| **Mini PC** | ~$150-$300 | Compacto, bajo consumo | Menos potente |
| **HP ProBook 650 G1** | Ya disponible | Potente, para desarrollo | No para producción |

**Recomendación:** HP ProBook para desarrollo. Equipo de la empresa (PC o laptop) para producción.

### 16.2 Componentes

| Componente | Modelo sugerido | Precio estimado |
|------------|-----------------|-----------------|
| **CPU** | PC o laptop de la empresa | Ya disponible |
| **Lector de huella** | FPM10A o Waveshare capacitivo | $20-$30 |
| **Monitor** | Cualquier monitor HDMI/VGA | $60-$100 |
| **Mouse** | USB básico | $5-$10 |
| **Teclado** | USB básico | $10-$15 |
| **Impresora térmica** | Adafruit o SparkFun (ESC/POS) | $50-$70 |
| **TPM 2.0** | Módulo interno o USB | $15-$25 |
| **UPS** | Para PC o laptop | $25-$40 |
| **Cables y conectores** | Varios | $10-$20 |
| **TOTAL** | | **$195-$310** |

### 16.3 Presupuesto total

| Escenario | Costo |
|-----------|-------|
| **Mínimo** | ~$150 (usando alternativas) |
| **Recomendado** | ~$250 (con periféricos) |
| **Completo** | ~$350 (con todo y repuestos) |

---

## 17. MANEJO DE ERRORES

### 17.1 Tipos de errores

| Error | Causa | Mitigación |
|-------|-------|------------|
| **Fallo de autenticación** | Huella no reconocida | Reintentar (máx. 3) |
| **Fallo de impresora** | Sin papel, sin tinta | Alerta, reintentar |
| **Fallo de energía** | Corte eléctrico | UPS, batería |
| **Fallo de BD** | Corrupción | Backup, recuperación |
| **Fallo de USB** | No detectado | Reintentar, USB de respaldo |
| **Fallo de Docker** | Contenedor caído | Reiniciar contenedor |
| **Fallo de Fabric** | Peer/orderer caído | Reiniciar red |

### 17.2 Protocolo de errores

```
1. Detectar error
2. Registrar en log de auditoría
3. Mostrar mensaje al operador
4. Aplicar mitigación
5. Si persiste: detener sistema
6. Notificar a soporte técnico
```

### 17.3 Modos de operación

| Modo | Descripción |
|------|-------------|
| **Normal** | Todo funciona |
| **Degradado** | Blockchain no disponible, votación continúa offline |
| **Emergencia** | Solo votación, sin VVPAT |
| **Detenido** | Sistema no operativo |

---

## 18. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidad |
|-----|-----------------|
| **Administrador** | Configurar sistema, cargar datos |
| **Operador de mesa** | Iniciar/cerrar votación, asistir votantes |
| **Votante** | Emitir voto |
| **Auditor** | Verificar VVPAT, USB, blockchain |
| **Custodio** | Transportar USB |
| **Soporte técnico** | Resolver fallos |
| **Desarrollador** | Mantener software |

---

## 19. ALTERNATIVAS CONSIDERADAS Y JUSTIFICACIÓN

| Alternativa | Ventajas | Desventajas | ¿Por qué no? |
|-------------|----------|-------------|--------------|
| **Papeleta física actual** | Transparente, simple, confiable | Lenta, costosa, errores humanos | Es el statu quo |
| **Escaneo óptico** | Rápido, auditable | Costoso, requiere infraestructura | No elimina papeleta |
| **Voto por internet** | Cómodo | Inseguro, brecha digital, no auditable | Riesgo alto |
| **Blockchain público (Ethereum)** | Transparente, descentralizado | Lento, costoso, requiere criptomonedas | No aplica |
| **Hyperledger Fabric (propuesta)** | Rápido, seguro, permisionado, sin costos | Complejidad media-alta | **Es la propuesta** |

---

## 20. CONSIDERACIONES ÉTICAS Y DE PRIVACIDAD

| Aspecto | Medida |
|---------|--------|
| **Privacidad de datos biométricos** | Cifrado AES-256, no se almacena huella raw |
| **Almacenamiento de huellas** | Solo hash, no imagen |
| **Consentimiento informado** | Interfaz clara |
| **Exclusión de personas sin huella legible** | Alternativa: CI + PIN |
| **Accesibilidad** | Interfaz con botones grandes, monitor + mouse |
| **Sesgo algorítmico** | No aplica (no hay ML) |
| **Transparencia del código** | Código abierto |
| **Auditoría ciudadana** | VVPAT visible + blockchain verificable |

---

## 21. MODELO DE SOSTENIBILIDAD

| Aspecto | Propuesta |
|---------|-----------|
| **Gobernanza** | Comité electoral + institución |
| **Financiamiento** | Presupuesto institucional |
| **Mantenimiento** | Equipo de TI de la institución |
| **Auditoría** | Estudiantes + docentes + veedores |
| **Capacitación** | Talleres anuales |
| **Actualización** | Cada 2 años |

---

## 22. PLAN DE PRUEBAS

### 22.1 Tipos de pruebas

| Tipo | Descripción | Herramienta |
|------|-------------|-------------|
| **Caja blanca** | Probar código interno | pytest |
| **Caja negra** | Probar funcionalidad | pytest |
| **Estrés** | Probar límites | Locust |
| **Accesibilidad** | Probar usabilidad | Manual |
| **Seguridad** | Probar ataques | OWASP ZAP |
| **Biometría** | Probar FAR/FRR | Dataset |
| **Blockchain** | Probar rendimiento | Hyperledger Caliper |
| **Integración** | Probar flujo completo | pytest + Fabric SDK |

### 22.2 Métricas de calidad (ISO 25000)

| Métrica | Descripción | Objetivo |
|---------|-------------|----------|
| **FAR** | False Acceptance Rate | < 0.1% |
| **FRR** | False Rejection Rate | < 1% |
| **Tiempo de votación** | Duración | < 2 min |
| **Disponibilidad** | Uptime | > 99% |
| **Latencia blockchain** | Tiempo de transacción | < 2 segundos |
| **Throughput blockchain** | Transacciones/segundo | > 100 TPS |

### 22.3 Pruebas de seguridad (OWASP)

| Prueba | Descripción |
|--------|-------------|
| **Inyección SQL** | Probar BD |
| **XSS** | Probar interfaz |
| **CSRF** | Probar formularios |
| **Autenticación** | Probar login |
| **Cifrado** | Probar AES/RSA |
| **Manipulación** | Probar integridad de blockchain |

---

## 23. PRESUPUESTO

| Ítem | Costo estimado |
|------|----------------|
| PC o laptop | Ya disponible |
| Lector de huella | $25 |
| Monitor | $80 |
| Mouse + teclado | $15 |
| Impresora térmica | $60 |
| TPM 2.0 | $20 |
| UPS | $30 |
| Cables | $15 |
| **TOTAL** | **$245** |

---

## 24. PENDIENTES Y VACÍOS POR RESOLVER

| # | Pendiente | Prioridad |
|---|-----------|-----------|
| 1 | Definir modalidad (TG/PG/TD) | 🔴 Crítico |
| 2 | Definir institución/caso (si PG/TD) | 🔴 Crítico |
| 3 | Investigar antecedentes nacionales (mín. 2) | 🔴 Crítico |
| 4 | Verificar legislación boliviana sobre voto electrónico | 🔴 Crítico |
| 5 | Definir licencia (Apache 2.0) | 🟡 Importante |
| 6 | Diseñar carcasa o gabinete | 🟡 Importante |
| 7 | Conseguir hardware | 🟡 Importante |
| 8 | Configurar red Hyperledger Fabric mononodo | 🟡 Importante |
| 9 | Desarrollar chaincode para auditoría | 🟡 Importante |
| 10 | Definir interfaz de usuario (PyQt6) | 🟡 Importante |

---

## 25. PRÓXIMOS PASOS

| # | Paso | Responsable | Plazo |
|---|------|-------------|-------|
| 1 | Definir modalidad | Estudiante | Inmediato |
| 2 | Definir institución/caso | Estudiante | Inmediato |
| 3 | Investigar antecedentes nacionales | Estudiante | 1 semana |
| 4 | Verificar legislación boliviana | Estudiante | 1 semana |
| 5 | Conseguir hardware | Estudiante | 2-4 semanas |
| 6 | Configurar Debian 13 + hardening | Estudiante | 1 semana |
| 7 | Instalar Hyperledger Fabric mononodo | Estudiante | 1 semana |
| 8 | Desarrollar prototipo | Estudiante | 8-12 semanas |
| 9 | Desarrollar chaincode | Estudiante | 3 semanas |
| 10 | Probar sistema | Estudiante | 2 semanas |
| 11 | Documentar tesis | Estudiante | 4 semanas |

---

## 26. ANEXO — INSTALACIÓN DE HYPERLEDGER FABRIC EN DEBIAN 13

### 26.1 Requisitos previos

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y curl git docker.io docker-compose build-essential
```

### 26.2 Instalación de Docker

```bash
# Iniciar y habilitar Docker
sudo systemctl start docker
sudo systemctl enable docker

# Añadir usuario al grupo docker
sudo usermod -aG docker $USER

# Cerrar sesión y volver a entrar para aplicar cambios
```

### 26.3 Descarga de Hyperledger Fabric

```bash
# Descargar el script de instalación
curl -sSLO https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/install-fabric.sh
chmod +x install-fabric.sh

# Ejecutar instalación
./install-fabric.sh docker binary samples
```

Esto descarga:
- **Binarios** (`peer`, `orderer`, `configtxgen`, etc.) en `fabric-samples/bin`
- **Imágenes Docker** de Fabric (peer, orderer, CA)
- **Ejemplos** (`fabric-samples`)

### 26.4 Levantar la red mononodo

```bash
cd fabric-samples/test-network

# Levantar la red con CA
./network.sh up -ca

# Verificar que los contenedores están corriendo
docker ps
```

Deberías ver 3 contenedores:
- `ca_org1`
- `orderer.example.com`
- `peer0.org1.example.com`

### 26.5 Crear un canal

```bash
# Crear el canal "mychannel"
./network.sh createChannel
```

### 26.6 Desplegar el chaincode

```bash
# Desplegar chaincode (ejemplo: acta)
./network.sh deployCC -ccn acta -ccp ../chaincode/acta -ccl go
```

### 26.7 Conectar la aplicación Python

```python
# Ejemplo con fabric-sdk-py
from fabric_sdk_py import FabricClient

client = FabricClient()
client.connect("peer0.org1.example.com", "mychannel", "acta")
result = client.submit_transaction("RegistrarActa", {"mesa": "1", "total": 500})
print(result)
```

### 26.8 Comandos útiles

```bash
# Detener la red
./network.sh down

# Reiniciar la red
./network.sh up -ca

# Ver logs de un contenedor
docker logs peer0.org1.example.com

# Ver la cadena de bloques
peer channel fetch newest -c mychannel
```

---

**Fin del Documento — v4.0**
```

---

