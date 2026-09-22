#!/bin/bash
# Entfernt den whisper-server-Dienst. Modell und Build bleiben liegen.
# OpenSuperWhisper wird nie angefasst.

source "$(dirname "$0")/../common.sh"
PLIST="$LAUNCH_AGENTS/$WHISPER_LABEL.plist"

log "Dienst $WHISPER_LABEL stoppen und entladen"
launchd_unload "$WHISPER_LABEL"
if [[ -f "$PLIST" ]]; then rm -f "$PLIST"; ok "$PLIST entfernt"; else ok "kein Agent installiert"; fi

ok "Build und Modell bleiben erhalten ($MEDVOX_HOME)"
