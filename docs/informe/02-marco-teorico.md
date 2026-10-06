# CAPÍTULO II — MARCO TEÓRICO

<!-- BORRADOR v1 (2026-10-06). GUÍA: cada concepto con mínimo DOS autores + concepto propio.
     Las citas están PARAFRASEADAS (sin comillas). Si la tutora exige citas textuales con página,
     reemplazar por el texto exacto del libro o artículo (no inventar páginas).
     Reescribir con palabras propias antes de entregar (control de similitud ≤ 20 %). -->

## 2.1. Marco conceptual

### 2.1.1. Sistema y sistema de información

Laudon y Laudon definen un sistema de información como un conjunto de componentes interrelacionados que recolectan, procesan, almacenan y distribuyen información para apoyar la toma de decisiones y el control en una organización [@laudon2020]. Sommerville, desde la ingeniería de software, subraya que un sistema de software abarca no solo los programas, sino también la documentación, los datos de configuración y los procedimientos necesarios para su operación [@sommerville2016].

**Concepto propio:** un sistema es un conjunto de componentes de hardware, software, datos, procedimientos y personas que trabajan de forma coordinada para cumplir un propósito; en este proyecto, el propósito es registrar, contar y verificar votos.

### 2.1.2. Votación electrónica

Gibson, Krimmer, Teague y Pomares describen la votación electrónica como el uso de medios electrónicos en una o más etapas del proceso electoral, especialmente en la emisión y el conteo de votos, y distinguen entre la votación presencial, en recintos supervisados, y la votación remota [@gibson2016]. La Recomendación CM/Rec(2017)5 del Consejo de Europa establece que un sistema de voto electrónico debe respetar los mismos principios que una elección tradicional: sufragio universal, igual, libre y secreto, además de transparencia y verificabilidad [@coe2017]. Jafar, Aziz y Shukur añaden que los sistemas de votación electrónica buscan reducir costos y tiempos, pero enfrentan desafíos de seguridad, privacidad y confianza que motivan el uso de cadenas de bloques [@jafar2021].

**Concepto propio:** la votación electrónica es la emisión y el conteo de votos mediante equipos informáticos que deben garantizar los mismos principios del voto en papel —en particular el secreto y la verificabilidad— y que, en su modalidad presencial, se realiza en un recinto bajo supervisión.

### 2.1.3. Operación sin conexión (aislamiento de red)

Byres analiza el concepto de *air gap* —el aislamiento físico de un sistema respecto de cualquier red— como medida de protección de sistemas críticos, y advierte que solo es efectivo si se acompaña de controles sobre los medios extraíbles y los procedimientos del personal [@byres2013]. La Oficina Nacional de Procesos Electorales del Perú describe su voto electrónico presencial como una solución cuyos equipos se encuentran aislados, sin conexión a bases de datos externas ni a redes inalámbricas o Bluetooth [@onpe_vep].

**Concepto propio:** un sistema fuera de línea es aquel que funciona sin ninguna conexión de red, de modo que no puede ser atacado a distancia; su seguridad se completa con el control del acceso físico y de los medios, como las memorias USB, que entran y salen del equipo.

### 2.1.4. Cadena de bloques (blockchain)

Nakamoto propuso una cadena de bloques en la que cada bloque contiene el resumen criptográfico del anterior, de forma que modificar un registro obliga a rehacer todos los bloques posteriores [@nakamoto2008]. Yaga, Mell, Roby y Scarfone, del NIST, definen las cadenas de bloques como libros de registro digitales distribuidos, resistentes y evidentes ante la manipulación, que operan sin una autoridad central que pueda alterarlos unilateralmente [@yaga2018]. Zheng y colaboradores destacan como características principales la descentralización, la persistencia, el anonimato y la auditabilidad [@zheng2018].

**Concepto propio:** una cadena de bloques es un registro de solo adición organizado en bloques enlazados por funciones hash, cuya alteración posterior es detectable; en este proyecto se utiliza para dejar constancia verificable de los hitos de cada elección.

### 2.1.5. Cadena de bloques permisionada e Hyperledger Fabric

