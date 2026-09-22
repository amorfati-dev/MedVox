#!/bin/bash
# Gemeinsame Pfade und Helfer für alle infra/-Skripte. Wird per `source` geladen.
# Alles liegt unter ~/Library/Application Support/MedVox – nichts im Repo,
# nichts in den Verzeichnissen anderer Programme (OpenSuperWhisper bleibt unberührt).

set -euo pipefail
# bash ≥ 5.2 würde '&' im Ersetzungstext von ${var//a/b} sonst als Treffer deuten.
shopt -u patsub_replacement 2>/dev/null || true

MEDVOX_HOME="$HOME/Library/Application Support/MedVox"
MEDVOX_MODELS="$MEDVOX_HOME/models"
MEDVOX_TLS="$MEDVOX_HOME/tls"
MEDVOX_CADDY="$MEDVOX_HOME/caddy"
MEDVOX_LOGS="$HOME/Library/Logs/MedVox"
WHISPER_LOG="$MEDVOX_LOGS/whisper-server.log"
CADDY_LOG="$MEDVOX_LOGS/caddy.log"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

WHISPER_SRC="$MEDVOX_HOME/whisper.cpp"
WHISPER_BIN="$WHISPER_SRC/build/bin/whisper-server"
WHISPER_MODEL="$MEDVOX_MODELS/ggml-large-v3-turbo.bin"
WHISPER_HOST="127.0.0.1"
WHISPER_PORT="8178"
WHISPER_LABEL="de.medvox.whisper-server"

