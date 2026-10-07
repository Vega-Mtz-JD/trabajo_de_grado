# Anexo D. Manual técnico {.unnumbered}

## 0. Alcance de este manual

Este manual está dirigido al **personal técnico** que instala, configura y mantiene VOTO SEGURO. Las tareas del personal de mesa están en el *Manual de usuario y guía de capacitación*. Las decisiones de diseño se justifican en los registros `docs/decisiones/ADR-*.md`.

> **Estado de la versión actual (0.3.x):** la **cámara web es real** (Qt Multimedia; integrada o USB externa, elegible en la interfaz; si no hay cámara se usa la simulada). Solo se enciende a pedido del operador y al apagarse **libera el dispositivo** (`/dev/videoN`). La vista en vivo se dibuja en la propia ventana (sin `QVideoWidget`, que en Wayland abre ventanas sueltas). El lector se **conecta y desconecta** desde la interfaz (`abrir()`/`cerrar()` de `LectorHuella`, que corresponden a la apertura del dispositivo en el SDK de ZKTeco). El **lector de huella** y la **impresora** funcionan en **modo simulado**: la huella se simula (con una ventana que muestra la lectura) y lo impreso se guarda en PDF dentro de `salida_ui/impresiones/` (constancias de empadronamiento, hojas de custodios, zerésima, actas y urna de VVPAT). Los controladores del lector ZKTeco y de la impresora ESC/POS se incorporan cuando se adquiera el equipo (ADR-006).

## 1. Arquitectura en una página

```
┌──────────────────────── Equipo de votación (sin red) ─────────────────────────┐
│                                                                               │
│  Monitor de la mesa            Monitor de la cabina                           │
│  ┌──────────────────┐          ┌──────────────────┐                           │
│  │  Panel de mesa   │  sesión  │     Cabina       │   Lector de huella        │
│  │  (operador)      │ ───────► │   (votante)      │   Cámara · Impresora      │
│  └────────┬─────────┘          └────────┬─────────┘                           │
│           └────────── votoseguro-ui (Python + PySide6) ──────────┐            │
│                       │                              │            │            │
│        socket Unix    ▼                 HTTP local   ▼            │            │
│        ┌──────────────────────┐        ┌────────────────────┐     │            │
│        │ PostgreSQL 17        │        │ Puente Go          │     │            │
│        │ eleccion · padron ·  │        │ 127.0.0.1:8770     │     │            │
│        │ urna · auditoria ·   │        └─────────┬──────────┘     │            │
│        │ blockchain · meta    │                  │ gRPC/TLS       │            │
│        └──────────────────────┘        ┌─────────▼──────────────────────────┐ │
│                                        │ Docker: orderer · peer0 · acta (Go)│ │
│                                        │ Hyperledger Fabric 2.5 (canal       │ │
│                                        │ «elecciones»)                       │ │
│                                        └─────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
   Salidas físicas: zerésima, actas, comprobantes (VVPAT), hojas de custodios, USB (.vsx)
```

| Componente | Ubicación | Función |
|---|---|---|
| Aplicación | `app/src/votoseguro/` | Servicios del proceso electoral, criptografía, interfaz y línea de comandos |
| Base de datos | PostgreSQL 17, BD `votoseguro` | Padrón, urna, actas, bitácora, cola de anclajes; migraciones en `datos/migraciones/` |
| Cadena de bloques | `blockchain/network/` | Red Fabric de un nodo en Docker |
| Contrato inteligente | `blockchain/chaincode/acta/` | Valida y registra los 6 hitos de cada mesa |
| Puente | `blockchain/bridge/` | API REST local entre la aplicación y Fabric |
| Scripts | `scripts/` | Instalación, base de datos, kiosco, endurecimiento y respaldos |

## 2. Requisitos

### 2.1. Hardware

| Elemento | Mínimo | Recomendado |
|---|---|---|
| Procesador | x86-64 de 4 núcleos | 4 núcleos o más |
| Memoria RAM | 8 GB | 16 GB |
| Disco | 30 GB libres | SSD, cifrado con LUKS |
| Pantallas | 1 (pruebas) | 2: mesa y cabina (producción) |
| Periféricos | — | Lector ZKTeco ZK9500/SLK20R con SDK Linux, impresora térmica USB ESC/POS de 58/80 mm, cámara web, ratón para la cabina, UPS de 600–800 VA |

