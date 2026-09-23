# Diktierhilfe – so versteht MedVox das Diktat

Eine Seite zum Ausdrucken. MedVox erkennt Sprache lokal auf dem Praxis-Mac und schlägt
Ziffern **nur aus dem geprüften Katalog** vor. Vorschläge sind Vorschläge – vor dem
Einfügen in Evident immer lesen.

## Die fünf Regeln

1. **Zahnnummern Ziffer für Ziffer:** „Zahn **drei sechs**", „**eins sechs**, **zwei sechs**".
   Nie „sechsunddreißig". Mehrere Zähne: „Zahn eins sechs zwei sechs" oder
   „drei sechs bis drei sieben" (Bereich).
2. **Flächen ausgesprochen, direkt hinter dem Zahn:** „Zahn drei sechs **mesial okklusal
   distal** Kompositfüllung" → 36 mod, 13c. Buchstaben („em o") und Flächen *hinter* dem
   Wort Füllung („Füllung mesial okklusal") werden nicht sicher gezählt – dann kommt 13a
   mit dem Hinweis „Flächenzahl nicht diktiert". Sicher ist auch das Zählwort:
   „Kompositfüllung **dreiflächig**".
3. **„geplant" in denselben Satzteil wie die Leistung:** „Zahn eins sechs
   Wurzelkanalaufbereitung **geplant**." → erscheint unter *Geplant*, nicht in den Ziffern.
   **Nicht** „Nächste Sitzung geplant: Zahn eins sechs WK" – Whisper macht aus dem
   Doppelpunkt oft ein Komma, dann gilt die WK als erbracht (so im Probelauf gesehen).
   Ebenso wirken „nächste Sitzung", „Termin", „Überweisung", „Wiedervorlage", „in zwei
   Wochen" – aber nur im eigenen Satzteil. „danach" oder „morgen" allein heißt *erbracht*.
4. **Eine Leistung, ein Satz – Zahn vorn:** „Zahn vier sechs Extraktion. Zahn drei sechs
   mesial okklusal Füllung." Kurze Sätze mit Punkt (Pause) sind sicherer als Ketten.
   Ohne Zahn in der Nähe nimmt MedVox den letzten Zahn davor im selben Satz.
5. **Verneinen hinter der Leistung:** „Zahn drei sechs Extraktion, **ohne** Anästhesie",
   „Infiltrationsanästhesie, **kein** Kofferdam". Vorsicht: „Zahn drei sechs ohne
   Anästhesie Extraktion" verneint auch die Extraktion (kein Vorschlag, nur ein Hinweis).

## Wörter, die die häufigen Ziffern auslösen

| Diktat (Beispiel) | Vorschlag |
|---|---|
| „Eingehende Untersuchung" | 01 |
| „PSI Code" | 04 |
| „Beratung" | Ä1 |
| „OPG" / „Zahnfilm Zahn drei sechs" | Ä935d / Ä925a |
| „Vitalitätsprüfung Zahn zwei eins" | 8 |
| „Infiltrationsanästhesie" / „Leitungsanästhesie drei acht" | 40 / 41a |
| „Kofferdam gelegt" | 12 |
| „Zahn drei sechs mesial okklusal Kompositfüllung" | 13b |
| „Karies profunda" (Überkappung) | 25 – prüfen, ist ein Befundwort |
| „Zahnsteinentfernung" | 107 |
| „Zahn eins eins Wurzelkanalbehandlung drei Kanäle" | 3x 32 |
| „Zahn vier sechs Extraktion" / „Zahn vier acht Osteotomie" | 44 / 47a |
| „Chlorhexidin Spülung" | 105 |
| „PZR" | 1040 (GOZ) |
| „BEMA dreizehn a", „GOZ zwei eins null null" | genau diese Ziffer |

Zu jeder BEMA-Ziffer zeigt MedVox das Privat-Gegenstück als *Alternative* (nicht in den
kopierten Ziffern). Die Umschaltung Kasse/Privat kommt mit einer späteren Version.

## „Ziffern kopieren" für Evident

Evident nimmt Abrechnungspositionen nur hinter einem Zahn an. „Ziffern kopieren" (iPad und
Rezeption) liefert deshalb **je Zahn eine Zeile**: erst der Zahn, dann seine Positionen,
kommagetrennt, in der Reihenfolge der Vorschläge. Mehrere Zähne stehen in der diktierten
Reihenfolge untereinander; der OP-Zuschlag 0500–0530 steht beim operierten Zahn. Positionen ohne
Zahn (01, Ä1, 107) kommen in eine letzte Zeile ohne Zahnnummer – die nimmt Evident so nicht an.
MedVox markiert diese Zeile am iPad und an der Rezeption mit „ohne Zahn – in Evident manuell
eintragen"; der Hinweis selbst wird nicht mitkopiert. Abgewählte Chips fehlen.

