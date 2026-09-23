#!/bin/bash
# Neustart-Probe ohne Mac-Neustart: beendet jeden MedVox-Dienst hart
# (launchctl kickstart -k) und misst, bis er wieder antwortet. Danach
# `status.sh`. Den echten Neustart-Test macht der Behandler selbst
# (docs/abnahme.md, Punkt 6).
#
#   make restart-test

source "$(dirname "$0")/common.sh"
fails=0

# probe <label> <prüfbefehl…> – Dienst hart neu starten, bis zu 90 s auf Antwort warten.
probe() {
  local label="$1"; shift
  launchd_running "$label" || { warn "$label läuft nicht – erst make install"; fails=$((fails + 1)); return; }
  local old new start i
  old="$(launchctl print "$(launchd_domain)/$label" | awk '/^\tpid = /{print $3}')"
  start=$(now_s)
  launchctl kickstart -k "$(launchd_domain)/$label"
  for ((i = 0; i < 180; i++)); do
    new="$(launchctl print "$(launchd_domain)/$label" 2>/dev/null | awk '/^\tpid = /{print $3}')"
    if [[ -n "$new" && "$new" != "$old" ]] && "$@" >/dev/null 2>&1; then
      ok "$label: PID $old → $new, antwortet wieder nach $(python3 -c "print(f'{$(now_s) - $start:.1f}')") s"
      return
    fi
    sleep 0.5
  done
  warn "$label antwortet 90 s nach dem Neustart nicht"; fails=$((fails + 1))
}

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
write_silent_wav "$tmp/stille.wav"
LAN_IP="${MEDVOX_LAN_IP:-$(lan_ip || true)}"

log "Dienste hart neu starten (launchctl kickstart -k)"
probe "$WHISPER_LABEL" whisper_inference "$tmp/stille.wav"
probe "$SERVER_LABEL" curl -fsS --max-time 2 "http://$API_UPSTREAM/api/v1/health"
probe "$CADDY_LABEL" curl -fsS --max-time 2 --cacert "$MEDVOX_TLS/rootCA.pem" "https://$LAN_IP/api/v1/health"

echo
"$INFRA_DIR/status.sh" || fails=$((fails + 1))
exit $(( fails > 0 ))
