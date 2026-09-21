#!/bin/bash
# Rauchtest: erzeugt mit `say` ein deutsches Zahnarzt-Diktat, schickt es an den
# laufenden whisper-server und prüft, dass "36" (oder "drei sechs") im
# Transkript steht. Exit 0 = bestanden.

source "$(dirname "$0")/../common.sh"
SENTENCE="Zahn drei sechs mesial okklusal distal Karies profunda, Infiltrationsanästhesie mit Artikain, Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt."

port_open "$WHISPER_PORT" || die "whisper-server läuft nicht auf Port $WHISPER_PORT (infra/whisper/install.sh)"

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
log "Erzeuge Test-Audio mit macOS-Stimme Anna (16 kHz, mono)"
say -v Anna -r 175 --data-format=LEI16@16000 -o "$tmp/diktat.wav" "$SENTENCE" \
  || die "say fehlgeschlagen – ist die deutsche Stimme 'Anna' installiert? (Systemeinstellungen > Bedienungshilfen > Gesprochene Inhalte)"
ok "Audio: $(afinfo "$tmp/diktat.wav" 2>/dev/null | awk '/estimated duration/{print $3 " s"}')"

log "Sende an http://$WHISPER_HOST:$WHISPER_PORT/inference"
start=$(now_s)
resp="$(whisper_inference "$tmp/diktat.wav")" || die "Anfrage fehlgeschlagen"   # Prompt kommt aus dem Dienst
end=$(now_s)
text="$(printf '%s' "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("text","").strip())' 2>/dev/null || printf '%s' "$resp")"
printf '   Dauer:      %.2f s\n' "$(python3 -c "print($end - $start)")"
echo   "   Diktat:     $SENTENCE"
echo   "   Transkript: $text"

if [[ "$text" == *36* || "$text" == *"drei sechs"* || "$text" == *"Drei sechs"* ]]; then
  ok "Rauchtest bestanden: Zahn 36 erkannt"
else
  die "Rauchtest fehlgeschlagen: weder '36' noch 'drei sechs' im Transkript"
fi
