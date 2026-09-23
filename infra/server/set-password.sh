#!/bin/bash
# Setzt das Behandler-Passwort: fragt es zweimal ab, speichert nur den
# PBKDF2-Hash in ~/Library/Application Support/MedVox/password-hash (nur für
# den eigenen Benutzer lesbar) und startet das Backend neu, damit er gilt.
#
#   make set-password
#
# Ohne Terminal (z. B. in Skripten) wird das Passwort als eine Zeile von
# stdin gelesen.

source "$(dirname "$0")/../common.sh"
command -v uv >/dev/null 2>&1 || die "uv fehlt: brew install uv"
mkdir -p "$MEDVOX_HOME"

hash="$(cd "$REPO_DIR/server" && uv run --quiet --no-dev python -c '
import getpass, sys
from medvox.auth import hash_password
if sys.stdin.isatty():
    first = getpass.getpass("Neues MedVox-Passwort: ")
    if first != getpass.getpass("Wiederholen: "):
        sys.exit("Die Eingaben stimmen nicht überein.")
else:
    first = sys.stdin.readline().rstrip("\n")
if len(first) < 8:
    sys.exit("Das Passwort muss mindestens 8 Zeichen haben.")
print(hash_password(first))
')" || die "Passwort nicht gesetzt"

( umask 077 && printf '%s\n' "$hash" > "$PASSWORD_FILE.tmp" )
mv "$PASSWORD_FILE.tmp" "$PASSWORD_FILE"
ok "Passwort-Hash gespeichert: $PASSWORD_FILE"

if launchctl print "$(launchd_domain)/$SERVER_LABEL" >/dev/null 2>&1; then
  launchctl kickstart -k "$(launchd_domain)/$SERVER_LABEL"
  wait_for_port "$SERVER_PORT" 30 && ok "Backend neu gestartet – das neue Passwort gilt ab sofort" \
    || warn "Backend startet nicht – Log: $SERVER_LOG"
else
  warn "Backend ist noch nicht installiert – 'make install' übernimmt das Passwort"
fi
