#!/usr/bin/env bash
# Instala la base de datos "votoseguro" en el PostgreSQL del sistema, para DESARROLLO.
#
#   sudo scripts/instalar_bd_desarrollo.sh            # instala (idempotente: no borra datos)
#   sudo scripts/instalar_bd_desarrollo.sh --recrear  # borra y vuelve a crear la BD
#
# Qué hace:
#   1. Activa pgaudit (shared_preload_libraries) y reinicia PostgreSQL.
#   2. Crea los roles (vs_propietario, vs_app, vs_auditor, vs_admin_bd).
#   3. Crea la BD votoseguro (si no existe) y la extensión pgaudit.
#   4. Crea un rol para tu usuario de Linux (miembro de vs_app, vs_auditor y vs_admin_bd), para conectarte
#      con psql o pgAdmin y para aplicar migraciones.
#   5. Aplica las migraciones pendientes del esquema (app/src/votoseguro/datos/migraciones/).
#      Una BD ya instalada se reconoce como "línea base": NO se borran datos.
#
# En DESARROLLO PostgreSQL escucha en localhost (por defecto en Debian). La configuración de
# PRODUCCIÓN (sin TCP, solo socket Unix) la aplica scripts/hardening_offline.sh (Sprint 5).
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Ejecutar con sudo"; exit 1; }
USUARIO="${SUDO_USER:-$(logname)}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SQL="$RAIZ/app/src/votoseguro/datos"
VERSION="$(ls /etc/postgresql | sort -n | tail -1)"
CONF="/etc/postgresql/$VERSION/main/conf.d/votoseguro.conf"

echo "==> PostgreSQL $VERSION: configurando pgaudit en $CONF"
cat > "$CONF" <<CONFIG
# VOTO SEGURO (desarrollo) — ver docs/decisiones/ADR-008-postgresql.md
shared_preload_libraries = 'pgaudit'
pgaudit.log = 'ddl, role, write'
pgaudit.log_parameter = off      # nunca registrar valores (secreto del voto)
pgaudit.log_relation = on
CONFIG
systemctl restart postgresql

# Los .sql se pasan por entrada estándar (los lee root): el usuario postgres no puede leer
# archivos dentro de /home/<usuario>, que tiene permisos 700.
# Los .sql se pasan por entrada estándar (los lee root): el usuario postgres no puede leer
# archivos dentro de /home/<usuario>, que tiene permisos 700. Se cambia a / para evitar el
# aviso "no se pudo cambiar al directorio" de psql.
psql_pg() { (cd / && sudo -u postgres psql -v ON_ERROR_STOP=1 -q "$@"); }

echo "==> Roles"
psql_pg < "$SQL/roles.sql"

if [ "${1:-}" = "--recrear" ]; then
  echo "==> Borrando la BD votoseguro"
  psql_pg -c "DROP DATABASE IF EXISTS votoseguro WITH (FORCE)"
fi

if ! psql_pg -tAc "SELECT 1 FROM pg_database WHERE datname = 'votoseguro'" | grep -q 1; then
  echo "==> Creando la BD votoseguro"
  psql_pg -c "CREATE DATABASE votoseguro ENCODING 'UTF8' TEMPLATE template0"
fi
psql_pg -d votoseguro -c "CREATE EXTENSION IF NOT EXISTS pgaudit"
psql_pg -c "GRANT CREATE ON DATABASE votoseguro TO vs_propietario"

echo "==> Rol de desarrollo para el usuario '$USUARIO'"
psql_pg <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$USUARIO') THEN
    CREATE ROLE "$USUARIO" LOGIN;
  END IF;
END \$\$;
-- vs_admin_bd permite aplicar migraciones (SET ROLE vs_propietario) sin heredar privilegios de dueño
GRANT vs_app, vs_auditor, vs_admin_bd TO "$USUARIO";
SQL

echo "==> Migraciones del esquema (ADR-011)"
VOTOSEGURO_BIN="$RAIZ/app/.venv/bin/votoseguro"
[ -x "$VOTOSEGURO_BIN" ] || { echo "Falta el entorno Python: cd app && python3 -m venv .venv && pip install -e ."; exit 1; }
sudo -u "$USUARIO" env VOTOSEGURO_DSN="dbname=votoseguro" "$VOTOSEGURO_BIN" bd migrar

echo
echo "Listo. Prueba:  psql -d votoseguro -c '\\dn'"
echo "Para la aplicación en desarrollo:  export VOTOSEGURO_DSN='dbname=votoseguro'"
echo "Para DBeaver/pgAdmin (conexión TCP a localhost) asigna una contraseña:"
echo "  sudo -u postgres psql -c \"ALTER ROLE $USUARIO PASSWORD 'tu-clave'\""
