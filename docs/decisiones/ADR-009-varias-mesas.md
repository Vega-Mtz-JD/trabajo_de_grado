# ADR-009 — Varias urnas: padrón dividido, empadronamiento local y consolidación

**Estado:** Aceptada · 2026-10-05

## Contexto
La empresa puede necesitar varias urnas (mesas) en una misma elección. Las urnas no tienen red
(RNF01), así que no pueden consultarse entre sí. Diego definió que el empadronamiento (datos, foto y
huella) se haga **en el mismo equipo** de cada urna, sin importar datos externos, y que el escrutinio
sea **por mesa**.

## Decisión
1. **Definición de elección exportable.** Una urna crea la *definición* (identificador global,
   nombre, opciones, mesas, sal del padrón) y la exporta como archivo cifrado y firmado (`.vsd`).
   Las demás urnas la importan y verifican la firma (la huella del equipo creador se compara con la
   hoja impresa). La definición no contiene datos personales.
2. **Cada mesa es una instancia local** de la elección (`eleccion_global` + `mesa`) con **su propia
   clave** y **sus propios custodios** (jurados de esa mesa). Escrutinio por mesa.
3. **Padrón dividido y local.** Cada urna empadrona a sus votantes. Antes de la apertura, cada urna
   exporta un resumen cifrado de su padrón (`.vsp`) y el **cruce de padrones** detecta CI
   duplicados entre mesas; el operador inhabilita al duplicado (con motivo, en la bitácora).
4. **Foto:** al empadronar (foto de registro) y al identificarse en la jornada (foto de presencia,
   en tabla aparte `padron.presencia`). Ambas cifradas con la clave de datos personales del equipo.
   Nunca hay cámara en la cabina y la presencia no se vincula al voto.
5. **Consolidación:** verifica cada paquete de mesa (auditoría triple), exige la misma definición,
   mesas distintas y que ningún CI haya votado en dos mesas, y suma los resultados en un acta de
   cómputo consolidado.
6. Los anclajes de Fabric se identifican por `eleccion_global` + `mesa`.

## Consecuencias
- (+) Ninguna urna recibe datos personales de fuera; la única entrada externa es la definición firmada.
- (+) Un duplicado entre mesas se detecta antes de votar y, si se escapara, también al consolidar.
- (−) El cruce de padrones requiere llevar un USB a cada urna antes de la apertura (paso del protocolo).
- (−) Más datos personales (fotos): se cifran, se excluyen del ledger y se borran al cerrar el proceso
  según la política de retención de la empresa.