Yaga y colaboradores distinguen las cadenas sin permisos, en las que cualquiera puede participar, de las permisionadas, en las que solo participan entidades autorizadas e identificadas [@yaga2018]. Androulaki y colaboradores presentan Hyperledger Fabric como una plataforma permisionada y modular que separa la ejecución de las transacciones, su ordenamiento y su validación, y que permite programar la lógica de negocio en lenguajes de propósito general mediante *chaincode* [@androulaki2018]. La documentación oficial de la versión 2.5 describe sus componentes: nodos pares (*peers*), servicio de ordenamiento, canales, autoridades de certificación y el cliente Fabric Gateway [@fabric25].

**Concepto propio:** Hyperledger Fabric es una cadena de bloques para organizaciones en la que cada participante tiene una identidad certificada y las reglas de negocio se ejecutan en contratos inteligentes; no requiere criptomonedas ni conexión a Internet, por lo que puede operar en una red local cerrada.

### 2.1.6. Contrato inteligente (chaincode)

Zheng y colaboradores describen los contratos inteligentes como programas que se ejecutan de forma automática sobre una cadena de bloques cuando se cumplen condiciones predefinidas [@zheng2018]. En Hyperledger Fabric, el contrato inteligente se denomina *chaincode* y encapsula la lógica que valida y modifica el estado compartido del registro [@androulaki2018]; Yaga y colaboradores señalan que su resultado es verificable por todos los participantes de la red [@yaga2018].

**Concepto propio:** un contrato inteligente es un programa que se ejecuta en la cadena de bloques y que solo acepta las operaciones que cumplen sus reglas; en este proyecto, el chaincode `acta` rechaza cualquier hito electoral fuera de orden o con conteos incoherentes.

### 2.1.7. Auditoría

La norma ISO 19011 define la auditoría como un proceso sistemático, independiente y documentado para obtener evidencias objetivas y evaluarlas con el fin de determinar el grado en que se cumplen unos criterios [@iso19011]. En el ámbito electoral, Mercuri sostiene que un sistema de votación electrónica solo es auditable si conserva un registro independiente, verificado por el propio votante, que permita recontar los votos [@mercuri2002].

**Concepto propio:** la auditoría electoral es la revisión independiente y documentada de la evidencia de una elección —papeletas, registros digitales y actas— para comprobar que el resultado corresponde a los votos emitidos.

### 2.1.8. Verificación y verificación multinivel

El estándar IEEE 1012 define la verificación como el proceso que proporciona evidencia objetiva de que un producto cumple sus requisitos y especificaciones [@ieee1012]. Gibson y colaboradores identifican la verificabilidad como una propiedad central de los sistemas de voto electrónico: debe poder comprobarse que los votos fueron registrados y contados tal como se emitieron [@gibson2016]; el Consejo de Europa recomienda, en el mismo sentido, que los sistemas permitan verificaciones independientes [@coe2017].

**Concepto propio:** la verificación multinivel es la comprobación de un mismo resultado a partir de varias fuentes de evidencia independientes —en este proyecto, el papel, el paquete digital cifrado y el registro distribuido— de modo que una alteración en una de ellas se detecta al contrastarla con las otras dos.

### 2.1.9. Resultados electorales y escrutinio

La Ley 026 del Régimen Electoral regula el escrutinio y el cómputo como las etapas en las que se cuentan los votos de cada mesa y se consolidan los resultados, que se registran en actas firmadas por los jurados [@ley026]. El Consejo de Europa recomienda que el conteo electrónico sea reproducible y que sus resultados puedan contrastarse de forma independiente [@coe2017].

**Concepto propio:** los resultados electorales son el número de votos válidos, blancos y nulos obtenidos por cada opción en cada mesa, registrados en un acta; el escrutinio es el procedimiento para obtenerlos.

### 2.1.10. Padrón electoral

La Ley 018 asigna al Órgano Electoral Plurinacional la administración del padrón electoral, entendido como el registro de las personas habilitadas para votar [@ley018], y la Ley 026 establece que solo pueden votar quienes figuran en él [@ley026]. En los sistemas electrónicos, Gibson y colaboradores señalan que la identificación del elector y la emisión del voto deben mantenerse separadas para preservar el secreto [@gibson2016].

