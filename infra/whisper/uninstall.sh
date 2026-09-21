#!/bin/bash
# Entfernt den whisper-server-Dienst. Standardmäßig bleiben Modell und Build
# liegen; mit --purge wird auch ~/Library/Application Support/MedVox/whisper.cpp
# und das Modell gelöscht. OpenSuperWhisper wird nie angefasst.

source "$(dirname "$0")/../common.sh"
PLIST="$LAUNCH_AGENTS/$WHISPER_LABEL.plist"

log "Dienst $WHISPER_LABEL stoppen und entladen"
launchd_unload "$WHISPER_LABEL"
if [[ -f "$PLIST" ]]; then rm -f "$PLIST"; ok "$PLIST entfernt"; else ok "kein Agent installiert"; fi

if [[ "${1:-}" == "--purge" ]]; then
  log "Lösche Build und Modell"
  rm -rf "$WHISPER_SRC" "$WHISPER_MODEL" "$WHISPER_MODEL.part"
  rm -f "$MEDVOX_LOGS/whisper-server.log" "$MEDVOX_LOGS/whisper-build.log"
  ok "gelöscht: $WHISPER_SRC, $WHISPER_MODEL"
else
  ok "Build und Modell bleiben erhalten ($MEDVOX_HOME). Zum Löschen: uninstall.sh --purge"
fi