### 2.2. Software

| Software | Versión | Uso |
|---|---|---|
| Debian | 13 «Trixie» | Sistema operativo |
| Python | 3.13 | Aplicación |
| PostgreSQL | 17 + `postgresql-17-pgaudit` | Base de datos y auditoría |
| Docker + Docker Compose | 26 o superior | Contenedores de Fabric |
| Hyperledger Fabric | 2.5.16 (binarios e imágenes `peer`, `orderer`, `baseos`) | Registro distribuido |
| Go | ≥ 1.25 (se instala 1.26.8 en `~/.local/go`) | Compilar el chaincode y el puente |
| pandoc, LibreOffice | — | Exportar el informe y los manuales (solo desarrollo) |

### 2.3. Red

- **Instalación:** requiere Internet para descargar paquetes, imágenes y bibliotecas.
- **Operación:** **ninguna** conexión de red. En producción, el endurecimiento desactiva Wi-Fi, Bluetooth y SSH, y el cortafuegos bloquea todo el tráfico salvo la red interna de Docker.

## 3. Instalación desde cero (laboratorio o desarrollo)

### 3.1. Obtener el código

```bash
git clone https://github.com/<usuario>/trabajo_de_grado.git ~/Proyectos/trabajo_de_grado
cd ~/Proyectos/trabajo_de_grado
```

### 3.2. Dependencias

```bash
scripts/instalar_dependencias.sh
```

El script es idempotente (lo ya instalado se omite) y realiza:

1. Paquetes de Debian: Python, PostgreSQL 17 con pgaudit, Docker (solo si no está instalado), pandoc y LibreOffice. Si agrega el usuario al grupo `docker`, **hay que cerrar sesión y volver a entrar**.
2. Entorno Python en `app/.venv` con la aplicación y sus dependencias.
3. Go 1.26.8 en `~/.local/go` (verifica la suma SHA-256 oficial).
4. Binarios de Fabric 2.5.16 en `blockchain/network/bin` e imágenes Docker `hyperledger/fabric-{peer,orderer,baseos}:2.5.16`.

### 3.3. Base de datos

```bash
sudo scripts/instalar_bd_desarrollo.sh            # no borra datos existentes
# sudo scripts/instalar_bd_desarrollo.sh --recrear # SOLO si se quiere empezar de cero
```

Crea los roles, la BD `votoseguro`, la extensión pgaudit, un rol de PostgreSQL para el usuario de Linux y aplica las **migraciones** del esquema. Verificación:

```bash
cd app && . .venv/bin/activate
export VOTOSEGURO_DSN='dbname=votoseguro'
votoseguro bd estado          # 0001 esquema_inicial  APLICADA
psql -d votoseguro -c '\dn'   # eleccion, padron, urna, auditoria, blockchain, meta
```

Opcional, para ver la BD con una interfaz gráfica: `sudo scripts/instalar_pgadmin.sh` y conectar con *Host* `/var/run/postgresql`, puerto `5432`, BD `votoseguro` y el usuario de Linux, sin contraseña.

### 3.4. Hyperledger Fabric (opcional, recomendado)

```bash
blockchain/network/up.sh        # crea certificados, canal, chaincode; idempotente
blockchain/bridge/iniciar.sh    # puente en 127.0.0.1:8770
docker ps                       # orderer, peer0 y acta en ejecución
curl -s http://127.0.0.1:8770/salud   # {"estado":"ok"}
```

Sin Fabric, el sistema funciona igual y deja los anclajes **en cola** (modo degradado); se envían después con `votoseguro sincronizar`.

### 3.5. Demostración repetible en la interfaz

Para mostrar la votación sin empadronar a mano cada vez (requiere haber abierto la interfaz una vez, para que exista el llavero):

