# Katalog v1 – BEMA/GOZ/GOÄ-Alltagspositionen (WP-7)

Der Katalog ist die einzige Quelle, aus der der Regel-Extraktor (WP-8) Ziffern vorschlagen darf.
Er ist bewusst klein (Alltag einer Zahnarztpraxis), vom Captain geprüft und ohne amtliche Volltexte.

| Datei | Zweck |
|---|---|
| `catalog_v1.json` | die 60–99 Alltagspositionen, die der Extraktor kennt (Quelle der Wahrheit, von Hand pflegbar) |
| `catalog_extended.json` | weitere geprüfte Positionen (Prothetik, PAR-Chirurgie, UPT, Kinder-Früherkennung …), gleiches Schema; wird nicht geladen, Saat für den Vollimport in Phase 2 |
| `schema.json` | JSON-Schema für beide Dateien |
| `validate.py` | prüft Schema + Fachregeln, druckt die Review-Tabelle (`cd server && make catalog-check` prüft beide Kataloge) |
| `review.py` | Prüftabellen Paare und Zuzahlungs-Liste (`python -m medvox.catalog.validate --markdown` für die PR-Beschreibung) |
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
  // "evident": "l1",                  // optional: Kurzform, die Evident statt der Ziffer erwartet (41a → l1);
                                       //   nur vom Behandler im Praxisbetrieb bestätigt, klein, nie aus abbrev
                                       //   abgeleitet (13c hat keine); Liste: docs/diktierhilfe.md
  "points": 53,                        // BEMA-Bewertungszahl bzw. GOZ/GOÄ-Punktzahl; null = nicht verifiziert
  "keywords": ["dreiflächig", "mod"],  // Auslösewörter, wie diktiert; klein geschrieben; kein Duplikat je System
  "rules": ["je Kanal", "..."],        // Freitext-Hinweise: Einheit, Alter, Gegenstück im anderen System
  "max_per": {"unit": "kieferhaelfte", "count": 1},   // Höchstzahl laut amtlichem Text (s. u.)
  "max_per_status": "bestaetigt",      // nur mit count: "vorschlag" (wirkt nicht) oder "bestaetigt" (wirkt)
  "surfaces_to_code": {"1": "13a", "2": "13b", "3": "13c", "4": "13d"},   // nur Füllungs-Familien
  "equivalent": [{"system": "GOZ", "code": "2100"}],   // Paar derselben Leistung im anderen System, beidseitig;
                                       //   optional "note": Unterschied, den der Behandler prüfen muss
  "zuzahlung": {                       // nur und immer bei GOZ/GOÄ: Zuzahlungs-Liste für Kassenpatienten
    "allowed": true,                   //   darf ein Kassenpatient diese Privatleistung bezahlen?
    "basis": ["13c"],                  //   BEMA-Ziffern, neben denen sie üblich ist ([] = eigenständig)
    "note": "Mehrkostenvereinbarung …",//   übliche Grundlage in einem Satz
    "sources": ["https://..."]         //   Beleg(e), stehen in meta.sources (system "Zuzahlung")
  },
  "sources": ["https://..."],          // Quelle(n), gegen die Ziffer/Kurztext/Punkte geprüft wurden
  "review": {"status": "draft"}        // draft | confirmed (+ optional date, note; note erscheint in PRUEFLISTE.md)
}
```

Regeln, die `validate.py` erzwingt: Ziffer je System eindeutig, Ziffernformat passt zum System,
kein exakt gleiches Keyword bei zwei Ziffern desselben Systems (BEMA und GOZ dürfen sich Wörter teilen),
`surfaces_to_code` zeigt nur auf vorhandene Ziffern und ist in der ganzen Familie identisch, jede Quelle
steht in `meta.sources`. Überlappende Phrasen wie `kürettage` (AITa) und `offene kürettage` (CPTa) sind
erlaubt: der Extraktor (WP-8) löst sie mit Longest-Match-wins auf, die längste passende Phrase gewinnt.

Paare (`equivalent`) verbinden BEMA und GOZ/GOÄ für dieselbe diktierte Leistung (Ost1 = BEMA 47a / GOZ 3030);
der Extraktor wählt mit dem Patiententyp genau eine Seite. Sie stehen immer beidseitig und nur innerhalb
einer Datei (`validate.py` prüft beides). Mehrere Paare sind erlaubt, wenn eine BEMA-Leistung im GOZ
aufgeteilt ist (BEMA 12 = GOZ 2030 oder 2040, BEMA 107 = GOZ 4050/4055 je Zahn, Ä925a–d = GOÄ Ä5000);
dann entscheidet das diktierte Wort. Die Abszesseröffnung wählt die Tiefe: oberflächlich BEMA Ä161 (Inz1)
= GOÄ Ä2428, tiefliegend nur GOÄ Ä2430 (kein BEMA-Paar, im BEMA ohne Ziffer); ein Wort ohne Tiefe
(„Inzision") gibt einen Prüfhinweis statt einer stillen Wahl (`extract_rules.py`). `zuzahlung` ist ein
Vorschlag zur Prüfung durch den Behandler, keine Rechtsberatung: `allowed: false` mit Begründung, wo die übliche Praxis umstritten oder nicht belegbar ist.

Höchstzahl (`max_per`): `count`-mal je `unit` – `sitzung` (ein Diktat ist eine Sitzung), `kieferhaelfte`
(je Kieferhälfte oder Frontzahnbereich), `zahn`, `kanal`, `flaeche` – oder `unbegrenzt` ohne `count`, wo
der amtliche Text keine Grenze nennt (nie eine erfinden). Jeder v1-Eintrag trägt das Feld, geprüft gegen
KZBV-Gesamtfassung bzw. GOZ-Text; Grenzen über längere Zeiträume („einmal je Kalenderhalbjahr“,
„höchstens zweimal je Jahr“) gelten mit derselben Anzahl je Sitzung. Jede Höchstzahl mit `count` trägt
`max_per_status`: `vorschlag` = aus dem amtlichen Text gelesen, wartet auf die Bestätigung des Behandlers;
`bestaetigt` = vom Behandler bestätigt. Der Extraktor begrenzt die Anzahl nur bei `bestaetigt`
(`extract_limits.py`), bisher nur BEMA 12; ein Vorschlag ändert an den Vorschlägen nichts, bis der
Behandler ihn bestätigt (ein Wechsel auf `bestaetigt` je Eintrag). Bereiche aus der FDI-Nummer: Frontzahnbereich = 13–23 bzw. 33–43,
Kieferhälfte = Seitenzähne 4–8 eines Quadranten (KZVB-Abrechnungsmappe zu BEMA 12). Im erweiterten
Katalog fehlt das Feld noch (gilt als ungeprüft/unbegrenzt).

Füllungs-Familien: die Materialwörter (füllung, komposit, …) stehen nur bei der einflächigen Ziffer
(13a, 2060; im erweiterten Katalog 2050, 2150); die Flächenzahl wählt über `surfaces_to_code` die
endgültige Ziffer. Eine Familie liegt immer vollständig in einer Datei.
Ein-/mehrwurzelig (43/44, AIT a/b, CPT a/b, UPT e/f) entscheidet der Extraktor aus der FDI-Nummer
nach der BEMA-Definition (einwurzelig: Frontzähne, OK 5er, UK 4er und 5er; mehrwurzelig: Molaren, OK 4er).

## Quellen und Stand

- BEMA: KZBV, Gesamt- und Kurzfassung, Stand 1. Januar 2026 (13a–d bereits mit den Werten nach dem
  Amalgam-Beschluss; 13e–h existieren nicht mehr).
- GOZ: GOZ 2012, Anlage 1, amtlicher Text auf gesetze-im-internet.de, gegengeprüft mit dem BZÄK-PDF.
- GOÄ: Anlage Gebührenverzeichnis auf gesetze-im-internet.de (Ä1, Ä5, Ä5000, Ä5002, Ä5004); Steigerungsfaktoren § 5 GOÄ (`go__1982/__5.html`).
- Punktwerte (§ 5): GOZ 5,62421 Cent, GOÄ 5,82873 Cent (in `meta.punktwert_cent`).
  BEMA-Punktwerte sind regional und stehen nicht im Katalog.

## Pflegen

1. Eintrag in `catalog_v1.json` (oder `catalog_extended.json`) ändern: Ziffer, Kurztext, Keywords, Regeln,
   oder `review.status` auf `confirmed` setzen. Punkte, die sich nicht belegen lassen, bleiben `null`.
2. `cd server && make catalog-check` – die Review-Tabelle zeigt Ziffer, Punkte (`?` = null), Kurztext,
   Keyword-Zahl, Status und listet alle Ziffern mit `null` unter „Punkte nicht verifiziert“.
3. `cd server && uv run pytest tests/test_catalog.py`.

## Patiententyp

Kassenpatienten bezahlen oft Privatleistungen neben der BEMA-Behandlung (Mehrkostenfüllung GOZ 2060–2120
neben 13a–d, PZR, elektrophysikalisch-chemische Aufbereitung in der Endodontie). Ein Behandlungsfall kann
deshalb BEMA- und GOZ-Positionen mischen – aber nur mit Positionen, deren `zuzahlung.allowed` true ist.
Privatpatienten bekommen nur GOZ/GOÄ. Der Zuschlag 0500–0530 gilt nur für Privatpatienten.

Die Zuzahlungs-Liste und die Paare sind recherchiert (KZVB-Abrechnungsmappe „Schnittstellen Bema/GOZ“,
KZVB-Merkblatt Endodontie, KZV-BW-Gegenüberstellung, KZBV-Festzuschuss-Kompendium, SGB V §§ 28/55, GOZ §§ 2/6,
ZÄK Berlin, BZÄK) und stehen zur Prüfung in `PRUEFLISTE.md` (`make catalog-review`). Grundsätze: Was BEMA
schon bezahlt, darf nicht zusätzlich privat berechnet werden; zulässig sind Mehrkosten (Füllungen, § 28 Abs. 2
SGB V), gleichartiger Zahnersatz (§ 55 Abs. 4) und Leistungen außerhalb der Kassenversorgung nach schriftlicher
Vereinbarung (§ 8 Abs. 7 BMV-Z). `allowed: false` steht auch dort, wo nur eine kommerzielle Quelle trägt
(0080, 4050/4055) oder die Bedingung („erst ab der 4. Einlage“) nicht aus dem Diktat folgt – dann nennt die Notiz
die Ausnahme. Eine Zuzahlung wird dem Kassenpatienten nur zusätzlich angeboten (`alternative`), wenn sie das Paar
der erbrachten BEMA-Position ist und deren Ziffer als Basis nennt (Mehrkostenfüllung zu 13a–d). Umgekehrt bringt
eine als GOZ diktierte Mehrkosten-Füllung oder ein Inlay (GOZ 2060–2120, 2150–2170) beim Kassenpatienten ihre
BEMA-Basis nach Flächenzahl mit (2080 → 13b, 2170 dreiflächig → 13c), denn die zahlt die Kasse.

Für den Patiententyp wurden die GOZ-Paare von v1-BEMA-Positionen (2020, 2350, 3020, 3300, 1000, 4000, 4020,
4070/4075) und die Inlays 2150–2170 nach v1 geholt; sie tragen `review.note` „neu, bitte prüfen“, das
`PRUEFLISTE.md` hinter der Ziffer zeigt. Eigenständige Privatleistungen ohne Paar (GOZ 2420, DVT GOÄ 5370/5377)
bleiben im erweiterten Katalog, bis der Behandler sie für v1 freigibt.

Bewusst nicht aufgenommen, weil ohne eigene Gebührennummer (nur Analogberechnung nach § 6 Abs. 1 GOZ) oder
beim Kassenpatienten nicht vereinbarungsfähig:

- maschinelle/rotierende Aufbereitung, NiTi-Feilen und Spülprotokolle neben BEMA 32 (Bestandteil der Aufbereitung,
  aufwändiges Spülen nur über den Faktor bei GOZ 2420);
- Dentalmikroskop GOZ 0110 (nur Zuschlag zu GOZ-Leistungen, neben einer Sachleistung nicht vereinbarungsfähig);
- photodynamische Therapie, Laser-/Ozon-Desinfektion, Bleaching (Verlangensleistung nach § 2 Abs. 3 GOZ),
  Lachgas-Sedierung – nur analog berechenbar;
- computergesteuerte Anästhesie: originär GOZ 0090/0100, beim Kassenpatienten also BEMA 40/41a ohne Zuzahlung;
- andersartiger Zahnersatz (§ 55 Abs. 5 SGB V) und die ganz private Endodontie außerhalb der Richtlinie: der ganze
  Fall wird nach GOZ berechnet – das ist kein Zuzahlungsfall neben BEMA, dafür bräuchte die App einen eigenen Modus.
