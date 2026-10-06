#!/usr/bin/env bash
# Endurecimiento del EQUIPO DE VOTACIÓN para operar sin red (propuesta §17, ISO/IEC 27002).
#
#   ⚠  NO ejecutar con --aplicar en la laptop de desarrollo: desactiva la red y cambia PostgreSQL.
#
#   scripts/hardening_offline.sh                       # SIMULACIÓN (por defecto): muestra lo que haría
#   sudo scripts/hardening_offline.sh --aplicar --confirmo-equipo-de-votacion [--admin USUARIO]
#
# Orden recomendado en el equipo de producción (con red todavía disponible):
#   1. Instalar Debian 13 con disco cifrado (LUKS) y sin entorno de escritorio.
#   2. Instalar el sistema (app, PostgreSQL, Docker, imágenes Fabric) y ejecutar configurar_kiosco.sh.
#   3. Ejecutar ESTE script (instala auditd/nftables y al final corta la red).
set -euo pipefail

APLICAR=false
CONFIRMADO=false
ADMIN="${SUDO_USER:-${USER:-admin}}"
PG_VERSION="$(ls /etc/postgresql 2>/dev/null | sort -n | tail -1 || true)"
PG_VERSION="${PG_VERSION:-17}"
while [ $# -gt 0 ]; do
  case "$1" in
    --aplicar) APLICAR=true ;;
    --confirmo-equipo-de-votacion) CONFIRMADO=true ;;
    --admin) ADMIN="$2"; shift ;;
    *) echo "Opción desconocida: $1"; exit 2 ;;
  esac
  shift
done
if $APLICAR; then
  $CONFIRMADO || { echo "Para aplicar, agregue --confirmo-equipo-de-votacion (solo en el equipo de votación)."; exit 2; }
  [ "$(id -u)" -eq 0 ] || { echo "Ejecutar con sudo"; exit 1; }
  echo "### APLICANDO el endurecimiento (administrador de BD: $ADMIN)"
else
  echo "### SIMULACIÓN: no se modifica nada. Use --aplicar --confirmo-equipo-de-votacion para aplicar."
fi

paso() { printf '\n==> %s\n' "$*"; }
hacer() { if $APLICAR; then "$@"; else printf '  [simulación] %s\n' "$*"; fi; }
escribir() {   # escribir RUTA  (contenido por entrada estándar); respalda el archivo anterior
  local ruta="$1" contenido
  contenido="$(cat)"
  if $APLICAR; then
    install -d "$(dirname "$ruta")"
    [ -f "$ruta" ] && [ ! -f "$ruta.antes-votoseguro" ] && cp -a "$ruta" "$ruta.antes-votoseguro"
    printf '%s\n' "$contenido" > "$ruta"
  else
    printf '  [simulación] escribir %s:\n%s\n' "$ruta" "$(sed 's/^/      │ /' <<<"$contenido")"
  fi
}
desactivar() {   # desactivar SERVICIO… (solo los que existen)
  for s in "$@"; do
    if systemctl list-unit-files "$s.service" 2>/dev/null | grep -q "^$s.service"; then
      hacer systemctl disable --now "$s.service"
    fi
  done
}

paso "1. Paquetes de seguridad (antes de cortar la red)"
hacer apt-get install -y auditd nftables apparmor apparmor-utils

paso "2. Sin acceso remoto: se elimina el servidor SSH"
if dpkg -s openssh-server >/dev/null 2>&1; then
  hacer apt-get purge -y openssh-server
else
  echo "  openssh-server no está instalado"
fi

