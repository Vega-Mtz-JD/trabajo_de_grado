# ADR-003 — Cifrado híbrido de votos y Shamir 3-de-5

**Estado:** Aceptada · 2026-10-05

## Contexto
La v4 cifraba votos con AES-256 sin definir la custodia de la clave: quien tuviera la clave (el
propio equipo) podría ver resultados parciales o votos en cualquier momento.

## Decisión
- Al configurar la elección se genera un par **RSA-3072**. Cada voto se cifra con una clave
  AES-256-GCM aleatoria, envuelta con **RSA-OAEP(SHA-256)** usando la clave pública.
- La clave privada se cifra con una KEK aleatoria de 256 bits; la KEK se divide con **Shamir
  sobre GF(256)** en 5 partes con umbral 3, y se destruye. Las partes se imprimen (texto + QR)
  para 5 custodios.
- En el escrutinio, ≥ 3 custodios reconstruyen la KEK **en memoria**; se descifran y cuentan los
  votos; la clave se descarta.
- El texto plano del voto tiene **longitud fija** (relleno) para no filtrar la opción por tamaño.

## Consecuencias
- (+) Ningún actor individual (ni el equipo) puede conocer resultados antes del escrutinio.
- (+) Justifica de forma real el uso de AES-256 y RSA del título.
- (−) Logística: si se pierden 3 de 5 partes, los votos no se pueden descifrar → el papel (VVPAT)
  queda como respaldo y el protocolo exige sobres sellados con custodia.
- Shamir se implementa en el proyecto (≈ 60 líneas) con pruebas exhaustivas; es material
  didáctico para el marco teórico.
