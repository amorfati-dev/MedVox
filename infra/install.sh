#!/bin/bash
# MedVox auf dem Praxis-Mac installieren – ein Befehl für alles (WP-12):
#
#   make install                         # im Repo-Verzeichnis
#   make install MODEL=/pfad/ggml-large-v3-turbo.bin   # vorhandenes Modell kopieren
#
# Idempotent: prüft die Voraussetzungen, richtet Spracherkennung (whisper-server),
# Backend (de.medvox.server), App und HTTPS (Caddy) ein und prüft am Ende alles.
# Erneut ausführen nach jedem Update des Repos – es wird nur nachgezogen, was fehlt.
# Rückfragen: das Mac-Passwort (sudo), wenn mkcert die Praxis-CA erstmals in den
# System-Schlüsselbund einträgt – deshalb nicht unbeaufsichtigt starten; bricht der Lauf
# dort ab, ein zweites `make install` schließt ab – und das MedVox-Passwort, falls noch
# keines gesetzt ist.

source "$(dirname "$0")/common.sh"
MODEL="${1:-${MODEL:-}}"

# --- 1. Voraussetzungen: alles Fehlende auf einmal nennen -------------------
log "Voraussetzungen prüfen"
missing=()
formulas=()
[[ "$(uname -s)" == "Darwin" ]] || die "MedVox wird auf einem Mac (Apple Silicon) installiert."
if xcode-select -p >/dev/null 2>&1; then ok "Xcode Command Line Tools"; else
  missing+=("Xcode Command Line Tools – im Terminal: xcode-select --install")
fi
if command -v brew >/dev/null 2>&1; then ok "Homebrew"; else
  missing+=("Homebrew – Befehl von https://brew.sh ausführen")
fi
for tool in ffmpeg uv node; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool"; else
    formulas+=("$tool"); missing+=("$tool – brew install $tool")
  fi
done
if command -v node >/dev/null 2>&1; then
  node_v="$(node -p 'process.versions.node')"
  IFS=. read -r major minor _ <<<"$node_v"
  if (( major < 22 || (major == 22 && minor < 18) )); then
    missing+=("Node.js ≥ 22.18 (installiert: $node_v) – brew upgrade node")
  fi
fi
if (( ${#missing[@]} )); then
  warn "Es fehlt:"
  for m in "${missing[@]}"; do printf '     • %s\n' "$m" >&2; done
  (( ${#formulas[@]} )) && printf '   Alles aus Homebrew auf einmal: brew install %s\n' "${formulas[*]}" >&2
  die "Bitte nachinstallieren und 'make install' erneut ausführen."
fi

# --- 2. Dienste ---------------------------------------------------------------
log "1/4 Spracherkennung (whisper-server)"
"$INFRA_DIR/whisper/install.sh" ${MODEL:+"$MODEL"}

log "2/4 Backend (de.medvox.server)"
"$INFRA_DIR/server/install.sh"

log "3/4 App (PWA)"
"$INFRA_DIR/app/install.sh"

log "4/4 HTTPS im Praxis-LAN (Caddy, Zertifikat) – beim ersten Mal fragt mkcert nach dem Mac-Passwort"
"$INFRA_DIR/tls/setup.sh"

# --- 3. Passwort ------------------------------------------------------------
if [[ ! -s "$PASSWORD_FILE" ]]; then
  if [[ -t 0 ]]; then
    log "Noch kein MedVox-Passwort gesetzt – jetzt festlegen (mind. 8 Zeichen)"
    "$INFRA_DIR/server/set-password.sh"
  else
    warn "Noch kein MedVox-Passwort gesetzt: make set-password"
  fi
fi

# --- 4. Gesamtprüfung und Adresse -------------------------------------------
echo
status=0
"$INFRA_DIR/status.sh" || status=$?
LAN_IP="${MEDVOX_LAN_IP:-$(lan_ip || echo '<LAN-IP>')}"
cat <<TXT

════════════════════════════════════════════════════════════════════════
 MedVox ist installiert.

 iPad / iPhone (Safari, dann „Zum Home-Bildschirm"):  https://$LAN_IP
 Rezeptions-PC (Edge/Chrome):                        https://$LAN_IP/transfer
 (statt der IP geht auch https://medvox.local, siehe infra/README.md)

 Zustand prüfen:   make status
 Abnahme:          docs/abnahme.md      Diktierhilfe: docs/diktierhilfe.md
════════════════════════════════════════════════════════════════════════
TXT
exit $status