**Concepto propio:** el padrón es la lista de personas habilitadas para votar en una mesa; en este proyecto incluye, además de los datos personales, una fotografía y la plantilla de la huella, ambas cifradas, y se mantiene separado de la urna.

### 2.1.11. Autenticación biométrica

Jain, Ross y Prabhakar definen el reconocimiento biométrico como la identificación automática de una persona a partir de sus características fisiológicas o de comportamiento, y distinguen la verificación (comparación 1:1 con una identidad declarada) de la identificación (búsqueda 1:N) [@jain2004]. Maltoni y colaboradores explican que la comparación de huellas produce un puntaje de similitud, por lo que dos lecturas del mismo dedo nunca son idénticas, y que el desempeño se mide con las tasas de falsa aceptación (FAR) y de falso rechazo (FRR) [@maltoni2022].

**Concepto propio:** la autenticación biométrica 1:1 comprueba que la persona presente es quien dice ser, comparando su huella con la plantilla registrada para la cédula que presenta; como la comparación es aproximada, se acepta cuando el puntaje supera un umbral.

### 2.1.12. Comprobante en papel verificable por el votante (VVPAT)

Mercuri propuso que el votante pueda ver, a través de una ventana, un comprobante impreso de su voto que no se lleva consigo y que queda en una urna sellada, para que exista un registro independiente del software [@mercuri2002]. Gibson y colaboradores señalan que los comprobantes en papel permiten auditorías y recuentos que no dependen de la confianza en el equipo electrónico [@gibson2016].

**Concepto propio:** el VVPAT es una papeleta impresa por el sistema que el votante verifica y deposita en una urna; no contiene datos del votante ni la hora, y permite recontar los votos en papel si el resultado digital es cuestionado.

### 2.1.13. Cifrado simétrico (AES-GCM)

El NIST especifica el Estándar de Cifrado Avanzado (AES) como un cifrado por bloques con claves de 128, 192 o 256 bits [@nist2023aes], y define el modo GCM, que además de cifrar autentica los datos, de modo que cualquier alteración se detecta al descifrar [@dworkin2007]. Stallings explica que en el cifrado simétrico la misma clave cifra y descifra, por lo que su protección es la clave del esquema [@stallings2017].

**Concepto propio:** el cifrado simétrico protege los datos con una sola clave secreta; en este proyecto, AES-256-GCM cifra cada voto, las fotografías y las plantillas de huella, y detecta cualquier modificación.

### 2.1.14. Cifrado asimétrico y firma digital (RSA)

El estándar PKCS #1 especifica el algoritmo RSA, que utiliza un par de claves —una pública y una privada— con el esquema OAEP para cifrar y el esquema PSS para firmar [@moriarty2016]. Katz y Lindell explican que una firma digital permite a cualquiera verificar, con la clave pública, que un documento fue firmado por el poseedor de la clave privada y no fue alterado [@katz2020].

**Concepto propio:** el cifrado asimétrico usa una clave pública para cifrar o verificar y una clave privada para descifrar o firmar; en este proyecto, la clave pública de la elección cifra los votos y la clave del equipo firma las actas.

### 2.1.15. Función hash criptográfica (SHA-3)

El NIST define SHA-3 como una familia de funciones que transforman un mensaje de cualquier longitud en un resumen de longitud fija [@nist2015sha3]. Katz y Lindell explican que una función hash criptográfica debe ser resistente a colisiones: debe ser inviable encontrar dos mensajes con el mismo resumen [@katz2020].

**Concepto propio:** una función hash produce una «huella» de longitud fija de cualquier dato; un cambio mínimo en el dato cambia por completo la huella, lo que permite detectar alteraciones en votos, actas y bitácora.

### 2.1.16. Árbol de Merkle

Merkle propuso estructurar los resúmenes de muchos datos en un árbol en el que cada nodo es el hash de sus hijos, de modo que un único valor, la raíz, compromete al conjunto completo [@merkle1988]. Yaga y colaboradores describen su uso en las cadenas de bloques para resumir todas las transacciones de un bloque [@yaga2018].

