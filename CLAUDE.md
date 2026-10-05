# CLAUDE.md — VOTO SEGURO (Proyecto de Grado UPEA)

Sistema de votación electrónica **offline** con autenticación biométrica, VVPAT, cifrado de umbral
y anclaje en **Hyperledger Fabric 2.5**. Proyecto de Grado de Ingeniería de Sistemas (UPEA, El Alto).
Responder siempre en **español**. Reparto de esfuerzo: **70 % sistema · 30 % informe**.

## Fuente de verdad
- Diseño: `docs/propuesta_v5.md` · Decisiones: `docs/decisiones/ADR-*.md` (no contradecirlas;
  si algo cambia, crear/actualizar un ADR).
- Normativa: `docs/normativa/reglamento_proyecto_grado.txt` (Art. 29–35, 46–48) y
  `docs/normativa/guia_tutora.txt` (guía de la tutora metodológica).

## Estructura
```
app/          Python 3.13, paquete src/votoseguro/{dominio,cripto,datos,auditoria,hardware,blockchain,servicios,ui}
blockchain/   network/ (compose Fabric), chaincode/acta (Go), bridge/ (Go, fabric-gateway)
docs/         Vault de Obsidian: informe/ (capítulos Art. 48), bitacora/ (sprints, reuniones),
              referencias/bibliografia.bib + apa.csl, exportar/ (pandoc → Word)
scripts/      instalación, hardening, kiosco
```

## Comandos
```bash
cd app && . .venv/bin/activate && pytest              # pruebas
pytest --cov=votoseguro --cov-report=term-missing     # cobertura
docs/exportar/exportar_word.sh [perfil]               # informe → docs/salida/*.docx
```

## Reglas técnicas no negociables
- **BD: PostgreSQL 17** (la tutora prohíbe BD ligeras como SQLite). Driver psycopg 3, solo socket Unix.
- **Secreto del voto (ADR-004/008):** nunca guardar hora en votos ni en `ya_voto`; nunca registrar en
  bitácora/ledger/logs un identificador que vincule votante↔voto; textos cifrados de longitud fija.
- **Nada de datos personales en Fabric.** Solo hashes, conteos y raíces de Merkle.
- Criptografía solo con `cryptography`/`hashlib`; nunca inventar primitivas (excepto Shamir GF(256), ADR-003, con pruebas).
- Hardware siempre detrás de interfaces con implementación simulada (ADR-006).
- Código, identificadores y docstrings en español, siguiendo el estilo existente.
- Toda funcionalidad nueva con pruebas pytest; las pruebas de BD usan una instancia PostgreSQL temporal.

## Reglas para el informe
- Formato (Art. 34–35): Carta, Arial 11, interlineado 2, márgenes 2.55/2.55/3 izq/2.55, APA 7.
- Estructura y numeración exactas del Art. 48 (ya están en `docs/informe/`).
- Antecedentes **desde 2020**; ≥ 2 internacionales y ≥ 2 nacionales (+ locales).
- Marco teórico: cada concepto con **≥ 2 autores** + concepto propio.
- **Nunca inventar referencias, autores, páginas, DOI ni datos de la empresa.** Si falta la
  fuente, escribir `⚠️ VERIFICAR` o `[EMPRESA]`. Citas en Markdown como `[@clave]`, con la
  entrada correspondiente en `docs/referencias/bibliografia.bib`.

## Pendientes conocidos
- `[EMPRESA]` sin definir. ADR-008 (PostgreSQL) pendiente del visto bueno de la tutora.
- Hardware (ZKTeco ZK9500/SLK20R con SDK Linux, impresora ESC/POS) aún no comprado → usar simuladores.
- `fabric-gateway` reciente requiere Go ≥ 1.25 (sistema: 1.24).