Diktat „Eingehende Untersuchung. Zahnfilm Zahn drei sechs, Leitungsanästhesie, Zahn drei sechs
mesial okklusal Kompositfüllung. Zahn vier sechs Extraktion. Zahnsteinentfernung." (Kasse):

```
36,Ä925a,l1,13b
46,44
01,107
```

Evident nimmt eine Mischung aus Ziffern und Kurzformen: steht im Katalog eine Evident-Kurzform
(Feld `evident`), wird sie statt der Ziffer kopiert (`l1` statt 41a), sonst die Ziffer.
Bisher bestätigt, für Kasse und privat: l1 (41a, GOZ 0100), wf (35), ost1 (47a, GOZ 3030), opg
(Ä935d, GOÄ Ä5004), pan1 (Ä935a, GOÄ Ä5002) – eine private Osteotomie an 48 kopiert als
`48,ost1,0500`; die Liste wächst mit den Meldungen aus dem Praxisalltag. Mehrfach erbrachte
Positionen stehen einmal mit Anzahl, hinter Kurzform wie Ziffer: drei Kanäle an 36 → `36,wf*3`,
`11,2410*3` (für Ziffern nach Auskunft des Behandlers, im Pilot noch an Evident zu prüfen).
Die Chips zeigen beides („41a · l1").
„Nur Ziffern" kopiert dieselben Zeilen nur mit amtlichen Ziffern (`36,35*3`), so geschrieben wie im
Katalog (GOÄ/BEMA-Röntgen mit „Ä", z. B. `Ä925a`); an der Rezeption gibt es nur „Ziffern kopieren".

## Bekannte Grenzen (ehrlich)

- **Der angezeigte Text** schreibt Zahnnummern als Ziffern („Zahn 36") und fügt Codes zusammen
  („BEMA 13a", „Ä935d"); Flächen und alles andere bleiben wie diktiert. Auch Zahlwörter werden
  Ziffern („drei Tage" → „3 Tage"). Messwertreihen („Sondierungstiefen 3 2 3") bleiben unverändert.
- **Reihenfolge zählt:** „Spülung mit Chlorhexidin" löst 105 *nicht* aus, „Chlorhexidin
  Spülung" schon.
- **Befundwörter** lösen Ziffern aus: „Karies profunda" → 25, „Längsfraktur" → 45,
  „Füllung intakt" würde als Füllung gelesen. Im Befund das Wort „Füllung" daher möglichst
  vermeiden oder den Vorschlag abwählen.
- **Zuordnung:** „36 o Karies, 37 mo Karies, Füllungen" ordnet die Füllung nur 37 zu – je Zahn
  einen Satz.
- Fehlen Flächen-, Kanal- oder Zahnangabe, kommt der kleinste Vorschlag mit Hinweis.
- Alter, PAR-Strecke, Frequenzen („einmal im Halbjahr") und die meisten
  Abrechnungsausschlüsse prüft MedVox **nicht**. Zuschlag 0500–0530 nur bei Chirurgie,
  die als GOZ diktiert wurde.
- Ein Abschnitt dauert höchstens 60 s – bei längeren Diktaten „Weiter" antippen.
- Echte Praxisakustik (Absauger, Maske) ist schlechter als die Testaufnahmen: nah ans iPad
  sprechen. Wiederkehrende Hörfehler notieren – sie kommen ins Wörterbuch bzw. in den
  Prompt (`infra/whisper/prompt.txt`).