```bash
cd app && . .venv/bin/activate && export VOTOSEGURO_DSN='dbname=votoseguro'
votoseguro preparar-demo --votantes 5           # elección lista para abrir (pide la frase del llavero)
votoseguro preparar-demo --votantes 5 --abrir   # o ya abierta
```

Imprime los CI de los votantes de ejemplo y las partes de la clave para el escrutinio. Cada ejecución crea una elección nueva, que se elige en el selector superior del panel.

### 3.5.1. Prueba de humo

```bash
cd app && . .venv/bin/activate
votoseguro demo --mesas 2 --fabric     # elección simulada completa: debe terminar en CONFORME
pytest                                 # batería de pruebas (las de Fabric se omiten si la red está apagada)
```

### 3.6. Primer arranque de la interfaz

```bash
scripts/iniciar_votoseguro.sh             # comprueba PostgreSQL, la BD y el entorno, e inicia la interfaz
scripts/iniciar_votoseguro.sh --fabric    # además levanta Fabric y el puente si no están en ejecución
```

(Equivale a `cd app && . .venv/bin/activate && export VOTOSEGURO_DSN='dbname=votoseguro' && votoseguro-ui`.)

1. Se pide crear la **frase del llavero** del equipo (mínimo 12 caracteres). El llavero, en `~/.local/share/votoseguro/llavero.vsk`, contiene la clave de firma del equipo y la clave de los datos personales. **Si se pierde la frase, el equipo no puede leer las fotos y las huellas del padrón.** Guárdela en un sobre sellado.
2. Se crea la cuenta del **administrador**.
3. Con el administrador se crean las cuentas de los operadores y del auditor (menú **Usuarios**).

## 4. Instalación en el equipo de votación (producción)

Orden obligatorio, **con red** hasta el último paso:

1. Instalar Debian 13 **con disco cifrado (LUKS)** y sin entorno de escritorio.
2. Pasos 3.1 a 3.5 de este manual.
3. Conservar las imágenes de Fabric para operar sin Internet:
   `docker save hyperledger/fabric-{peer,orderer,baseos}:2.5.16 -o fabric-imagenes.tar`.
4. Identificar los monitores y el ratón de la cabina: `swaymsg -t get_outputs` y `swaymsg -t get_inputs` (dentro de una sesión de sway).
5. Modo kiosco con dos monitores (ADR-012). Primero **simular** y revisar, luego aplicar:
   ```bash
   scripts/configurar_kiosco.sh --salida-mesa eDP-1 --salida-cabina HDMI-A-1 --entrada-cabina "1133:49970:Mouse"
   sudo scripts/configurar_kiosco.sh --aplicar --salida-mesa … --salida-cabina … --entrada-cabina …
   ```
   Crea el usuario `kiosco` (sin privilegios ni contraseña), su inicio automático en tty1, la configuración cerrada de sway (panel y cabina a pantalla completa, cada uno en su monitor, y el ratón de la cabina confinado a su pantalla) y los servicios `votoseguro-fabric` y `votoseguro-puente`.
6. Endurecimiento (corta la red). Primero **simular**:
   ```bash
   scripts/hardening_offline.sh
   sudo scripts/hardening_offline.sh --aplicar --confirmo-equipo-de-votacion
   ```
   **No ejecutar con `--aplicar` en una laptop de desarrollo.**
7. Completar la lista manual que imprime el script: contraseña de BIOS, arranque solo desde el disco, Secure Boot, cable de red retirado y etiquetas de seguridad.
8. Reiniciar y comprobar: tty1 entra directo a VOTO SEGURO; `ip link` no muestra interfaces activas salvo `lo` y las de Docker.

**Mantenimiento en producción:** Ctrl+Alt+F2 y sesión del administrador. El botón **Salir** cierra la aplicación, que se vuelve a iniciar sola (es un kiosco).

## 5. Configuración

### 5.1. Variables de entorno

