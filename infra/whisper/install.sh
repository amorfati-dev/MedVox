#!/bin/bash
# Richtet whisper-server als Praxisdienst ein (WP-1). Idempotent: kann beliebig
# oft laufen, baut nur nach, was fehlt, und lädt den Dienst neu.
#
#   infra/whisper/install.sh                      # Modell wird heruntergeladen (1,6 GB)
#   infra/whisper/install.sh /pfad/zu/ggml-large-v3-turbo.bin
#                                                 # vorhandene Modelldatei wird KOPIERT
#                                                 # (die Quelle bleibt unverändert)
#
# Ergebnis: launchd-Agent de.medvox.whisper-server, lauscht auf 127.0.0.1:8178,
# Prompt aus infra/whisper/prompt.txt. Prompt ändern → prompt.txt bearbeiten,
# install.sh erneut ausführen.

source "$(dirname "$0")/../common.sh"

WHISPER_REPO="https://github.com/ggml-org/whisper.cpp"
# Fester Stand, mit dem die Messungen im Plan gemacht wurden (2026-09-18).
WHISPER_REF="5670d5c0bbcb148feabef84400a07cfca9aa3b30"
MODEL_SRC="${1:-}"
PROMPT_FILE="$INFRA_DIR/whisper/prompt.txt"
TEMPLATE="$INFRA_DIR/whisper/$WHISPER_LABEL.plist.template"
PLIST="$LAUNCH_AGENTS/$WHISPER_LABEL.plist"
LOG="$WHISPER_LOG"

[[ "$(uname -s)" == "Darwin" ]] || die "Dieses Skript ist für macOS (Apple Silicon) gedacht."
[[ -f "$PROMPT_FILE" ]] || die "Prompt-Datei fehlt: $PROMPT_FILE"

# --- 1. Werkzeuge -----------------------------------------------------------
log "Voraussetzungen prüfen"
xcode-select -p >/dev/null 2>&1 || die "Xcode Command Line Tools fehlen: xcode-select --install"
need_brew
brew_ensure cmake
command -v git >/dev/null || die "git fehlt (kommt mit den Xcode Command Line Tools)"
mkdir -p "$MEDVOX_HOME" "$MEDVOX_MODELS" "$MEDVOX_LOGS" "$LAUNCH_AGENTS"

# --- 2. whisper.cpp holen und bauen (Metal) ---------------------------------
if [[ -d "$WHISPER_SRC/.git" ]]; then
  ok "whisper.cpp vorhanden: $WHISPER_SRC"
else
  log "Klone whisper.cpp nach $WHISPER_SRC"
  git clone --quiet "$WHISPER_REPO" "$WHISPER_SRC"
fi
if [[ "$(git -C "$WHISPER_SRC" rev-parse HEAD)" != "$WHISPER_REF" ]]; then
  log "Stelle whisper.cpp auf Stand $WHISPER_REF"
  git -C "$WHISPER_SRC" fetch --quiet origin "$WHISPER_REF" || git -C "$WHISPER_SRC" fetch --quiet origin
  git -C "$WHISPER_SRC" checkout --quiet "$WHISPER_REF"
  rm -rf "$WHISPER_SRC/build"
fi

if [[ -x "$WHISPER_BIN" ]]; then
  ok "whisper-server ist gebaut"
else
  log "Baue whisper-server mit Metal (dauert einige Minuten)"
  cmake -S "$WHISPER_SRC" -B "$WHISPER_SRC/build" -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release \
    -DWHISPER_BUILD_TESTS=OFF >"$MEDVOX_LOGS/whisper-build.log" 2>&1 \
    || die "cmake fehlgeschlagen, siehe $MEDVOX_LOGS/whisper-build.log"
  cmake --build "$WHISPER_SRC/build" -j "$(sysctl -n hw.ncpu)" --target whisper-server \
    >>"$MEDVOX_LOGS/whisper-build.log" 2>&1 \
    || die "Build fehlgeschlagen, siehe $MEDVOX_LOGS/whisper-build.log"
  [[ -x "$WHISPER_BIN" ]] || die "whisper-server wurde nicht erzeugt"
  ok "whisper-server gebaut: $WHISPER_BIN"
fi

# --- 3. Modell --------------------------------------------------------------
if [[ -n "$MODEL_SRC" ]]; then
  [[ -f "$MODEL_SRC" ]] || die "Modelldatei nicht gefunden: $MODEL_SRC"
  if [[ -f "$WHISPER_MODEL" ]] && cmp -s "$MODEL_SRC" "$WHISPER_MODEL"; then
    ok "Modell bereits vorhanden (identisch mit $MODEL_SRC)"
  else
    log "Kopiere Modell nach $WHISPER_MODEL (Quelle bleibt unverändert)"
    cp "$MODEL_SRC" "$WHISPER_MODEL.part" && mv "$WHISPER_MODEL.part" "$WHISPER_MODEL"
  fi
elif [[ -f "$WHISPER_MODEL" ]]; then
  ok "Modell vorhanden: $WHISPER_MODEL"
else
  log "Kein Modell vorhanden – lade ggml-large-v3-turbo.bin (1,6 GB) von Hugging Face – einmalig, danach kein Internet nötig"
  log "Vorhandene Datei stattdessen nutzen: make install MODEL=/pfad/zum/ggml-large-v3-turbo.bin"
  sh "$WHISPER_SRC/models/download-ggml-model.sh" large-v3-turbo "$MEDVOX_MODELS"
  [[ -f "$WHISPER_MODEL" ]] || die "Download fehlgeschlagen"
fi
size="$(stat -f %z "$WHISPER_MODEL")"
(( size > 1000000000 )) || die "Modelldatei ist unerwartet klein ($size Byte) – kaputter Download?"

# --- 4. launchd-Agent -------------------------------------------------------
log "Schreibe $PLIST"
prompt="$(tr -d '\n' < "$PROMPT_FILE" | xml_escape)"
[[ -n "$prompt" ]] || die "prompt.txt ist leer"
render_template "$TEMPLATE" "$PLIST" \
  "LABEL=$WHISPER_LABEL" \
  "WHISPER_BIN=$(printf '%s' "$WHISPER_BIN" | xml_escape)" \
  "MODEL=$(printf '%s' "$WHISPER_MODEL" | xml_escape)" \
  "PROMPT=$prompt" \
  "HOST=$WHISPER_HOST" \
  "PORT=$WHISPER_PORT" \
  "WORKDIR=$(printf '%s' "$WHISPER_SRC" | xml_escape)" \
  "LOG=$(printf '%s' "$LOG" | xml_escape)"
plutil -lint "$PLIST" >/dev/null || die "plist ist ungültig"

log "Dienst (neu) laden"
launchd_unload "$WHISPER_LABEL"
rotate_log "$LOG"
launchd_load "$PLIST"
if wait_for_port "$WHISPER_PORT" 60; then
  ok "whisper-server läuft auf http://$WHISPER_HOST:$WHISPER_PORT"
else
  die "whisper-server antwortet nicht auf Port $WHISPER_PORT – Log: $LOG"
fi

echo
echo "Fertig. Prüfen mit:  infra/whisper/status.sh"
echo "Prompt ändern:       infra/whisper/prompt.txt bearbeiten, dann install.sh erneut ausführen."
