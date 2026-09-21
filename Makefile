.PHONY: catalog-check
PYTHON ?= python3

catalog-check: ## Katalog v1 gegen Schema und Fachregeln prüfen, Review-Tabelle ausgeben
	cd server && $(PYTHON) -m medvox.catalog.validate