**Concepto propio:** la raíz de Merkle resume en 32 bytes el conjunto completo de votos de una urna; si se altera, agrega o elimina un solo voto, la raíz cambia.

### 2.1.17. Secreto compartido de Shamir

Shamir mostró cómo dividir un secreto en *n* partes de modo que cualquier grupo de *k* partes permite reconstruirlo, mientras que *k − 1* partes no revelan ninguna información sobre él [@shamir1979].

<!-- ⚠️ VERIFICAR: agregar una segunda fuente (p. ej. un libro de criptografía que trate el secreto compartido) con su página. -->

**Concepto propio:** el secreto compartido permite que la clave que abre la urna no esté en manos de una sola persona: se reparte entre cinco custodios y se necesitan tres de ellos para el escrutinio.

### 2.1.18. Secreto del voto

La Constitución Política del Estado establece que el sufragio se ejerce mediante voto igual, universal, directo, individual, secreto, libre y obligatorio [@cpe2009]. El Consejo de Europa exige que los sistemas de voto electrónico garanticen que no sea posible vincular un voto con el votante que lo emitió [@coe2017].

**Concepto propio:** el secreto del voto exige que nadie, ni siquiera el administrador del sistema, pueda saber por quién votó una persona; en este proyecto se garantiza separando el padrón de la urna, eliminando toda marca de tiempo de los votos y mezclando la urna periódicamente.

## 2.2. Marco contextual

<!-- Contexto del voto electrónico en la región y en Bolivia; ampliar con fuentes verificadas. -->

En América del Sur, varios organismos electorales emplean equipos de votación presencial. El Tribunal Superior de Justicia Electoral del Paraguay utilizó máquinas de votación en las elecciones municipales de 2021, en las que el elector selecciona su opción en una pantalla y la máquina imprime una boleta que se deposita en una urna [@tsje2021]. La Oficina Nacional de Procesos Electorales del Perú aplica el voto electrónico presencial con equipos aislados de cualquier red y una constancia impresa que puede cotejarse [@onpe_vep]. En Bolivia, el voto electrónico solo está previsto para los ciudadanos residentes en el exterior [@ley026], mientras que las elecciones internas de empresas, cooperativas y universidades se realizan, por lo general, con papeletas y conteo manual, como ocurre en [EMPRESA].

## 2.3. Marco metodológico

### 2.3.1. SCRUM

SCRUM es un marco de trabajo ligero que ayuda a personas, equipos y organizaciones a generar valor mediante soluciones adaptativas para problemas complejos [@schwaber2020]. Define tres responsabilidades —el *Product Owner*, el *Scrum Master* y los desarrolladores—, cinco eventos —el sprint, la planificación, la reunión diaria, la revisión y la retrospectiva— y tres artefactos —el *product backlog*, el *sprint backlog* y el incremento— [@schwaber2020]. Pressman y Maxim la ubican entre los métodos ágiles que privilegian las entregas incrementales y la adaptación al cambio [@pressman2020].

<!-- Tabla de roles del proyecto: Product Owner = [EMPRESA: responsable], Scrum Master = tutor/postulante, Desarrollador = postulante. -->

### 2.3.2. UML

El Lenguaje Unificado de Modelado es un lenguaje gráfico estándar para especificar, visualizar, construir y documentar los artefactos de un sistema de software [@booch2005], mantenido por el Object Management Group en su versión 2.5.1 [@omg2017uml]. En este proyecto se emplean diagramas de casos de uso, clases, secuencia, estados (máquina de estados de la elección) y despliegue.

## 2.4. Marco institucional

[EMPRESA: descripción de la institución, su estructura y su reglamento de elecciones internas].

## 2.5. Marco tecnológico

### 2.5.1. Lenguajes y bibliotecas

- **Python:** lenguaje de programación interpretado de propósito general, con una biblioteca estándar amplia [@pythondocs]; es el lenguaje de la aplicación.
- **PySide6:** enlace oficial de Python para el marco gráfico Qt 6, distribuido con licencia LGPL [@qtpyside6]; se usa para el panel de mesa y la cabina.
- **Go:** lenguaje compilado utilizado para el contrato inteligente y el servicio puente, por ser uno de los lenguajes oficiales de Hyperledger Fabric [@fabric25].

