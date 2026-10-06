# ADR-002 — Integración Python ↔ Fabric mediante puente Go

**Estado:** Aceptada · 2026-10-05

## Contexto
La v4 proponía `fabric-sdk-py`, que no se mantiene desde ~2020 y no soporta Fabric 2.5. Los
clientes oficiales mantenidos (Fabric Gateway client API) existen solo para Go, Node.js y Java.
La aplicación principal está en Python.

## Decisión
Implementar un **servicio puente en Go** con `github.com/hyperledger/fabric-gateway` que escucha
únicamente en `127.0.0.1`, autenticado con un token local, y expone una API REST mínima
(`POST /tx/{funcion}`, `GET /eleccion/{id}`, `GET /historial/{id}`, `GET /salud`).
La app Python escribe cada anclaje en una tabla **outbox** y un trabajador lo envía al puente
con reintentos idempotentes.

## Alternativas descartadas
- `fabric-sdk-py`: abandonado.
- Invocar el binario `peer` por `subprocess`: frágil, difícil de manejar errores.
- Puente en Node.js: viable, pero Go unifica lenguaje con el chaincode.

## Consecuencias
- (+) SDK oficial y mantenido; chaincode y puente en el mismo lenguaje.
- (+) El outbox permite el **modo degradado**: la votación no depende de Fabric.
- (−) Un proceso adicional que supervisar (systemd).
- (−) `fabric-gateway` v1.12 requiere Go ≥ 1.25 (Debian 13 trae 1.24): se instaló Go 1.26.8 en
  `~/.local/go` (ADR-010).
- Implementado en el Sprint 4: `blockchain/bridge/` (REST: `/salud`, `/tx/{funcion}`, `/mesa/…`,
  `/historial/…`; errores 409 = rechazo del chaincode, 503 = Fabric no disponible).
