#!/usr/bin/env bash
# Instala pgAdmin 4 (modo escritorio) desde el repositorio oficial de pgadmin.org.
#   sudo scripts/instalar_pgadmin.sh
# pgAdmin es el cliente gráfico oficial de PostgreSQL: permite ver esquemas, tablas, datos,
# ejecutar consultas y generar el diagrama entidad-relación (Herramientas → ERD).
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecutar con sudo"; exit 1; }

. /etc/os-release   # VERSION_CODENAME (trixie en Debian 13)
LLAVE=/usr/share/keyrings/packages-pgadmin-org.gpg

echo "==> Llave del repositorio de pgAdmin"
curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | gpg --dearmor --yes -o "$LLAVE"

echo "==> Repositorio para $VERSION_CODENAME"
echo "deb [signed-by=$LLAVE] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$VERSION_CODENAME pgadmin4 main" \
  > /etc/apt/sources.list.d/pgadmin4.list

apt-get update
apt-get install -y pgadmin4-desktop

echo
echo "Listo. Abre 'pgAdmin 4' desde el menú de aplicaciones."
echo "Conexión a la BD del proyecto (sin contraseña, por socket local):"
echo "  Host: /var/run/postgresql   Puerto: 5432   BD: votoseguro   Usuario: ${SUDO_USER:-$(logname)}"