### 2.5.2. Base de datos: PostgreSQL

PostgreSQL es un sistema de gestión de bases de datos objeto-relacional de código abierto que ofrece transacciones ACID, roles con privilegios por columna, disparadores y funciones en el servidor [@postgresql17]. Se emplea la versión 17 con la extensión pgaudit, que registra las operaciones sobre la base de datos con su responsable y momento, y se configura para aceptar únicamente conexiones locales.

### 2.5.3. Contenedores: Docker

Docker permite empaquetar una aplicación con sus dependencias en contenedores aislados que se ejecutan de la misma forma en cualquier equipo [@dockerdocs]; los nodos de Hyperledger Fabric se ejecutan en contenedores.

### 2.5.4. Pruebas de software

Myers, Sandler y Badgett definen las pruebas como el proceso de ejecutar un programa con la intención de encontrar errores, y distinguen las pruebas de caja blanca, basadas en la estructura interna del código, de las pruebas de caja negra, basadas en las especificaciones [@myers2011]. Las pruebas de estrés someten al sistema a cargas superiores a las normales, y las de accesibilidad evalúan su uso por personas con distintas capacidades [@sommerville2016].

### 2.5.5. Seguridad de la información (ISO/IEC 27000)

La norma ISO/IEC 27001 establece los requisitos de un sistema de gestión de seguridad de la información orientado a preservar la confidencialidad, integridad y disponibilidad de la información [@iso27001], y la ISO/IEC 27002 describe los controles de referencia, entre ellos el control de acceso, la criptografía y el registro y supervisión de eventos [@iso27002]. El modelo STRIDE clasifica las amenazas en suplantación, manipulación, repudio, revelación de información, denegación de servicio y elevación de privilegios [@shostack2014], y la metodología MAGERIT guía el análisis y la gestión de riesgos de los sistemas de información [@magerit2012].

### 2.5.6. Ciclo de vida del software

Sommerville describe el ciclo de vida como el conjunto de actividades que conducen a la producción de un sistema —especificación, diseño e implementación, validación y evolución— y presenta el modelo incremental como alternativa al modelo en cascada [@sommerville2016]. Pressman y Maxim señalan que los modelos iterativos permiten entregar versiones operativas que se perfeccionan en cada ciclo [@pressman2020].

### 2.5.7. Métricas de calidad

La norma ISO/IEC 25010 define el modelo de calidad del producto de software con características como la adecuación funcional, la eficiencia de desempeño, la compatibilidad, la usabilidad, la fiabilidad, la seguridad, la mantenibilidad y la portabilidad [@iso25010]. La escala SUS es un cuestionario de diez preguntas que proporciona una medida global de la usabilidad percibida [@brooke1996].

### 2.5.8. Modelo de costos COCOMO II

COCOMO II estima el esfuerzo de desarrollo, en personas-mes, a partir del tamaño del software (miles de líneas de código o puntos de función), ajustado por factores de escala y multiplicadores de esfuerzo [@boehm2000].

## 2.6. Marco legal

| Norma | Contenido relevante para el proyecto |
|---|---|
| Constitución Política del Estado [@cpe2009] | Voto igual, universal, directo, individual, secreto, libre y obligatorio; derecho a la privacidad y acción de protección de privacidad ⚠️ VERIFICAR artículos |
| Ley 018 del Órgano Electoral Plurinacional [@ley018] | Atribuciones del OEP, incluida la supervisión de procesos electorales de organizaciones |
| Ley 026 del Régimen Electoral [@ley026] | Principios del sufragio, escrutinio y cómputo; el voto electrónico solo se prevé para los bolivianos en el exterior (Art. 43.II, modificado por la Ley 1066 de 2018) |
| Ley 164 y Decreto Supremo 1793 [@ley164; @ds1793] | Validez jurídica de la firma digital vinculada a un certificado de una entidad certificadora autorizada |
| [EMPRESA: estatuto o reglamento de elecciones internas] | Reglas que el sistema debe respetar en la institución |
