#!/bin/bash
# Zeigt, ob whisper-server läuft: launchd-Zustand, Health-Check mit einer
# stummen 1-s-WAV und die letzten Log-Zeilen. Exit-Code 0 = gesund.

source "$(dirname "$0")/../common.sh"
LOG="$MEDVOX_LOGS/whisper-server.log"
status=0

log "launchd: $WHISPER_LABEL"
if launchd_running "$WHISPER_LABEL"; then
  pid="$(launchctl print "$(launchd_domain)/$WHISPER_LABEL" | awk '/^\tpid = /{print $3}')"
  ok "läuft (PID ${pid:-?})"
else
  warn "nicht geladen oder nicht aktiv – infra/whisper/install.sh ausführen"
  status=1
fi

log "Modell"
if [[ -f "$WHISPER_MODEL" ]]; then
  ok "$WHISPER_MODEL ($(du -h "$WHISPER_MODEL" | cut -f1))"
else
  warn "fehlt: $WHISPER_MODEL"; status=1
fi

log "Health-Check: stumme 1-s-WAV an http://$WHISPER_HOST:$WHISPER_PORT/inference"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
write_silent_wav "$tmp/silence.wav"
if port_open "$WHISPER_PORT"; then
  start=$(now_s)
  if resp="$(whisper_inference "$tmp/silence.wav" 2>&1)" && [[ "$resp" == *'"text"'* ]]; then
    ok "antwortet in $(printf %.2f "$(python3 -c "print($(now_s) - $start)")") s: $resp"
  else
    warn "unerwartete Antwort: $resp"; status=1
  fi
else
  warn "Port $WHISPER_PORT ist geschlossen"; status=1
fi

log "Log (letzte 15 Zeilen): $LOG"
rotate_log "$LOG"
if [[ -f "$LOG" ]]; then tail -n 15 "$LOG"; else warn "noch kein Log"; fi

echo
if (( status == 0 )); then ok "whisper-server ist gesund"; else warn "whisper-server hat Probleme"; fi
exit $status
