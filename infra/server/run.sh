#!/bin/bash
# Startskript des Backends für launchd (de.medvox.server). Wird von
# infra/server/install.sh nach ~/Library/Application Support/MedVox/server/
# kopiert und von dort gestartet – nie aus dem Repo.
#
# Liest den Passwort-Hash aus ../password-hash (geschrieben von
# `make set-password`), damit er weder in der plist noch in einer Shell steht.
# Ohne Zugriffslog: Anfrage-URLs enthalten Kurzcodes (AGENTS.md: Logs ohne Inhalte).
# --timeout-graceful-shutdown: offene Live-Ströme des Büros (/api/v1/events) halten einen
# Neustart nicht auf; die Seiten verbinden sich von selbst neu.

set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"
hash_file="$dir/../password-hash"
if [[ -s "$hash_file" ]]; then
  MEDVOX_PASSWORD_HASH="$(tr -d '\n' < "$hash_file")"
  export MEDVOX_PASSWORD_HASH
else
  echo "Kein Passwort gesetzt ($hash_file fehlt) – Anmeldung antwortet mit 503. Abhilfe: make set-password" >&2
fi
exec "$dir/.venv/bin/uvicorn" medvox.main:app --app-dir "$dir" --no-access-log --timeout-graceful-shutdown 3 "$@"