| Variable | Valor por defecto | Uso |
|---|---|---|
| `VOTOSEGURO_DSN` | `dbname=votoseguro user=vs_app` | Conexión a PostgreSQL (en desarrollo: `dbname=votoseguro`) |
| `VOTOSEGURO_PUENTE_URL` | `http://127.0.0.1:8770` | Dirección del puente |
| `VOTOSEGURO_PUENTE_TOKEN` | archivo `~/.config/votoseguro/puente.token` | Token compartido con el puente (lo crea `iniciar.sh`) |
| `QT_QPA_PLATFORM` | automático | `wayland` en producción; `xcb` si la cabina no pasa al frente en algún escritorio |

### 5.2. Opciones de `votoseguro-ui`

| Opción | Efecto |
|---|---|
| `--dsn CADENA` | Conexión a PostgreSQL |
| `--llavero RUTA` | Llavero del equipo (por defecto `~/.local/share/votoseguro/llavero.vsk`) |
| `--salida CARPETA` | Carpeta de la impresora simulada (por defecto `salida_ui/`) |
| `--kiosco` | Cabina a pantalla completa y sin bordes (producción) |
| `--fabric` | Anclar los hitos en Hyperledger Fabric |
| `--camara auto\|web\|simulada` | Cámara web real (por defecto, si existe) o simulada |

Con **un solo monitor**, la cabina se muestra **dentro de la ventana del panel** (a pantalla completa mientras se vota); con dos monitores, la cabina es una ventana propia en el segundo monitor.

### 5.3. Usuarios y roles

| Rol en la aplicación | Páginas | Rol en PostgreSQL |
|---|---|---|
| ADMIN | Todas | (la aplicación usa `vs_app`) |
| OPERADOR | Resumen, Empadronamiento, Jornada, Escrutinio | `vs_app` |
| AUDITOR | Resumen, Auditoría | `vs_app` / `vs_auditor` (solo lectura, sin fotos ni huellas) |

| Rol de PostgreSQL | Permisos |
|---|---|
| `vs_propietario` | Dueño de los objetos. Nadie inicia sesión con él |
| `vs_app` | Solo lo necesario: vota mediante la función `urna.emitir_voto()`; no puede modificar ni borrar votos, actas ni bitácora |
| `vs_auditor` | Solo lectura, sin columnas de fotos ni plantillas |
| `vs_admin_bd` | Migraciones (asume `vs_propietario` sin heredar sus privilegios) y respaldos |

### 5.4. Parámetros de una elección

| Parámetro | Valor por defecto | Observación |
|---|---|---|
| Custodios necesarios / totales | 3 de 5 | Si se pierden más de 2 partes, los votos digitales no pueden contarse (queda el papel) |
| Checkpoint cada N votos | 10 (mínimo 10) | Cada checkpoint mezcla la urna y ancla la raíz de Merkle. N también es el tamaño mínimo del grupo de anonimato |
| Mesas | 01 | Códigos de mesa separados por comas |

### 5.5. Archivos y ubicaciones

| Elemento | Ubicación |
|---|---|
| Llavero del equipo | `~/.local/share/votoseguro/llavero.vsk` (permisos 600) |
| Impresiones simuladas | `salida_ui/impresiones/` (zerésima, actas, hojas de custodios, urna de VVPAT mezclada) |
| Token del puente | `~/.config/votoseguro/puente.token` (permisos 600) |
| Certificados de Fabric | `blockchain/network/organizations/` (no se versiona) |
| Ledger | Volúmenes Docker `votoseguro-fabric_orderer` y `votoseguro-fabric_peer0` |
| Bitácora de la BD (pgaudit) | Registro de PostgreSQL (`/var/log/postgresql/`) |

## 6. Importaciones y exportaciones

