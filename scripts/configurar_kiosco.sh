#!/usr/bin/env bash
# Configura el EQUIPO DE VOTACIÓN en modo kiosco con dos monitores (ADR-012):
#   * usuario "kiosco" sin privilegios con inicio automático en tty1;
#   * sway con una configuración cerrada: panel de mesa a pantalla completa en el monitor de la mesa y
#     cabina a pantalla completa en el monitor de la cabina; el ratón/teclado de la cabina en su propio
#     "seat" confinado a ese monitor (el votante no puede alcanzar el panel);
#   * la aplicación instalada en /opt/votoseguro.
#
#   scripts/configurar_kiosco.sh                         # SIMULACIÓN (por defecto)
#   sudo scripts/configurar_kiosco.sh --aplicar --salida-mesa eDP-1 --salida-cabina HDMI-A-1 \
#        --entrada-cabina "1234:5678:Mouse_USB" [--entrada-cabina ...]
#
# Los nombres de monitores y dispositivos se obtienen en el equipo con:
#   swaymsg -t get_outputs     y     swaymsg -t get_inputs   (campo "identifier")
set -euo pipefail

APLICAR=false
SALIDA_MESA="eDP-1"
SALIDA_CABINA="HDMI-A-1"
ENTRADAS_CABINA=()
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO=/opt/votoseguro
while [ $# -gt 0 ]; do
  case "$1" in
    --aplicar) APLICAR=true ;;
    --salida-mesa) SALIDA_MESA="$2"; shift ;;
    --salida-cabina) SALIDA_CABINA="$2"; shift ;;
    --entrada-cabina) ENTRADAS_CABINA+=("$2"); shift ;;
    *) echo "Opción desconocida: $1"; exit 2 ;;
  esac
  shift
done
if $APLICAR; then
  [ "$(id -u)" -eq 0 ] || { echo "Ejecutar con sudo"; exit 1; }
  [ ${#ENTRADAS_CABINA[@]} -gt 0 ] || { echo "Indique al menos un --entrada-cabina (ratón de la cabina)"; exit 2; }
else
  echo "### SIMULACIÓN: no se modifica nada. Use --aplicar para aplicar."
fi
[ ${#ENTRADAS_CABINA[@]} -gt 0 ] || ENTRADAS_CABINA=("RATON_DE_LA_CABINA")

paso() { printf '\n==> %s\n' "$*"; }
hacer() { if $APLICAR; then "$@"; else printf '  [simulación] %s\n' "$*"; fi; }
escribir() {
  local ruta="$1" contenido
  contenido="$(cat)"
  if $APLICAR; then
    install -d "$(dirname "$ruta")"
    printf '%s\n' "$contenido" > "$ruta"
  else
    printf '  [simulación] escribir %s:\n%s\n' "$ruta" "$(sed 's/^/      │ /' <<<"$contenido")"
  fi
}

paso "1. Paquetes del kiosco (con red, antes del endurecimiento)"
hacer apt-get install -y sway python3-venv

paso "2. Usuario 'kiosco' sin privilegios y sin contraseña (solo inicio automático)"
if ! id kiosco >/dev/null 2>&1; then
  hacer useradd --create-home --shell /bin/bash --comment "VOTO SEGURO kiosco" kiosco
fi
hacer passwd --lock kiosco

paso "3. Aplicación en $DESTINO (entorno Python propio)"
hacer python3 -m venv "$DESTINO/venv"
hacer "$DESTINO/venv/bin/pip" install "$RAIZ/app[ui]"

paso "4. Inicio automático del usuario kiosco en tty1"
escribir /etc/systemd/system/getty@tty1.service.d/votoseguro.conf <<'GETTY'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin kiosco --noclear %I $TERM
GETTY
escribir /home/kiosco/.bash_profile <<'PERFIL'
# Solo en tty1: inicia el compositor de kiosco. En otras terminales, sesión normal.
if [ "$(tty)" = "/dev/tty1" ]; then
  exec sway --config /etc/votoseguro/sway.conf
fi
PERFIL
hacer chown kiosco:kiosco /home/kiosco/.bash_profile

paso "5. Hyperledger Fabric y puente como servicios del sistema (arrancan al encender)"
hacer cp -a "$RAIZ/blockchain" "$DESTINO/blockchain"
hacer chown -R kiosco:kiosco "$DESTINO/blockchain"    # el puente (usuario kiosco) lee la identidad cliente
hacer install -d -o kiosco -g kiosco -m 700 /home/kiosco/.config/votoseguro
escribir /etc/systemd/system/votoseguro-fabric.service <<UNIDAD
[Unit]
Description=VOTO SEGURO: red Hyperledger Fabric local
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=VOTOSEGURO_SIN_COMPILAR=1
ExecStart=$DESTINO/blockchain/network/up.sh

[Install]
WantedBy=multi-user.target
UNIDAD
escribir /etc/systemd/system/votoseguro-puente.service <<UNIDAD
[Unit]
Description=VOTO SEGURO: puente Go entre la aplicación y Fabric (127.0.0.1:8770)
After=votoseguro-fabric.service
Requires=votoseguro-fabric.service

[Service]
User=kiosco
ExecStart=$DESTINO/blockchain/bridge/iniciar.sh --primer-plano
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIDAD
hacer systemctl enable votoseguro-fabric.service votoseguro-puente.service

paso "6. Configuración cerrada de sway (dos monitores, seat de la cabina)"
{
  cat <<SWAY
# VOTO SEGURO — compositor de kiosco (generado por configurar_kiosco.sh, ADR-012)
# Sin barra, sin atajos de terminal ni de salida. El personal sale con el botón «Salir» del panel
# (pide contraseña); al salir, la sesión se reinicia sola (es un kiosco).
default_border none
default_floating_border normal
focus_follows_mouse no
output * bg #ffffff solid_color
output $SALIDA_MESA pos 0 0
output $SALIDA_CABINA pos 10000 0

# Ratón/teclado de la cabina: seat propio, confinado al monitor de la cabina
SWAY
  for entrada in "${ENTRADAS_CABINA[@]}"; do
    echo "seat cabina attach \"$entrada\""
    echo "input \"$entrada\" map_to_output $SALIDA_CABINA"
  done
  cat <<SWAY

for_window [title="^VOTO SEGURO — Panel de mesa\$"] move container to output $SALIDA_MESA, fullscreen enable
for_window [title="^VOTO SEGURO — Cabina de votación\$"] move container to output $SALIDA_CABINA, fullscreen enable

exec sh -c 'QT_QPA_PLATFORM=wayland VOTOSEGURO_DSN="dbname=votoseguro user=vs_app" $DESTINO/venv/bin/votoseguro-ui --kiosco --fabric; swaymsg exit'
SWAY
} | escribir /etc/votoseguro/sway.conf
hacer systemctl daemon-reload

cat <<FIN

==> Listo. Al reiniciar, tty1 entra directo a VOTO SEGURO.
  * Mesa:   $SALIDA_MESA     Cabina: $SALIDA_CABINA     Entradas de la cabina: ${ENTRADAS_CABINA[*]}
  * Mantenimiento: Ctrl+Alt+F2 y sesión del administrador (la cabina debe usar solo ratón o teclado numérico).
  * Luego ejecute scripts/hardening_offline.sh para cortar la red.
FIN
