#!/bin/bash
# Startskript des Namensdienstes für launchd (de.medvox.mdns). Wird von
# infra/mdns/install.sh nach ~/Library/Application Support/MedVox/mdns/
# kopiert und von dort gestartet – nie aus dem Repo.
#
# Meldet per Bonjour/mDNS den Namen medvox.local mit der AKTUELLEN LAN-IP an
# (`dns-sd -P`, dazu den Dienst „MedVox" als _https._tcp auf Port 443). dns-sd
# hält die Adresse fest, die es beim Start bekommt – deshalb prüft dieses
# Skript alle $INTERVAL Sekunden die LAN-IP (gleiche Regel wie `lan_ip` in
# common.sh) und meldet bei einer Änderung neu an. Ohne Netz wird nichts
# angemeldet; stirbt dns-sd, startet es beim nächsten Durchlauf neu.
# Der Mac behält seinen eigenen Namen; medvox.local ist ein zusätzlicher Name.

source "$(dirname "$0")/common.sh"
set +e  # Dauerschleife: ein fehlgeschlagener Befehl darf den Dienst nicht beenden
INTERVAL="${MEDVOX_MDNS_INTERVAL:-5}"
current="" pid=""

stop_dns_sd() {
  if [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
  fi
  pid=""
}
trap 'stop_dns_sd; exit 0' TERM INT HUP

while true; do
  ip="$(lan_ip || true)"
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
    echo "$(date '+%F %T') dns-sd beendet – melde neu an"
    pid=""
  fi
  if [[ "$ip" != "$current" || ( -n "$ip" && -z "$pid" ) ]]; then
    stop_dns_sd
    if [[ -n "$ip" ]]; then
      prev=""; [[ -n "$current" && "$current" != "$ip" ]] && prev=" (vorher $current)"
      echo "$(date '+%F %T') melde $MDNS_NAME → $ip an$prev"
      dns-sd -P MedVox _https._tcp local "$CADDY_HTTPS_PORT" "$MDNS_NAME" "$ip" &
      pid=$!
    else
      echo "$(date '+%F %T') keine LAN-IP – $MDNS_NAME abgemeldet, warte auf Netz"
    fi
    current="$ip"
  fi
  sleep "$INTERVAL" & wait $!
done