| Archivo | Lo genera | Contenido | Protección | Lo usa |
|---|---|---|---|---|
| Hoja de custodio (papel) `VS1-…` | Instalar mesa | Una parte (Shamir) de la clave que abre la urna digital | Sobre sellado; suma de verificación contra errores de transcripción | Escrutinio (≥ 3 partes) |
| `definicion.vsd` | Configuración → **Exportar definición** | Nombre, opciones, mesas, umbral y sal del padrón. **Sin datos personales** | AES-256-GCM con frase (Argon2id) + firma RSA-PSS del equipo creador + hoja de control impresa | Otras urnas → **Importar definición** |
| `padron_mesaNN.vsp` | Empadronamiento → **Exportar resumen** | CI y nombres de los habilitados (sin fotos ni huellas) | Cifrado con frase + firma del equipo | **Cruzar padrones** |
| `votoseguro_<id>_mesaNN.vsx` | Escrutinio → **Exportar el paquete** | Elección, votos cifrados, padrón con participación, actas firmadas, checkpoints, bitácora, cola de anclajes y clave pública del equipo, con un manifiesto SHA3 firmado | Cifrado con frase + manifiesto firmado | Auditoría y consolidación |
| Informe de auditoría (PDF) | Auditoría → **Guardar el informe** | Resultado de las comprobaciones | — | Comité electoral |
| `votoseguro_AAAAMMDD_HHMM.dump.gpg` | `scripts/respaldo_bd.sh` | Respaldo completo de la BD | gpg AES-256 con frase + suma `.sha256` | Restauración |

### 6.1. Procedimiento con varias urnas

1. **Urna 1 (administrador):** Configuración → crear la elección con todas las mesas (p. ej. `01, 02, 03`) → **Instalar mesa** `01` → **Exportar definición** a un USB. Se imprime la *hoja de control* con el hash de la definición y la huella del equipo.
2. **Urnas 2 y 3:** **Importar definición** con la frase y la **huella de la hoja de control** → instalar la mesa `02` o `03`. Cada urna genera **su propia clave** y sus custodios.
3. **Cada urna:** empadronar → **Exportar resumen** del padrón al USB.
4. **Una urna:** **Cruzar padrones** con todos los `.vsp` → por cada CI duplicado, **Inhabilitar** en todas las mesas menos una (con motivo) → volver a exportar y cruzar hasta que no haya duplicados.
5. **Cada urna:** **Cerrar el padrón** → jornada → cierre → escrutinio con sus custodios → **Exportar paquete**.
6. **Auditor:** Auditoría (o `votoseguro consolidar *.vsx --frase … --fabric`): verifica cada mesa, exige la misma definición y todas las mesas, detecta a quien haya votado en dos mesas y suma los resultados.

## 7. Operación (ciclo de una elección)

La elección pasa por estados que la base de datos y el contrato inteligente obligan a respetar:

```
CONFIGURACION → EMPADRONAMIENTO → LISTA → ABIERTA → CERRADA → ESCRUTADA → EXPORTADA
```

| Estado | Qué se puede hacer | Evidencia generada |
|---|---|---|
| CONFIGURACION | Instalar la mesa, iniciar el empadronamiento | Hojas de custodios; anclaje `RegistrarEleccion` |
| EMPADRONAMIENTO | Registrar, inhabilitar, exportar resumen, cruzar, cerrar el padrón | Bitácora `VOTANTE_REGISTRADO` |
| LISTA | Abrir la mesa | Zerésima firmada; anclaje `RegistrarApertura` |
| ABIERTA | Identificar, votar, reimprimir, liberar la cabina, cerrar | VVPAT; checkpoints cada N votos |
| CERRADA | Escrutar con los custodios | Acta de cierre, lista de ausentes |
| ESCRUTADA | Exportar el paquete | Acta de escrutinio |
| EXPORTADA | Auditar y consolidar | Paquete `.vsx`; anclaje `RegistrarExportacion` |

## 8. Seguridad

### 8.1. Capas

| Capa | Medidas |
|---|---|
| **Física** | Equipo con etiquetas de seguridad, UPS, disco cifrado (LUKS), contraseña de BIOS, cabina con biombo, urna de papel sellada |
| **Red** | Sin red: Wi-Fi y Bluetooth bloqueados en el núcleo, sin SSH, cortafuegos con política de descarte; PostgreSQL solo por socket local; puente solo en 127.0.0.1 con token |
| **Sistema operativo** | Usuario `kiosco` sin privilegios, compositor cerrado sin atajos, ratón de la cabina confinado, parámetros del núcleo endurecidos, AppArmor, auditd vigilando la BD, la aplicación y el llavero |
| **Aplicación** | Contraseñas Argon2id; bloqueo de 5 min tras 3 intentos; salida solo con contraseña; páginas según el rol; todo evento en la bitácora |
| **Base de datos** | Mínimo privilegio por esquema y columna; votos, actas y bitácora de solo inserción (ni el superusuario los modifica sin desactivar los disparadores); máquina de estados en disparadores; pgaudit sin registrar valores |
| **Cadena de bloques** | Contrato inteligente que solo acepta hitos en orden y coherentes; cada cambio de código del contrato exige una nueva secuencia del ciclo de vida; sin datos personales en el ledger |

