# CAPÍTULO III — MARCO APLICATIVO

## 3.1. Marco aplicativo

<!-- Elaboración propia: situación actual con DFD; propuesta. -->

## 3.2. Desarrollo de la metodología

### 3.2.1. Análisis de requerimientos

<!-- Requerimientos funcionales y no funcionales; historias de usuario; product backlog. -->

### 3.2.2. Diseño del sistema

<!-- UML: casos de uso, clases, secuencia, estados, despliegue; diseño de BD; arquitectura (ADRs). -->

### 3.2.3. Implementación

<!-- Un subapartado por sprint: objetivo, backlog del sprint, resultado, capturas.
     Fuente: docs/bitacora/sprint-*.md -->

#### Sprint 1: Núcleo criptográfico, base de datos y bitácora

El primer sprint tuvo como objetivo construir los componentes de seguridad sobre los que se apoya el resto del sistema. En el módulo criptográfico se implementaron la función hash SHA3-256 con serialización canónica, el árbol de Merkle que resume el conjunto de votos en un único valor, el esquema de secreto compartido de Shamir sobre el cuerpo finito GF(2⁸) y el cifrado híbrido de votos, que combina AES-256-GCM con RSA-OAEP. Este último produce textos cifrados de longitud fija, de modo que el tamaño no revela la opción elegida, y deposita la clave privada de la elección bajo la custodia de cinco personas, de las cuales al menos tres deben concurrir para descifrarla. Se completaron además las firmas digitales RSA-PSS que respaldan la zerésima y las actas.

La persistencia se implementó en PostgreSQL 17 con cinco esquemas (elección, padrón, urna, auditoría y blockchain) y roles de mínimo privilegio. El rol de la aplicación no puede insertar votos directamente ni modificar el indicador de participación del votante: solo puede invocar la función `urna.emitir_voto()`, que realiza ambas operaciones en una única transacción. Los votos, la bitácora y las actas quedaron protegidos con disparadores de solo inserción que impiden su modificación incluso al superusuario. Durante las pruebas se identificó que la columna interna `xmin` de PostgreSQL permite reconstruir el orden de emisión y vincular a cada votante con su voto. Para mitigar este riesgo se diseñó la función `urna.mezclar()`, que reescribe la urna en orden aleatorio y verifica que su contenido no haya cambiado. Finalmente, se implementó la bitácora de auditoría encadenada por hash, cuya integridad se comprueba recalculando la cadena y contrastando la última entrada con un ancla externa.

| Elemento del backlog | Resultado |
|---|---|
| Hash SHA3-256, serialización canónica y árbol de Merkle | Completado |
| Secreto compartido de Shamir (3 de 5) | Completado |
| Cifrado híbrido de votos y custodia de la clave | Completado |
| Firmas digitales RSA-PSS | Completado |
| Esquema PostgreSQL, roles, disparadores y máquina de estados | Completado |
| Emisión atómica del voto y mezcla de la urna | Completado |
| Bitácora de auditoría encadenada | Completado |
| Pruebas automatizadas (61 pruebas, cobertura del 95 %) | Completado |

<!-- CAPTURA: salida de `pytest --cov=votoseguro` en la terminal (61 passed, 95 %). -->
<!-- CAPTURA: diagrama entidad-relación de la BD generado con DBeaver o pgAdmin. -->

#### Sprint 2: Proceso electoral completo y auditoría triple

El segundo sprint implementó las fases del proceso electoral como servicios independientes: configuración, empadronamiento, apertura, identificación y emisión del voto, cierre, escrutinio, exportación y verificación. En la configuración se genera el par de claves de la elección y la clave privada se reparte entre cinco custodios, cuyas partes se imprimen con código QR. Durante el empadronamiento se registra la plantilla de huella de cada votante cifrada con la clave del equipo. La apertura comprueba el hardware y emite la zerésima, un acta firmada que certifica que la urna está vacía y compromete el padrón mediante una raíz de Merkle. En la votación, el votante se identifica con su cédula y su huella con un máximo de tres intentos; si la huella es ilegible, el operador puede autorizar una excepción justificada que queda registrada. Cada voto se cifra, se deposita en la urna y genera un comprobante impreso sin hora ni datos del votante, y cada diez votos se mezcla la urna y se registra un punto de control.

Al cierre se verifica que el número de votos coincida con el de votantes marcados y se emite el acta de cierre firmada. El escrutinio requiere que tres de los cinco custodios presenten sus partes: la clave se reconstruye solo en memoria, se descifran y cuentan los votos y se emite el acta de escrutinio. Finalmente, el expediente completo se exporta a un paquete cifrado con un manifiesto firmado, y un verificador independiente contrasta el papel, el paquete y los anclajes del registro distribuido. Para validar el conjunto se desarrolló una simulación con cien votantes que incluye fallas de lectura, una excepción manual, un intento de doble voto y abstención; el verificador emitió un dictamen conforme en sus veintitrés comprobaciones.

| Elemento del backlog | Resultado |
|---|---|
| Configuración y custodia de la clave (3 de 5) | Completado |
| Empadronamiento biométrico (simulado) | Completado |
| Apertura y zerésima firmada | Completado |
| Identificación, huella 1:1, excepción manual y emisión con VVPAT | Completado |
| Puntos de control con mezcla de urna | Completado |
| Cierre, escrutinio y actas firmadas | Completado |
| Exportación del paquete cifrado y verificador de auditoría triple | Completado |
| Simulación de punta a punta (`votoseguro demo`) | Completado |
| Pruebas automatizadas (81 pruebas, cobertura del 96 %) | Completado |

<!-- CAPTURA: salida de `votoseguro demo` con el informe de auditoría CONFORME. -->
<!-- CAPTURA: acta de cierre (salida_demo/impresiones/07_acta_cierre.pdf) y un VVPAT. -->
<!-- CAPTURA: tabla auditoria.bitacora en pgAdmin mostrando la cadena de hashes. -->

### 3.2.4. Pruebas y calidad de software

### 3.2.5. Resultados
