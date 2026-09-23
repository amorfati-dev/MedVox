# MedVox auf dem Praxis-Mac – Befehle für den Betrieb (Entwicklung: server/Makefile, app/package.json).

.PHONY: install status set-password restart-test

# Alles installieren bzw. nach einem Update nachziehen. Vorhandenes Modell: make install MODEL=/pfad/…bin
install:
	@infra/install.sh $(MODEL)

# Gesamtzustand in einer deutschen Übersicht; Exit-Code ≠ 0 bei jedem echten Problem.
status:
	@infra/status.sh

# Behandler-Passwort setzen oder ändern (speichert nur den Hash, startet das Backend neu).
set-password:
	@infra/server/set-password.sh

# Jeden Dienst hart neu starten und messen, bis er wieder antwortet.
restart-test:
	@infra/restart-test.sh