### 8.2. Criptografía

| Uso | Algoritmo |
|---|---|
| Cifrado de cada voto | AES-256-GCM con clave de un solo uso, envuelta con RSA-3072-OAEP (clave pública de la elección); texto de longitud fija |
| Custodia de la clave de la elección | Secreto compartido de Shamir sobre GF(2⁸), 3 de 5 |
| Fotos y huellas | AES-256-GCM con la clave de datos del llavero; el tipo, la elección y el CI se autentican junto al dato |
| Firmas (zerésima, actas, manifiestos, definición) | RSA-2048-PSS con SHA-256 |
| Resúmenes | SHA3-256; árbol de Merkle con prefijos de dominio |
| Archivos protegidos con frase | Argon2id → AES-256-GCM |
| Contraseñas | Argon2id |

### 8.3. Secreto del voto

- La urna (`urna.voto`) no tiene fecha, hora ni orden; el identificador del voto es aleatorio.
- El padrón solo registra **si** la persona votó, nunca **cuándo**.
- La bitácora registra «voto emitido n.º k», sin la opción ni el identificador del voto.
- Cada N votos, la urna se **mezcla**: se reescribe en orden aleatorio, lo que borra el orden de inserción que PostgreSQL guarda internamente (`xmin`, posición física). La mezcla verifica que el contenido no cambie.
- El VVPAT no lleva hora ni datos del votante; su código permite cotejar el papel con la urna digital sin revelar identidades.
- **Riesgo residual documentado:** entre dos mezclas, un atacante con acceso de superusuario al disco durante la jornada podría acotar el voto de una persona a un grupo de N votos. Se mitiga con la custodia de la contraseña del superusuario, la presencia de delegados y el borrado seguro de la instancia tras la exportación.

### 8.4. Integridad y auditoría triple

| Nivel | Evidencia | Qué detecta |
|---|---|---|
| Papel | Comprobantes en la urna, zerésima y actas firmadas por los delegados | Votos digitales agregados o quitados; equipo cambiado (huella) |
| USB | Paquete con manifiesto firmado, bitácora encadenada, raíz de Merkle y actas firmadas | Votos, actas o bitácora alterados, aunque se rehaga el manifiesto |
| Ledger | Hitos anclados en Fabric | Base de datos regenerada después de anclar los hitos |

### 8.5. Lo que el sistema NO protege

- Una red de Fabric de un solo nodo no impide que quien controla el equipo reconstruya el ledger: por eso el hash final se ancla además en **papel firmado**.
- La coacción del votante fuera de la cabina y la compra de votos son problemas organizativos; el sistema los dificulta (el votante no se lleva el comprobante), pero no los elimina.
- Las firmas del sistema no tienen valor legal (requerirían un certificado de una entidad certificadora autorizada).

## 9. Mantenimiento

