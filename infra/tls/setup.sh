#!/bin/bash
# LAN-HTTPS für MedVox (WP-3): eigene Praxis-CA mit mkcert, Zertifikat für
# medvox.local + aktuelle LAN-IP, Caddy als Reverse-Proxy auf Port 443 als
# launchd-Agent. Idempotent.
#
#   infra/tls/setup.sh   # fragt einmal nach dem Mac-Passwort: mkcert trägt die
#                        # CA in den macOS-Schlüsselbund ein
#
# Erneut ausführen, wenn sich die LAN-IP geändert hat – das Zertifikat wird
# automatisch neu ausgestellt. Umgebungsvariable: MEDVOX_LAN_IP (Standard:
# automatisch ermittelt).

source "$(dirname "$0")/../common.sh"

[[ $# -eq 0 ]] || die "Unbekannte Option: $1"

CERT="$MEDVOX_TLS/cert.pem"
KEY="$MEDVOX_TLS/key.pem"
ROOT="$MEDVOX_TLS/rootCA.pem"
CADDYFILE="$MEDVOX_CADDY/Caddyfile"
PLIST="$LAUNCH_AGENTS/$CADDY_LABEL.plist"
APP_DIST="$REPO_DIR/app/dist"

# --- 1. Werkzeuge -----------------------------------------------------------
log "Voraussetzungen prüfen"
need_brew
brew_ensure mkcert
brew_ensure caddy
mkdir -p "$MEDVOX_TLS" "$MEDVOX_CADDY" "$MEDVOX_LOGS" "$LAUNCH_AGENTS"
chmod 700 "$MEDVOX_TLS"
# Zugriffslogs sind abgeschaltet; eine ältere Fassung dieser Skripte hat noch
# welche geschrieben (Anfrage-URLs, Client-IPs) – diese Altlast kommt weg.
rm -f "$MEDVOX_LOGS"/caddy-access*.log

LAN_IP="${MEDVOX_LAN_IP:-$(lan_ip || true)}"
[[ -n "$LAN_IP" ]] || die "Keine LAN-IP gefunden. Ist der Mac im Praxis-WLAN/LAN? (Alternativ: MEDVOX_LAN_IP=… setzen)"
ok "LAN-IP des Macs: $LAN_IP"

# --- 2. Praxis-CA -----------------------------------------------------------
CAROOT="$(mkcert -CAROOT)"
if [[ -f "$CAROOT/rootCA.pem" ]]; then
  ok "Praxis-CA vorhanden: $CAROOT"
else
  log "Erzeuge Praxis-CA (mkcert)"
fi
log "CA im macOS-Schlüsselbund eintragen (mkcert -install, fragt ggf. nach Passwort)"
mkcert -install
cp "$CAROOT/rootCA.pem" "$ROOT" 2>/dev/null || true

# --- 3. Zertifikat ----------------------------------------------------------
needs_cert=0
[[ -f "$CERT" && -f "$KEY" ]] || needs_cert=1
if (( ! needs_cert )); then
  # Neu ausstellen, wenn die IP nicht mehr im Zertifikat steht oder es in < 30 Tagen abläuft.
  sans="$(cert_san_list "$CERT")"
  [[ "$sans" == *"IPAddress:$LAN_IP,"* ]] || needs_cert=1
  [[ "$sans" == *"DNS:medvox.local,"* ]] || needs_cert=1
  openssl x509 -in "$CERT" -noout -checkend $((30*24*3600)) >/dev/null 2>&1 || needs_cert=1
fi
if (( needs_cert )); then
  log "Stelle Zertifikat aus: medvox.local, $LAN_IP"
  ( cd "$MEDVOX_TLS" && mkcert -cert-file cert.pem -key-file key.pem medvox.local "$LAN_IP" )
  chmod 600 "$KEY"
  cp "$CAROOT/rootCA.pem" "$ROOT"
  ok "Zertifikat: $CERT (gültig bis $(openssl x509 -in "$CERT" -noout -enddate | cut -d= -f2))"
else
  ok "Zertifikat aktuell: $CERT"
fi
[[ -f "$ROOT" ]] || die "rootCA.pem fehlt in $CAROOT"

# --- 4. Caddy ---------------------------------------------------------------
log "Schreibe $CADDYFILE"
[[ -d "$APP_DIST" ]] || warn "App-Verzeichnis $APP_DIST existiert noch nicht (erst nach 'npm run build' in app/) – Caddy startet trotzdem"
render_template "$INFRA_DIR/tls/Caddyfile" "$CADDYFILE" \
  "LAN_IP=$LAN_IP" \
  "HTTPS_PORT=$CADDY_HTTPS_PORT" \
  "CERT=$CERT" \
  "KEY=$KEY" \
  "API_UPSTREAM=$API_UPSTREAM" \
  "APP_DIST=$APP_DIST"
caddy validate --config "$CADDYFILE" --adapter caddyfile >/dev/null 2>&1 \
  || { caddy validate --config "$CADDYFILE" --adapter caddyfile; die "Caddyfile ungültig"; }

log "Schreibe $PLIST"
render_template "$INFRA_DIR/tls/$CADDY_LABEL.plist.template" "$PLIST" \
  "LABEL=$CADDY_LABEL" \
  "CADDY_BIN=$(printf '%s' "$(command -v caddy)" | xml_escape)" \
  "CADDYFILE=$(printf '%s' "$CADDYFILE" | xml_escape)" \
  "HOME=$(printf '%s' "$HOME" | xml_escape)" \
  "DATA_DIR=$(printf '%s' "$MEDVOX_CADDY" | xml_escape)" \
  "LOG=$(printf '%s' "$CADDY_LOG" | xml_escape)"
plutil -lint "$PLIST" >/dev/null || die "plist ist ungültig"

log "Caddy (neu) laden"
launchd_unload "$CADDY_LABEL"
rotate_log "$CADDY_LOG"
launchd_load "$PLIST"
if wait_for_port "$CADDY_HTTPS_PORT" 20; then
  ok "Caddy lauscht auf https://$LAN_IP:$CADDY_HTTPS_PORT"
else
  die "Caddy antwortet nicht auf Port $CADDY_HTTPS_PORT – Log: $CADDY_LOG"
fi

# --- 5. Anleitung für die Geräte -------------------------------------------
URL="https://$LAN_IP"
cat <<TXT

════════════════════════════════════════════════════════════════════════
 Fertig. Adresse der App im Praxis-LAN:   $URL
                                          (oder https://medvox.local, siehe README)
 Praxis-CA zum Verteilen:                 $ROOT

 iPad / iPhone – Praxis-CA einmalig installieren:
   1. rootCA.pem aufs Gerät bringen: im Finder rechtsklick auf die Datei
      → „Teilen" → AirDrop an das iPad (oder als Mail-Anhang senden und
      den Anhang auf dem iPad antippen).
   2. Meldung „Profil geladen" → Einstellungen öffnen → oben „Profil geladen"
      (bzw. Einstellungen > Allgemein > VPN & Geräteverwaltung) → „mkcert …"
      → „Installieren" (Gerätecode eingeben) → „Installieren" bestätigen.
   3. WICHTIG, sonst bleibt Safari rot: Einstellungen > Allgemein > Info
      > Zertifikatsvertrauenseinstellungen → Schalter bei „mkcert …" auf EIN
      → „Weiter".
   4. Safari: $URL öffnen → Schloss ohne Warnung. Dann „Teilen"
      → „Zum Home-Bildschirm" für die PWA.

 Windows-Rezeptions-PC – Praxis-CA einmalig installieren:
   1. rootCA.pem auf den PC kopieren (USB-Stick, Mail, Netzfreigabe).
   2. Datei umbenennen in rootCA.crt, Doppelklick → „Zertifikat installieren…"
      → „Lokaler Computer" (Admin) oder „Aktueller Benutzer"
      → „Alle Zertifikate in folgendem Speicher speichern" → „Durchsuchen…"
      → „Vertrauenswürdige Stammzertifizierungsstellen" → Fertig stellen.
      (Alternativ als Admin in PowerShell:
       Import-Certificate -FilePath rootCA.crt -CertStoreLocation Cert:\\LocalMachine\\Root)
   3. Edge/Chrome neu starten, $URL öffnen. Firefox braucht zusätzlich
      about:config → security.enterprise_roots.enabled = true.

 Prüfen von diesem Mac aus:  infra/tls/check.sh
════════════════════════════════════════════════════════════════════════
TXT
