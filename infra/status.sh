#!/bin/bash
# Gesamtzustand von MedVox auf dem Praxis-Mac – eine Zeile je Baustein, auf
# Deutsch, für den Praxisalltag lesbar:
#
#   make status
#
# Exit-Code 0 nur, wenn alles wirklich funktioniert: Spracherkennung, Backend
# (inkl. Passwort), HTTPS-Zugang mit App und API, Zertifikat und keine
# liegengebliebene Audiodatei. „Hinweis"-Zeilen zählen nicht als Fehler.
# Details je Dienst: infra/whisper/status.sh, infra/tls/check.sh.

source "$(dirname "$0")/common.sh"
ROOT="$MEDVOX_TLS/rootCA.pem"
CERT="$MEDVOX_TLS/cert.pem"
problems=0

good()  { printf '\033[1;32m ✓\033[0m %-24s %s\n' "$1" "$2"; }
bad()   { printf '\033[1;31m ✗\033[0m %-24s %s\n' "$1" "$2"; problems=$((problems + 1)); }
hint()  { printf '\033[1;33m !\033[0m %-24s %s\n' "$1" "$2"; }

for f in "$WHISPER_LOG" "$CADDY_LOG" "$SERVER_LOG"; do rotate_log "$f"; done
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
LAN_IP="${MEDVOX_LAN_IP:-$(lan_ip || true)}"

echo "MedVox – Zustand am $(date '+%d.%m.%Y um %H:%M')"
echo

# 1. Spracherkennung: Dienst läuft und transkribiert eine stumme Sekunde.
if ! launchd_running "$WHISPER_LABEL"; then
  bad "Spracherkennung" "Dienst läuft nicht → make install"
else
  write_silent_wav "$tmp/stille.wav"
  start=$(now_s)
  if resp="$(whisper_inference "$tmp/stille.wav" 2>/dev/null)" && [[ "$resp" == *'"text"'* ]]; then
    good "Spracherkennung" "läuft, antwortet in $(python3 -c "print(f'{$(now_s) - $start:.1f}'.replace('.', ','))") s"
  else
    bad "Spracherkennung" "Dienst läuft, antwortet aber nicht (startet evtl. gerade – in 30 s erneut prüfen)"
  fi
fi

# 2. Backend: Dienst läuft, /api/v1/health antwortet und sieht die Spracherkennung.
if ! launchd_running "$SERVER_LABEL"; then
  bad "Backend" "Dienst läuft nicht → make install"
elif ! health="$(curl -fsS --max-time 5 "http://$API_UPSTREAM/api/v1/health" 2>/dev/null)"; then
  bad "Backend" "Dienst läuft, antwortet aber nicht – Log: $SERVER_LOG"
elif [[ "$health" != *'"whisper":"ok"'* ]]; then
  bad "Backend" "antwortet, erreicht aber die Spracherkennung nicht"
else
  good "Backend" "läuft auf $API_UPSTREAM"
fi

# 3. Passwort für die Anmeldung auf dem iPad.
if [[ -s "$PASSWORD_FILE" ]]; then
  good "Passwort" "gesetzt (ändern: make set-password)"
else
  bad "Passwort" "nicht gesetzt – Anmeldung unmöglich → make set-password"
fi

# 4. HTTPS-Zugang: Caddy läuft und liefert App und API über die LAN-IP.
if ! launchd_running "$CADDY_LABEL"; then
  bad "HTTPS-Zugang (Caddy)" "Dienst läuft nicht → make install"
elif [[ -z "$LAN_IP" ]]; then
  bad "HTTPS-Zugang (Caddy)" "keine LAN-IP – ist der Mac im Praxis-Netz?"
elif [[ ! -f "$ROOT" ]]; then
  bad "HTTPS-Zugang (Caddy)" "Praxis-CA fehlt → make install"
else
  url="https://$LAN_IP"
  app_code="$(curl -sS --max-time 5 --cacert "$ROOT" -o "$tmp/index.html" -w '%{http_code}' "$url/" 2>/dev/null || true)"
  api_code="$(curl -sS --max-time 5 --cacert "$ROOT" -o /dev/null -w '%{http_code}' "$url/api/v1/health" 2>/dev/null || true)"
  if [[ "$app_code" != 200 ]] || ! grep -q 'id="root"' "$tmp/index.html" 2>/dev/null; then
    bad "HTTPS-Zugang (Caddy)" "$url liefert die App nicht (HTTP ${app_code:-–}) → make install"
  elif [[ "$api_code" != 200 ]]; then
    bad "HTTPS-Zugang (Caddy)" "App da, aber $url/api antwortet mit HTTP ${api_code:-–} (Backend?)"
  else
    good "HTTPS-Zugang (Caddy)" "$url – App und API erreichbar"
  fi
fi

# 5. Zertifikat: passt zur aktuellen LAN-IP und ist noch lange genug gültig.
if [[ ! -f "$CERT" ]]; then
  bad "Zertifikat" "fehlt → make install"
else
  sans="$(cert_san_list "$CERT")"
  until="$(openssl x509 -in "$CERT" -noout -enddate | cut -d= -f2)"
  if ! openssl x509 -in "$CERT" -noout -checkend 0 >/dev/null 2>&1; then
    bad "Zertifikat" "abgelaufen ($until) → make install"
  elif [[ -n "$LAN_IP" && "$sans" != *"IPAddress:$LAN_IP,"* ]]; then
    bad "Zertifikat" "passt nicht zur LAN-IP $LAN_IP (IP geändert?) → make install"
  elif ! openssl x509 -in "$CERT" -noout -checkend $((30 * 24 * 3600)) >/dev/null 2>&1; then
    hint "Zertifikat" "läuft bald ab ($until) → make install stellt ein neues aus"
  else
    good "Zertifikat" "gültig bis $until, für ${LAN_IP:-?} und medvox.local"
  fi
fi

# 6. Datensparsamkeit: keine Audiodatei älter als 2 Minuten im Zwischenordner.
leftover="$( { find "$MEDVOX_TMP" -type f -mmin +2 2>/dev/null || true; } | wc -l | tr -d ' ')"
if [[ "$leftover" == 0 ]]; then
  good "Audiodateien" "keine gespeichert ($MEDVOX_TMP ist leer)"
else
  bad "Audiodateien" "$leftover Datei(en) liegengeblieben in $MEDVOX_TMP – bitte melden"
fi

# Hinweis (kein Fehler): Mac darf am Netzteil nicht einschlafen.
sleep_ac="$(pmset -g custom 2>/dev/null | awk '/^AC Power/{ac=1} ac && $1=="sleep"{print $2; exit}')"
if [[ -n "$sleep_ac" && "$sleep_ac" != 0 ]]; then
  hint "Ruhezustand" "Mac schläft am Netzteil nach $sleep_ac min – abschalten, siehe infra/README.md Abschnitt 5"
fi

echo
if (( problems == 0 )); then
  printf '\033[1;32mAlles in Ordnung.\033[0m MedVox ist bereit.\n'
else
  printf '\033[1;31m%d Problem(e).\033[0m Zuerst „make install" erneut ausführen; hilft das nicht, Details:\n' "$problems"
  echo "  infra/whisper/status.sh   infra/tls/check.sh   tail -n 30 \"$SERVER_LOG\""
fi
exit $(( problems > 0 ))
