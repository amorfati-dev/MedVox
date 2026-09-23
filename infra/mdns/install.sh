#!/bin/bash
# Richtet den Namensdienst de.medvox.mdns ein: der Mac antwortet im LAN per
# Bonjour/mDNS auf medvox.local – immer mit seiner aktuellen Adresse, auch nach
# einem Netzwechsel (siehe run.sh). Idempotent: kopiert run.sh und common.sh
# nach ~/Library/Application Support/MedVox/mdns und lädt den Dienst neu.
#
#   infra/mdns/install.sh

source "$(dirname "$0")/../common.sh"

TEMPLATE="$INFRA_DIR/mdns/$MDNS_LABEL.plist.template"
PLIST="$LAUNCH_AGENTS/$MDNS_LABEL.plist"

command -v dns-sd >/dev/null 2>&1 || die "dns-sd fehlt (gehört zu macOS)"
mkdir -p "$MEDVOX_MDNS" "$MEDVOX_LOGS" "$LAUNCH_AGENTS"

log "Kopiere Namensdienst nach $MEDVOX_MDNS"
cp "$INFRA_DIR/mdns/run.sh" "$INFRA_DIR/common.sh" "$MEDVOX_MDNS/"
chmod +x "$MEDVOX_MDNS/run.sh"

log "Schreibe $PLIST"
x() { printf '%s' "$1" | xml_escape; }
render_template "$TEMPLATE" "$PLIST" \
  "LABEL=$MDNS_LABEL" \
  "RUN=$(x "$MEDVOX_MDNS/run.sh")" \
  "HOME=$(x "$HOME")" \
  "LOG=$(x "$MDNS_LOG")"
plutil -lint "$PLIST" >/dev/null || die "plist ist ungültig"

log "Namensdienst (neu) laden"
launchd_unload "$MDNS_LABEL"
rotate_log "$MDNS_LOG"
launchd_load "$PLIST"
ip="$(lan_ip || true)"
if [[ -z "$ip" ]]; then
  warn "Keine LAN-IP – $MDNS_NAME wird angemeldet, sobald der Mac im Netz ist"
elif wait_for_mdns "$ip" 15; then
  ok "$MDNS_NAME → $ip (Bonjour)"
else
  die "$MDNS_NAME löst nicht auf $ip auf – Log: $MDNS_LOG"
fi
