# ADR-010 — Red Fabric: cryptogen, chaincode como servicio y trazabilidad del código

**Estado:** Aceptada · 2026-10-05

## Contexto
La red debe funcionar **sin internet** en el equipo de la urna (ADR-001). En el modelo clásico de
Fabric, el peer compila el chaincode dentro de un contenedor `fabric-ccenv` y descarga dependencias Go
de internet, y necesita acceso al socket de Docker. Además, en una red de una sola organización no
hay inscripción dinámica de identidades.

## Decisión
1. **Identidades con `cryptogen`** (generación local, sin servidor) en lugar de Fabric CA: un orderer
   (`OrdenanteMSP`), un peer (`MesaMSP`), un administrador y un usuario cliente (`User1`, usado por el
   puente). Los certificados incluyen `localhost`/`127.0.0.1` como SAN.
2. **Chaincode como servicio (CCaaS):** el chaincode `acta` se compila como binario Go estático y corre
   en su propio contenedor (`fabric-baseos`); el peer se conecta a él. El peer no compila nada, no
   descarga nada y no necesita el socket de Docker.
3. **Trazabilidad del código del chaincode:** con CCaaS el paquete instalado solo contiene la dirección
   del servicio, así que un cambio de código no cambiaría el identificador del paquete. Por eso la
   etiqueta del paquete incluye el **SHA-256 del binario** (`acta_1.0_<hash>`): todo cambio de código
   exige aprobar y confirmar una nueva **secuencia** del ciclo de vida, que queda registrada en el ledger.
4. **Empaquetado reproducible** (`tar` con fechas y dueños fijos, `gzip -n`): el mismo binario produce
   siempre el mismo identificador.
5. Base de estado LevelDB (ADR-007), `BatchTimeout` de 500 ms, puertos publicados solo en `127.0.0.1`,
   ledger en volúmenes Docker con nombre.
6. Go 1.26.8 instalado en `~/.local/go` (Debian 13 trae 1.24; `fabric-gateway` v1.12 requiere ≥ 1.25).

## Consecuencias
- (+) Operación offline completa una vez descargadas las imágenes (`peer`, `orderer`, `baseos`).
- (+) Cada versión del código del chaincode queda auditada en el ledger (secuencia 1, 2, 3…).
- (+) Latencia medida de anclaje: 0,525 s (media de 20 transacciones), dominada por el corte de bloque.
- (−) Con un solo orderer Raft no hay tolerancia a fallas (declarado en ADR-001); el modo degradado
  (outbox) cubre las caídas.
- (−) `cryptogen` no es para producción multiorganización: si en el futuro participan varias
  instituciones, se debe migrar a Fabric CA.
