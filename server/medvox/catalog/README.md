# Katalog v1 – BEMA/GOZ/GOÄ-Alltagspositionen (WP-7)

Der Katalog ist die einzige Quelle, aus der der Regel-Extraktor (WP-8) Ziffern vorschlagen darf.
Er ist bewusst klein (Alltag einer Zahnarztpraxis), vom Captain geprüft und ohne amtliche Volltexte.

| Datei | Zweck |
|---|---|
| `catalog_v1.json` | die 60–84 Alltagspositionen, die der Extraktor kennt (Quelle der Wahrheit, von Hand pflegbar) |
| `catalog_extended.json` | weitere geprüfte Positionen (Prothetik, PAR-Chirurgie, UPT, Kinder-Früherkennung …), gleiches Schema; wird nicht geladen, Saat für den Vollimport in Phase 2 |
| `schema.json` | JSON-Schema für beide Dateien |
| `validate.py` | prüft Schema + Fachregeln, druckt die Review-Tabelle (`cd server && make catalog-check` prüft beide Kataloge) |
| `../../tests/test_catalog.py` | pytest: beide Kataloge gültig, zusammen widerspruchsfrei, Validator findet echte Fehler |

## Eintrag (Entry-Form)

```json
{
  "code": "13c",                       // Ziffer wie in der Praxissoftware: 13a, 2080, Ä935d, AITa, IP5
  "system": "BEMA",                    // BEMA | GOZ | GOÄ
  "area": "Konservierend",             // Fachbereich (Diagnostik, Röntgen, Anästhesie, Konservierend,
                                       //   Endodontie, Chirurgie, Prophylaxe, PAR, Prothetik)
  "title": "Füllung, dreiflächig",     // eigener Kurztext, kein amtlicher Volltext (Lizenz)
  "abbrev": "F3",                      // optional, nur BEMA: amtliche Kurzbezeichnung
  "points": 53,                        // BEMA-Bewertungszahl bzw. GOZ/GOÄ-Punktzahl; null = nicht verifiziert
  "keywords": ["dreiflächig", "mod"],  // Auslösewörter, wie diktiert; klein geschrieben; kein Duplikat je System
  "rules": ["je Kanal", "..."],        // Freitext-Hinweise: Einheit, Alter, Gegenstück im anderen System
  "surfaces_to_code": {"1": "13a", "2": "13b", "3": "13c", "4": "13d"},   // nur Füllungs-Familien
  "sources": ["https://..."],          // Quelle(n), gegen die Ziffer/Kurztext/Punkte geprüft wurden
  "review": {"status": "draft"}        // draft | confirmed (+ optional date, note)
}
```

Regeln, die `validate.py` erzwingt: Ziffer je System eindeutig, Ziffernformat passt zum System,
kein exakt gleiches Keyword bei zwei Ziffern desselben Systems (BEMA und GOZ dürfen sich Wörter teilen),
`surfaces_to_code` zeigt nur auf vorhandene Ziffern und ist in der ganzen Familie identisch, jede Quelle
steht in `meta.sources`. Überlappende Phrasen wie `kürettage` (AITa) und `offene kürettage` (CPTa) sind
erlaubt: der Extraktor (WP-8) löst sie mit Longest-Match-wins auf, die längste passende Phrase gewinnt.

Füllungs-Familien: die Materialwörter (füllung, komposit, …) stehen nur bei der einflächigen Ziffer
(13a, 2060; im erweiterten Katalog 2050, 2150); die Flächenzahl wählt über `surfaces_to_code` die
endgültige Ziffer. Eine Familie liegt immer vollständig in einer Datei.
Ein-/mehrwurzelig (43/44, AIT a/b, CPT a/b, UPT e/f) entscheidet der Extraktor aus der FDI-Nummer
nach der BEMA-Definition (einwurzelig: Frontzähne, OK 5er, UK 4er und 5er; mehrwurzelig: Molaren, OK 4er).

## Quellen und Stand

- BEMA: KZBV, Gesamt- und Kurzfassung, Stand 1. Januar 2026 (13a–d bereits mit den Werten nach dem
  Amalgam-Beschluss; 13e–h existieren nicht mehr).
- GOZ: GOZ 2012, Anlage 1, amtlicher Text auf gesetze-im-internet.de, gegengeprüft mit dem BZÄK-PDF.
- GOÄ: Anlage Gebührenverzeichnis auf gesetze-im-internet.de (Ä1, Ä5, Ä5000, Ä5002, Ä5004).
- Punktwerte (§ 5): GOZ 5,62421 Cent, GOÄ 5,82873 Cent (in `meta.punktwert_cent`).
  BEMA-Punktwerte sind regional und stehen nicht im Katalog.

## Pflegen

1. Eintrag in `catalog_v1.json` (oder `catalog_extended.json`) ändern: Ziffer, Kurztext, Keywords, Regeln,
   oder `review.status` auf `confirmed` setzen. Punkte, die sich nicht belegen lassen, bleiben `null`.
2. `cd server && make catalog-check` – die Review-Tabelle zeigt Ziffer, Punkte (`?` = null), Kurztext,
   Keyword-Zahl, Status und listet alle Ziffern mit `null` unter „Punkte nicht verifiziert“.
3. `cd server && uv run pytest tests/test_catalog.py`.

## Hinweise für Phase 2

- Kassenpatienten erbringen häufig Zuzahlungen als Privatleistung (z. B. GOZ-Kompositfüllungen
  statt BEMA 13a–d). Ein Kassenpatient wird also **nicht** immer rein nach BEMA abgerechnet;
  ein Behandlungsfall kann BEMA- und GOZ-Positionen mischen. Extraktor (WP-8) und Oberfläche
  dürfen nicht annehmen, dass „Kassenpatient" gleich „nur BEMA" bedeutet.
