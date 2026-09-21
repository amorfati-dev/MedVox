#!/bin/bash
# Entfernt den Caddy-Dienst. Zertifikate bleiben; mit --purge werden auch
# ~/Library/Application Support/MedVox/tls und caddy gelöscht. Die Praxis-CA
# im Schlüsselbund entfernt `mkcert -uninstall` (bewusst nicht automatisch).

source "$(dirname "$0")/../common.sh"
PLIST="$LAUNCH_AGENTS/$CADDY_LABEL.plist"

log "Dienst $CADDY_LABEL stoppen und entladen"
launchd_unload "$CADDY_LABEL"
if [[ -f "$PLIST" ]]; then rm -f "$PLIST"; ok "$PLIST entfernt"; else ok "kein Agent installiert"; fi

if [[ "${1:-}" == "--purge" ]]; then
  rm -rf "$MEDVOX_TLS" "$MEDVOX_CADDY"
  rm -f "$MEDVOX_LOGS/caddy.log" "$MEDVOX_LOGS/caddy-access.log"*
  ok "Zertifikate und Caddy-Daten gelöscht. CA aus dem Schlüsselbund: mkcert -uninstall"
else
  ok "Zertifikate bleiben in $MEDVOX_TLS. Zum Löschen: uninstall.sh --purge"
fi