CADDY_LABEL="de.medvox.caddy"
CADDY_HTTPS_PORT="443"
API_UPSTREAM="127.0.0.1:8000"

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$INFRA_DIR/.." && pwd)"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m !\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m ✗\033[0m %s\n' "$*" >&2; exit 1; }

need_brew() {
  command -v brew >/dev/null 2>&1 || die "Homebrew fehlt. Installieren: https://brew.sh (siehe infra/README.md, Voraussetzungen)."
}

# brew_ensure <formel> – installiert eine Homebrew-Formel nur, wenn sie fehlt.
brew_ensure() {
  if brew list --formula "$1" >/dev/null 2>&1; then
    ok "$1 ist installiert"
  else
    log "Installiere $1 über Homebrew"
    brew install "$1"
  fi
}

# Aktuelle LAN-IPv4 des Macs. Zuerst die Schnittstelle der Standardroute – das
# ist die, über die iPad und Rezeptions-PC den Mac erreichen; erst danach en0…en5
# (z. B. wenn gerade keine Standardroute gesetzt ist).
lan_ip() {
  local ip="" iface
  iface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"
  if [[ -n "$iface" ]]; then
    ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
    [[ -n "$ip" ]] && { echo "$ip"; return 0; }
  fi
  for iface in en0 en1 en2 en3 en4 en5; do
    ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
    [[ -n "$ip" ]] && { echo "$ip"; return 0; }
  done
  return 1
}

# cert_sans <zertifikat> – gibt die SAN-Liste als "DNS:…, IP Address:…" aus.
# Bewusst über `-text`: das macOS-eigene /usr/bin/openssl (LibreSSL) kennt
# `-ext subjectAltName` nicht.
cert_sans() {
  openssl x509 -in "$1" -noout -text 2>/dev/null \
    | awk '/X509v3 Subject Alternative Name/{getline; gsub(/^ +| +$/, ""); print; exit}' || true
}

# cert_san_list <zertifikat> – SANs ohne Leerzeichen, mit abschließendem Komma,
# damit `*"IPAddress:$ip,"*` eine ganze IP trifft und nicht nur deren Anfang.
cert_san_list() {
  printf '%s,\n' "$(cert_sans "$1" | tr -d ' ')"
}

# xml_escape – für Werte, die in eine launchd-plist geschrieben werden.
xml_escape() {
  sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g'
}

# render_template <template> <ziel> VAR=WERT ... – ersetzt @@VAR@@ im Template.
render_template() {
  local tpl="$1" out="$2"; shift 2
  local content; content="$(cat "$tpl")"
  local kv key val
  for kv in "$@"; do
    key="${kv%%=*}"; val="${kv#*=}"
    content="${content//@@${key}@@/$val}"
  done
  if [[ "$content" == *@@*@@* ]]; then
    die "Template $tpl enthält nicht ersetzte Platzhalter"
  fi
  printf '%s\n' "$content" > "$out"
}

# launchd-Helfer: Agent (neu) laden bzw. entladen. gui/<uid> = Benutzer-Sitzung.
launchd_domain() { echo "gui/$(id -u)"; }

launchd_unload() {
  local label="$1"
  if launchctl print "$(launchd_domain)/$label" >/dev/null 2>&1; then
    launchctl bootout "$(launchd_domain)/$label" 2>/dev/null || true
    sleep 1
  fi
}

launchd_load() {
  local plist="$1"
  launchctl bootstrap "$(launchd_domain)" "$plist"
}

launchd_running() {
  local label="$1"
  launchctl print "$(launchd_domain)/$label" 2>/dev/null | grep -q 'state = running'
}

# Prüft, ob ein TCP-Port auf 127.0.0.1 antwortet.
port_open() {
  nc -z -w 1 127.0.0.1 "$1" >/dev/null 2>&1
}

# Wartet bis zu $2 Sekunden, bis Port $1 offen ist.
wait_for_port() {
  local port="$1" secs="${2:-30}" i
  for ((i = 0; i < secs; i++)); do
    port_open "$port" && return 0
    sleep 1
  done
  return 1
}

# rotate_log <datei> – begrenzt ein Dienst-Log auf 5 MiB: darüber wird der
# Inhalt nach .1 (.2, .3) gesichert und die Datei geleert. Geleert statt
# umbenannt, damit der laufende launchd-Dienst weiter in dieselbe Datei schreibt.
rotate_log() {
  local f="$1" max=$((5 * 1024 * 1024))
  [[ -f "$f" ]] || return 0
  (( $(stat -f %z "$f") > max )) || return 0
  rm -f "$f.3"
  if [[ -f "$f.2" ]]; then mv "$f.2" "$f.3"; fi
  if [[ -f "$f.1" ]]; then mv "$f.1" "$f.2"; fi
  cp "$f" "$f.1"
  : > "$f"
}

# Schreibt eine 1-Sekunde lange, stumme 16-kHz-Mono-WAV-Datei nach $1.
# (44-Byte-RIFF-Header + 32000 Nullbytes = 16000 Samples × 2 Byte.)
write_silent_wav() {
  local out="$1"
  {
    printf 'RIFF'
    printf '\x24\x7d\x00\x00'   # Dateigröße-8 = 32036
    printf 'WAVEfmt '
    printf '\x10\x00\x00\x00'   # fmt-Chunk-Größe 16
    printf '\x01\x00'           # PCM
    printf '\x01\x00'           # 1 Kanal
    printf '\x80\x3e\x00\x00'   # 16000 Hz
    printf '\x00\x7d\x00\x00'   # Byte-Rate 32000
    printf '\x02\x00'           # Block-Align 2
    printf '\x10\x00'           # 16 Bit
    printf 'data'
    printf '\x00\x7d\x00\x00'   # Daten-Größe 32000
    head -c 32000 /dev/zero
  } > "$out"
}

# POST einer WAV-Datei an whisper-server; gibt die JSON-Antwort aus.
# Ohne zweites Argument gilt der beim Dienststart gesetzte Prompt.
whisper_inference() {
  local wav="$1" prompt="${2:-}"
  local args=(-F "file=@$wav" -F "language=de" -F "response_format=json")
  [[ -n "$prompt" ]] && args+=(-F "prompt=$prompt")
  curl -sS --max-time 120 "${args[@]}" "http://$WHISPER_HOST:$WHISPER_PORT/inference"
}

now_s() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
