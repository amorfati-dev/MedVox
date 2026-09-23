#!/bin/bash
# Baut die PWA (app/) und kopiert das Ergebnis nach
# ~/Library/Application Support/MedVox/app – dort liefert Caddy sie aus.
# Idempotent; das Repo darf danach verschoben oder gelöscht werden.
#
#   infra/app/install.sh

source "$(dirname "$0")/../common.sh"
APP_SRC="$REPO_DIR/app"

command -v npm >/dev/null 2>&1 || die "Node.js fehlt: brew install node"
mkdir -p "$MEDVOX_LOGS"

log "Baue die App (npm ci && npm run build)"
( cd "$APP_SRC" && npm ci --no-audit --no-fund --loglevel=error && npm run build --silent ) \
  >"$MEDVOX_LOGS/app-build.log" 2>&1 \
  || { tail -n 20 "$MEDVOX_LOGS/app-build.log" >&2; die "App-Build fehlgeschlagen, siehe $MEDVOX_LOGS/app-build.log"; }
[[ -f "$APP_SRC/dist/index.html" ]] || die "Build hat keine dist/index.html erzeugt"

log "Kopiere App nach $MEDVOX_APP"
mkdir -p "$MEDVOX_APP"
rsync -a --delete "$APP_SRC/dist/" "$MEDVOX_APP/"
ok "App installiert ($(find "$MEDVOX_APP" -type f | wc -l | tr -d ' ') Dateien)"