| Tarea | Procedimiento |
|---|---|
| Actualizar el esquema | `votoseguro bd estado` y `votoseguro bd migrar`. Los cambios de esquema se escriben como **migraciones nuevas**; nunca se edita una migración aplicada (el sistema lo detecta) |
| Respaldo de la BD | `sudo scripts/respaldo_bd.sh /media/USB` (pide una frase) |
| Probar un respaldo | `sudo scripts/respaldo_bd.sh --restaurar ARCHIVO.dump.gpg` → BD `votoseguro_restaurada` |
| Verificar la bitácora | `votoseguro verificar-bitacora [--ultimo-hash HASH_DEL_ACTA]` |
| Anclajes pendientes | `votoseguro sincronizar`; estado de una mesa: `votoseguro ledger <eleccion_global> <mesa>` |
| Actualizar el chaincode | Cambiar el código y ejecutar `blockchain/network/up.sh`: detecta el cambio y aprueba una nueva secuencia |
| Detener Fabric | `blockchain/bridge/detener.sh` y `blockchain/network/down.sh` (conserva el ledger; `--borrar` lo elimina) |
| Revisar accesos del sistema | `sudo ausearch -k votoseguro_bd` (también `votoseguro_app`, `votoseguro_llavero`) |
| Después del proceso electoral | Conservar el paquete `.vsx` y las actas según el reglamento; borrar la BD de la elección y el llavero según la política de retención de datos personales de la institución |

## 10. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| «sudo: a terminal is required…» | Se ejecutó un comando con `sudo` desde un entorno sin terminal | Ejecutarlo en una terminal normal |
| «Permiso denegado» al leer un `.sql` con psql | El usuario `postgres` no puede leer `/home/<usuario>` | Usar los scripts del proyecto (pasan el SQL por entrada estándar) |
| «no existe el rol …» | No se completó la instalación de la BD | `sudo scripts/instalar_bd_desarrollo.sh` |
| «Migración … modificada» | Se editó una migración ya aplicada | Restaurar el archivo original (git) y crear una migración nueva |
| «Fabric no disponible», anclajes en cola | Red o puente detenidos | `up.sh` + `iniciar.sh`; luego `votoseguro sincronizar` |
| La consulta al chaincode queda esperando | El contenedor `acta` corre con un identificador de paquete distinto | Ejecutar `up.sh` (actualiza la secuencia y reinicia `acta`) |
| La cabina no pasa al frente | Escritorio que impide activar ventanas | Pulsar de nuevo «Habilitar la cabina»; probar `QT_QPA_PLATFORM=xcb`; en producción usar sway |
| Lector, cámara o impresora en rojo | Periférico desconectado | Reconectar y volver a la página Jornada |
| «Frase incorrecta» al abrir el llavero | Frase equivocada | Tres intentos por arranque; sin la frase no se pueden leer fotos ni huellas |

## 11. Referencia de comandos

| Comando | Descripción |
|---|---|
| `votoseguro-ui [--fabric] [--kiosco]` | Interfaz gráfica |
| `votoseguro demo [--mesas N] [--votantes N] [--fabric]` | Elección simulada completa |
| `votoseguro preparar-demo [--votantes N] [--abrir]` | Elección lista para mostrar en la interfaz |
| `scripts/iniciar_votoseguro.sh [--fabric] [--camara-simulada]` | Iniciar la interfaz comprobando requisitos |
| `votoseguro verificar PAQUETE --frase F [--papel A=…] [--huella H] [--fabric]` | Auditoría triple de un paquete |
| `votoseguro consolidar P1 P2 … --frase F [--fabric]` | Consolidación de mesas |
| `votoseguro verificar-bitacora [--ultimo-hash H]` | Integridad de la bitácora |
| `votoseguro sincronizar` | Enviar anclajes pendientes a Fabric |
| `votoseguro ledger GLOBAL MESA` | Estado anclado e historial de una mesa |
| `votoseguro bd estado` · `votoseguro bd migrar` | Migraciones del esquema |
| `scripts/instalar_dependencias.sh` | Instalación de dependencias desde cero |
| `sudo scripts/instalar_bd_desarrollo.sh [--recrear]` | Roles, BD y migraciones |
| `blockchain/network/up.sh` · `down.sh [--borrar]` | Red Fabric |
| `blockchain/bridge/iniciar.sh` · `detener.sh` | Puente Go |
| `scripts/configurar_kiosco.sh [--aplicar …]` | Modo kiosco de producción |
| `scripts/hardening_offline.sh [--aplicar --confirmo-equipo-de-votacion]` | Endurecimiento sin red |
| `sudo scripts/respaldo_bd.sh DESTINO` · `--restaurar ARCHIVO` | Respaldo cifrado |
