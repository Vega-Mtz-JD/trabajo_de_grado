# Scripts de instalación y operación

| Script | Propósito | Sprint |
|---|---|---|
| `instalar_dependencias.sh` | Paquetes Debian, venv Python, Go, imágenes Fabric | 1–3 |
| `instalar_bd_desarrollo.sh` | Roles, BD `votoseguro`, esquema y pgaudit en el PostgreSQL local | 1 |
| `instalar_pgadmin.sh` | pgAdmin 4 (cliente gráfico oficial de PostgreSQL) | 1 |
| `hardening_offline.sh` | Endurecimiento sin red del equipo de votación (simula por defecto) | 6 |
| `configurar_kiosco.sh` | Usuario `kiosco`, sway con dos monitores, Fabric y puente como servicios (simula por defecto) | 6 |
| `respaldo_bd.sh` | Respaldo cifrado (gpg AES-256) de la BD y restauración de prueba | 6 |