paso "3. PostgreSQL de producción: solo socket Unix, auditoría y sin WAL archivado (ADR-008)"
escribir "/etc/postgresql/$PG_VERSION/main/conf.d/votoseguro-produccion.conf" <<CONF
# VOTO SEGURO — producción (generado por hardening_offline.sh)
listen_addresses = ''                 # sin TCP: solo socket Unix
password_encryption = scram-sha-256
wal_level = minimal                   # sin réplicas ni archivo de WAL (secreto del voto, ADR-008)
max_wal_senders = 0
archive_mode = off
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %u@%d '
shared_preload_libraries = 'pgaudit'
pgaudit.log = 'ddl, role, write'
pgaudit.log_parameter = off           # nunca registrar valores (secreto del voto)
CONF
escribir "/etc/postgresql/$PG_VERSION/main/pg_hba.conf" <<HBA
# VOTO SEGURO — solo conexiones locales por socket, identidad del sistema operativo (peer)
local   all         postgres                peer
local   votoseguro  all                     peer map=votoseguro
HBA
escribir "/etc/postgresql/$PG_VERSION/main/pg_ident.conf" <<IDENT
# MAPA        USUARIO-SO    ROL-BD
votoseguro    kiosco        vs_app
votoseguro    $ADMIN        vs_admin_bd
votoseguro    $ADMIN        vs_auditor
IDENT
hacer systemctl restart postgresql

paso "4. Parámetros del núcleo"
escribir /etc/sysctl.d/90-votoseguro.conf <<SYSCTL
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.unprivileged_bpf_disabled = 1
kernel.yama.ptrace_scope = 2
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.suid_dumpable = 0
SYSCTL
hacer sysctl --system

paso "5. Auditoría del sistema (auditd): quién tocó la BD, la aplicación o el llavero"
escribir /etc/audit/rules.d/votoseguro.rules <<REGLAS
-w /etc/postgresql/ -p wa -k votoseguro_bd
-w /opt/votoseguro/ -p wa -k votoseguro_app
-w /home/kiosco/.local/share/votoseguro/ -p rwa -k votoseguro_llavero
-w /etc/sudoers -p wa -k privilegios
-w /etc/sudoers.d/ -p wa -k privilegios
-w /usr/bin/sudo -p x -k privilegios
REGLAS
hacer augenrules --load
hacer systemctl enable --now auditd

paso "6. Cortafuegos (nftables): nada entra ni sale salvo la red interna de Fabric"
escribir /etc/nftables.conf <<'NFT'
#!/usr/sbin/nft -f
# Solo se reemplaza la tabla propia: NO se usa "flush ruleset", que borraría las reglas de Docker
# (red interna de Fabric).
table inet votoseguro
delete table inet votoseguro
table inet votoseguro {
  chain entrada {
    type filter hook input priority 0; policy drop;
    iif "lo" accept
    ct state established,related accept
    iifname "docker0" accept
    iifname "br-*" accept
  }
  chain salida {
    type filter hook output priority 0; policy drop;
    oif "lo" accept
    ct state established,related accept
    oifname "docker0" accept
    oifname "br-*" accept
  }
}
NFT
hacer systemctl enable --now nftables

paso "7. Sin red inalámbrica ni Bluetooth (módulos bloqueados) y sin servicios de red"
escribir /etc/modprobe.d/votoseguro-sin-red.conf <<'MOD'
# VOTO SEGURO: el equipo de votación opera sin red (RNF01)
install bluetooth /bin/false
install btusb /bin/false
blacklist iwlwifi
blacklist iwlmvm
blacklist ath9k
blacklist ath10k_pci
blacklist ath11k_pci
blacklist brcmfmac
blacklist rtw88_pci
blacklist rtw89_pci
blacklist mt7921e
MOD
if command -v rfkill >/dev/null 2>&1; then hacer rfkill block all; fi
desactivar NetworkManager wpa_supplicant ModemManager avahi-daemon cups-browsed bluetooth

paso "8. AppArmor"
if command -v aa-enabled >/dev/null 2>&1; then
  echo "  AppArmor activo: $(aa-enabled 2>/dev/null || echo no)"
else
  echo "  aa-enabled no disponible (se instala en el paso 1)"
fi

cat <<'MANUAL'

==> 9. Lista de verificación MANUAL (no se puede automatizar)
  [ ] Disco cifrado con LUKS (se elige al instalar Debian)
  [ ] Contraseña de BIOS/UEFI; arranque solo desde el disco interno; Secure Boot si está disponible
  [ ] Cable de red desconectado; antenas Wi-Fi retiradas si es posible
  [ ] Etiquetas de seguridad (tamper-evident) en puertos libres, tapa y tornillos
  [ ] Hash del paquete instalado anotado e impreso en la zerésima (comparar con el publicado)
  [ ] Reiniciar el equipo y comprobar: `ip link` sin interfaces activas salvo lo/docker
MANUAL
