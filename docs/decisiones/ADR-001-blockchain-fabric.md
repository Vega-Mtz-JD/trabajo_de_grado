# ADR-001 — Hyperledger Fabric 2.5 mononodo con anclaje en papel

**Estado:** Aceptada · 2026-10-05

## Contexto
El sistema requiere un registro de hitos electorales resistente a manipulación, operando sin
internet en un único equipo. El antecedente local (TG-0059, UPEA 2020) implementó una cadena
propia en Python con prueba de trabajo, que puede regenerarse completa por quien controle el equipo.

## Decisión
Usar **Hyperledger Fabric 2.5 LTS** con 1 CA, 1 orderer Raft y 1 peer en Docker, canal `elecciones`
y chaincode `acta` en Go que valida las transiciones de estado de la elección. Para compensar la
debilidad de un nodo único, el hash del último bloque y la raíz de Merkle se **anclan
externamente** imprimiéndolos (texto + QR) en la zerésima y el acta, firmadas a mano por delegados.

## Consecuencias
- (+) Tecnología estándar, permisionada, con identidades X.509 y lógica de negocio en chaincode.
- (+) El chaincode rechaza transiciones inválidas (p. ej. checkpoint tras cierre).
- (−) Mayor complejidad operativa (Docker, certificados) y consumo de RAM (≥ 8 GB recomendado).
- (−) Un solo nodo no ofrece tolerancia a fallas ni inmutabilidad frente al administrador: se
  declara explícitamente como *tamper-evidence* en límites del proyecto.
- Trabajo futuro: múltiples organizaciones (empresa, sindicato, auditor externo) con un peer cada una.
