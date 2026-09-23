#!/bin/bash
# Richtet das Backend (FastAPI, server/) als launchd-Agent de.medvox.server auf
# 127.0.0.1:8000 ein. Idempotent: kopiert den aktuellen Stand aus dem Repo nach
# ~/Library/Application Support/MedVox/server, installiert die Python-Pakete
# (uv, ohne Entwicklungswerkzeuge) und lädt den Dienst neu.
#
#   infra/server/install.sh
#
# Das Passwort setzt `make set-password` (infra/server/set-password.sh).

source "$(dirname "$0")/../common.sh"

TEMPLATE="$INFRA_DIR/server/$SERVER_LABEL.plist.template"
PLIST="$LAUNCH_AGENTS/$SERVER_LABEL.plist"

log "Backend-Voraussetzungen prüfen"
command -v uv >/dev/null 2>&1 || die "uv fehlt: brew install uv"
FFMPEG="$(command -v ffmpeg || true)"
[[ -n "$FFMPEG" ]] || die "ffmpeg fehlt: brew install ffmpeg"
mkdir -p "$MEDVOX_SERVER" "$MEDVOX_TMP" "$MEDVOX_LOGS" "$LAUNCH_AGENTS"
chmod 700 "$MEDVOX_TMP"

log "Kopiere Backend nach $MEDVOX_SERVER"
rsync -a --delete --exclude '__pycache__' "$REPO_DIR/server/medvox/" "$MEDVOX_SERVER/medvox/"
cp "$REPO_DIR/server/pyproject.toml" "$REPO_DIR/server/uv.lock" "$MEDVOX_SERVER/"
cp "$INFRA_DIR/whisper/prompt.txt" "$MEDVOX_SERVER/prompt.txt"
cp "$INFRA_DIR/server/run.sh" "$MEDVOX_SERVER/run.sh"
chmod +x "$MEDVOX_SERVER/run.sh"

log "Python-Pakete installieren (uv sync, nur Laufzeit)"
# --no-install-project: der Code liegt direkt daneben (uvicorn --app-dir), kein Paketbau nötig.
uv sync --quiet --frozen --no-dev --no-install-project --project "$MEDVOX_SERVER" \
  || die "uv sync fehlgeschlagen (Internet nötig beim ersten Mal)"
[[ -x "$MEDVOX_SERVER/.venv/bin/uvicorn" ]] || die "uvicorn fehlt in $MEDVOX_SERVER/.venv"
ok "Backend-Umgebung bereit"

[[ -s "$PASSWORD_FILE" ]] || warn "Noch kein Passwort gesetzt – danach: make set-password"

log "Schreibe $PLIST"
x() { printf '%s' "$1" | xml_escape; }
render_template "$TEMPLATE" "$PLIST" \
  "LABEL=$SERVER_LABEL" \
  "RUN=$(x "$MEDVOX_SERVER/run.sh")" \
  "HOST=$SERVER_HOST" \
  "PORT=$SERVER_PORT" \
  "WORKDIR=$(x "$MEDVOX_SERVER")" \
  "HOME=$(x "$HOME")" \
  "DB_PATH=$(x "$MEDVOX_HOME/medvox.db")" \
  "FFMPEG=$(x "$FFMPEG")" \
  "WHISPER_URL=http://$WHISPER_HOST:$WHISPER_PORT" \
  "PROMPT_FILE=$(x "$MEDVOX_SERVER/prompt.txt")" \
  "TMP_DIR=$(x "$MEDVOX_TMP")" \
  "LOG=$(x "$SERVER_LOG")"
plutil -lint "$PLIST" >/dev/null || die "plist ist ungültig"

log "Backend (neu) laden"
launchd_unload "$SERVER_LABEL"
rotate_log "$SERVER_LOG"
launchd_load "$PLIST"
if wait_for_port "$SERVER_PORT" 30 \
  && curl -fsS --max-time 5 "http://$API_UPSTREAM/api/v1/health" >/dev/null; then
  ok "Backend läuft auf http://$API_UPSTREAM"
else
  die "Backend antwortet nicht auf Port $SERVER_PORT – Log: $SERVER_LOG"
fi
