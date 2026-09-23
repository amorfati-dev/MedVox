# Prüfliste Patiententyp: Paare und Zuzahlungs-Liste

Erzeugt aus `catalog_v1.json` und `catalog_extended.json` mit `make catalog-review` – nicht von Hand
ändern, sondern den Katalog. Bewusst nicht aufgenommene Leistungen: `README.md`, Abschnitt „Patiententyp“.
**Vorschlag zur Prüfung durch den Behandler, keine Rechtsberatung.** Je Zeile abhaken oder streichen.

- **Paar:** dieselbe diktierte Leistung in BEMA und GOZ/GOÄ; der Patiententyp wählt genau eine Ziffer
  (Kassenpatient BEMA, Privatpatient GOZ/GOÄ), nie beide. Der Hinweis erscheint beim Umstellen als Prüfpunkt.
- **Zuzahlung „ja“:** der Extraktor schlägt die Privatleistung auch beim Kassenpatienten vor, als
  `zuzahlung` markiert. „nein“: beim Kassenpatienten nie (Kassenleistung, umstritten oder nicht belegt).
- **BEMA-Bezug:** bei „ja“ die BEMA-Position, neben der sie üblich ist (– = eigenständige Privatleistung),
  bei „nein“ die Kassenleistung, die sie abdeckt.

## Katalog v1 (wird geladen)

### Paare BEMA ↔ GOZ/GOÄ

| ☐ | BEMA | Kurztext | Privat | Kurztext | Hinweis | Quelle |
|---|---|---|---|---|---|---|
| ☐ | Ä1 | Beratung | GOÄ Ä1 | Beratung |  | [Q1] [Q2] [Q3] |
| ☐ | 01 | Eingehende Untersuchung | GOZ 0010 | Eingehende Untersuchung |  | [Q1] [Q4] [Q3] |
| ☐ | 04 | PSI (Parodontaler Screening-Index) | GOZ 4005 | Gingival-/Parodontalindex (z. B. PSI) |  | [Q1] [Q4] [Q3] |
| ☐ | 8 | Sensibilitätsprüfung | GOZ 0070 | Vitalitätsprüfung, je Sitzung |  | [Q1] [Q4] [Q3] |
| ☐ | Ä925a | Zahnfilm, bis 2 Aufnahmen | GOÄ Ä5000 | Zahnfilm, je Projektion | GOÄ Ä5000 zählt je Projektion (BEMA Ä925a: 1–2 Aufnahmen) – Anzahl prüfen | [Q1] [Q2] [Q3] |
| ☐ | Ä925b | Zahnfilme, 3 bis 5 Aufnahmen | GOÄ Ä5000 | Zahnfilm, je Projektion | GOÄ Ä5000 zählt je Projektion (BEMA Ä925b: 3–5 Aufnahmen) – Anzahl prüfen | [Q1] [Q2] [Q3] |
| ☐ | Ä925c | Zahnfilme, 6 bis 8 Aufnahmen | GOÄ Ä5000 | Zahnfilm, je Projektion | GOÄ Ä5000 zählt je Projektion (BEMA Ä925c: 6–8 Aufnahmen) – Anzahl prüfen | [Q1] [Q2] [Q3] |
| ☐ | Ä925d | Röntgenstatus, mehr als 8 Aufnahmen | GOÄ Ä5000 | Zahnfilm, je Projektion | GOÄ Ä5000 zählt je Projektion (BEMA Ä925d: mehr als 8 Aufnahmen) – Anzahl prüfen | [Q1] [Q2] [Q3] |
| ☐ | Ä935d | OPG (Orthopantomogramm) | GOÄ Ä5004 | OPG (Panoramaschichtaufnahme) |  | [Q1] [Q2] [Q3] |
| ☐ | Ä935a | Teilaufnahme Schädel / Panoramaaufnahme eines Kiefers, eine Aufnahme | GOÄ Ä5002 | Panoramaaufnahme(n) eines Kiefers | BEMA Ä935a umfasst auch Schädelteilaufnahmen; GOÄ Ä5002 nur die Panoramaaufnahme eines Kiefers | [Q1] [Q2] [Q3] |
| ☐ | 40 | Infiltrationsanästhesie | GOZ 0090 | Infiltrationsanästhesie | BEMA 40 gilt je Sitzung für bis zu 2 Nachbarzähne, GOZ 0090 je Zahn – Zähne prüfen | [Q1] [Q4] [Q3] |
| ☐ | 41a | Leitungsanästhesie, intraoral | GOZ 0100 | Leitungsanästhesie, intraoral |  | [Q1] [Q4] [Q3] |
| ☐ | 13a | Füllung, einflächig | GOZ 2060 | Kompositfüllung adhäsiv, einflächig | GOZ 2060–2120 setzt Adhäsivtechnik voraus; selbstadhäsiv/Bulkfill ohne Konditionieren wäre GOZ 2050–2110 – prüfen | [Q1] [Q4] [Q3] |
| ☐ | 13b | Füllung, zweiflächig | GOZ 2080 | Kompositfüllung adhäsiv, zweiflächig | GOZ 2060–2120 setzt Adhäsivtechnik voraus; selbstadhäsiv/Bulkfill ohne Konditionieren wäre GOZ 2050–2110 – prüfen | [Q1] [Q4] [Q3] |
| ☐ | 13c | Füllung, dreiflächig | GOZ 2100 | Kompositfüllung adhäsiv, dreiflächig | GOZ 2060–2120 setzt Adhäsivtechnik voraus; selbstadhäsiv/Bulkfill ohne Konditionieren wäre GOZ 2050–2110 – prüfen | [Q1] [Q4] [Q3] |
| ☐ | 13d | Füllung, mehr als dreiflächig / Eckenaufbau | GOZ 2120 | Kompositfüllung adhäsiv, mehr als dreiflächig | GOZ 2060–2120 setzt Adhäsivtechnik voraus; selbstadhäsiv/Bulkfill ohne Konditionieren wäre GOZ 2050–2110 – prüfen | [Q1] [Q4] [Q3] |
| ☐ | 11 | Provisorischer Verschluss / unvollendete Füllung | GOZ 2020 | Temporärer speicheldichter Verschluss |  | [Q1] [Q4] [Q3] |
| ☐ | 12 | Besondere Maßnahmen (Kofferdam, Separieren) | GOZ 2030 | Besondere Maßnahmen beim Präparieren/Füllen |  | [Q1] [Q4] [Q3] |
| ☐ | 12 | Besondere Maßnahmen (Kofferdam, Separieren) | GOZ 2040 | Kofferdam (Spanngummi) |  | [Q1] [Q4] [Q3] |
| ☐ | 25 | Indirekte Überkappung | GOZ 2330 | Indirekte Überkappung, je Kavität |  | [Q1] [Q4] [Q3] |
| ☐ | 26 | Direkte Überkappung | GOZ 2340 | Direkte Überkappung, je Kavität |  | [Q1] [Q4] [Q3] |
| ☐ | 27 | Pulpotomie | GOZ 2350 | Amputation und Versorgung der vitalen Pulpa (Pulpotomie) |  | [Q1] [Q4] [Q3] |
| ☐ | 28 | Vitalexstirpation, je Kanal | GOZ 2360 | Vitalexstirpation, je Kanal |  | [Q1] [Q4] [Q3] |
| ☐ | 31 | Trepanation eines pulpatoten Zahnes | GOZ 2390 | Trepanation, als selbstständige Leistung |  | [Q1] [Q4] [Q3] |
| ☐ | 32 | Wurzelkanalaufbereitung, je Kanal | GOZ 2410 | Wurzelkanalaufbereitung, je Kanal |  | [Q1] [Q4] [Q3] |
| ☐ | 34 | Medikamentöse Einlage | GOZ 2430 | Medikamentöse Einlage |  | [Q1] [Q4] [Q3] |
| ☐ | 35 | Wurzelkanalfüllung, je Kanal | GOZ 2440 | Wurzelkanalfüllung |  | [Q1] [Q4] [Q3] |
| ☐ | 43 | Extraktion, einwurzeliger Zahn | GOZ 3000 | Extraktion, einwurzeliger Zahn / Implantat |  | [Q1] [Q4] [Q3] |
| ☐ | 44 | Extraktion, mehrwurzeliger Zahn | GOZ 3010 | Extraktion, mehrwurzeliger Zahn |  | [Q1] [Q4] [Q3] |
| ☐ | 45 | Extraktion, tieffrakturierter Zahn | GOZ 3020 | Extraktion, tief frakturierter/zerstörter Zahn |  | [Q1] [Q4] [Q3] |
| ☐ | 47a | Osteotomie (Zahnentfernung durch Osteotomie) | GOZ 3030 | Osteotomie (Zahn/Implantat) |  | [Q1] [Q4] [Q3] |
| ☐ | 48 | Osteotomie, retinierter/verlagerter Zahn | GOZ 3040 | Osteotomie, retinierter/verlagerter Zahn |  | [Q1] [Q4] [Q3] |
| ☐ | 38 | Nachbehandlung nach chirurgischem Eingriff | GOZ 3300 | Nachbehandlung nach chirurgischem Eingriff (z. B. Tamponieren) |  | [Q1] [Q4] [Q3] |
| ☐ | 38 | Nachbehandlung nach chirurgischem Eingriff | GOZ 3290 | Kontrolle nach chirurgischem Eingriff | GOZ 3290 ist die reine Kontrolle; mit Behandlung (Tamponieren, Spülen) GOZ 3300 – prüfen | [Q1] [Q4] [Q3] |
| ☐ | 105 | Lokale Schleimhautbehandlung / Druckstelle | GOZ 4020 | Lokalbehandlung Mundschleimhaut / Taschenspülung |  | [Q1] [Q4] [Q3] |
| ☐ | 107 | Entfernung harter Zahnbeläge (Zahnstein) | GOZ 4050 | Zahnsteinentfernung, einwurzeliger Zahn | BEMA 107 gilt je Sitzung, GOZ 4050/4055 je Zahn – Zähne prüfen | [Q1] [Q4] [Q3] |
| ☐ | 107 | Entfernung harter Zahnbeläge (Zahnstein) | GOZ 4055 | Zahnsteinentfernung, mehrwurzeliger Zahn |  | [Q1] [Q4] [Q3] |
| ☐ | IP1 | Mundhygienestatus | GOZ 1000 | Mundhygienestatus und Unterweisung (mind. 25 min) | GOZ 1000 umfasst Status und Unterweisung, mindestens 25 Minuten – prüfen | [Q1] [Q4] [Q3] |
| ☐ | IP2 | Mundgesundheitsaufklärung | GOZ 1000 | Mundhygienestatus und Unterweisung (mind. 25 min) | GOZ 1000 umfasst Status und Unterweisung, mindestens 25 Minuten – prüfen | [Q1] [Q4] [Q3] |
| ☐ | IP4 | Lokale Fluoridierung | GOZ 1020 | Lokale Fluoridierung, je Sitzung |  | [Q1] [Q4] [Q3] |
| ☐ | IP5 | Fissurenversiegelung 6er/7er, je Zahn | GOZ 2000 | Fissurenversiegelung, je Zahn |  | [Q1] [Q4] [Q3] |
| ☐ | 4 | Parodontalstatus (PAR-Status) | GOZ 4000 | Parodontalstatus |  | [Q1] [Q4] [Q3] |
| ☐ | MHU | Patientenindividuelle Mundhygieneunterweisung | GOZ 1000 | Mundhygienestatus und Unterweisung (mind. 25 min) | kein inhaltsgleiches GOZ-Gegenstück; KZV BW vergleicht MHU mit GOZ 1000 – prüfen | [Q1] [Q4] [Q3] |
| ☐ | AITa | Antiinfektiöse Therapie, einwurzeliger Zahn | GOZ 4070 | Geschlossene Kürettage, einwurzeliger Zahn | KZV BW vergleicht AIT mit GOZ 4050 + 4070 (ggf. 4080) – prüfen | [Q1] [Q4] [Q3] |
| ☐ | AITb | Antiinfektiöse Therapie, mehrwurzeliger Zahn | GOZ 4075 | Geschlossene Kürettage, mehrwurzeliger Zahn | KZV BW vergleicht AIT mit GOZ 4055 + 4075 (ggf. 4080) – prüfen | [Q1] [Q4] [Q3] |
| ☐ | BEVa | Befundevaluation nach AIT | GOZ 4000 | Parodontalstatus | Befundevaluation hat kein eigenes GOZ-Gegenstück; privat über den Parodontalstatus GOZ 4000 – prüfen | [Q1] [Q4] [Q3] |

### Zuzahlung – Diagnostik

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 0010 | Eingehende Untersuchung | 01 | Kassenleistung BEMA 01 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q1] [Q5] |
| ☐ | nein | GOZ 0070 | Vitalitätsprüfung, je Sitzung | 8 | Kassenleistung BEMA 8 – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | nein | GOÄ Ä1 | Beratung | Ä1 | Kassenleistung BEMA Ä1 – privat nicht zusätzlich berechenbar. | [Q1] |
| ☐ | nein | GOÄ Ä5 | Symptombezogene Untersuchung | 01 | Symptombezogene Untersuchung ist beim Kassenpatienten mit 01/Ä1 abgegolten. | [Q1] |

### Zuzahlung – Röntgen

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOÄ Ä5000 | Zahnfilm, je Projektion | Ä925a, Ä925b, Ä925c, Ä925d | Kassenleistung BEMA Ä925 – privat nicht zusätzlich berechenbar. | [Q1] [Q6] |
| ☐ | nein | GOÄ Ä5004 | OPG (Panoramaschichtaufnahme) | Ä935d | Kassenleistung BEMA Ä935d – privat nicht zusätzlich berechenbar. | [Q1] |
| ☐ | nein | GOÄ Ä5002 | Panoramaaufnahme(n) eines Kiefers | Ä935a | Kassenleistung BEMA Ä935 – privat nicht zusätzlich berechenbar. | [Q1] |
| ☐ | ja | GOÄ Ä5370 | Computergesteuerte Tomographie im Kopfbereich (DVT) | – | DVT ist keine BEMA-Leistung; beim Kassenpatienten nur als Privatleistung nach GOÄ 5370 (+ ggf. 5377). | [Q1] [Q7] [Q8] |
| ☐ | ja | GOÄ Ä5377 | Zuschlag computergesteuerte Analyse mit 3D-Rekonstruktion | – | Zuschlag für computergesteuerte 3D-Analyse zur privaten DVT; nur zum einfachen Satz. | [Q2] [Q7] |

### Zuzahlung – Anästhesie

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 0080 | Oberflächenanästhesie | – | Nicht belegt: nur ein kommerzielles Portal nennt die Oberflächenanästhesie privat vereinbar; amtlich steht nur fest, dass BEMA sie nicht enthält. | [Q9] [Q1] [Q3] |
| ☐ | nein | GOZ 0090 | Infiltrationsanästhesie | 40 | Kassenleistung BEMA 40; Ausnahme: Anästhesie zu einer Privatleistung (z. B. Inlay) ist GOZ 0090. | [Q1] [Q10] [Q11] |
| ☐ | nein | GOZ 0100 | Leitungsanästhesie, intraoral | 41a | Kassenleistung BEMA 41a; Ausnahme: Anästhesie zu einer Privatleistung (z. B. Inlay) ist GOZ 0100. | [Q1] [Q10] [Q11] |

### Zuzahlung – Konservierend

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | ja | GOZ 2000 | Fissurenversiegelung, je Zahn | – | Nur außerhalb IP5 privat vereinbar (Prämolaren, andere Zähne, Erwachsene); 6er/7er bis 17 J. sind IP5. | [Q12] [Q13] |
| ☐ | nein | GOZ 2020 | Temporärer speicheldichter Verschluss | 11 | Kassenleistung BEMA 11; in BEMA 25/34 ist der provisorische Verschluss enthalten. | [Q1] [Q3] |
| ☐ | ja | GOZ 2030 | Besondere Maßnahmen beim Präparieren/Füllen | 13a, 13b, 13c, 13d | Nur neben mehrkostenfähiger Füllung für getrennte Arbeitsschritte (z. B. Formgebungshilfe), sonst BEMA 12. | [Q10] |
| ☐ | ja | GOZ 2040 | Kofferdam (Spanngummi) | – | Kofferdam ist in BEMA 12 enthalten; privat nur, wenn er für eine Privatleistung (z. B. 2400/2420, Inlay) gelegt wird. | [Q1] [Q14] [Q10] |
| ☐ | ja | GOZ 2060 | Kompositfüllung adhäsiv, einflächig | 13a | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt BEMA 13a, Patient die Differenz – nur Mehrfarbentechnik oder adhäsive Seitenzahnfüllung außerhalb der Bulkfill-Regel. | [Q1] [Q10] [Q15] |
| ☐ | ja | GOZ 2080 | Kompositfüllung adhäsiv, zweiflächig | 13b | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt BEMA 13b, Patient die Differenz – nur Mehrfarbentechnik oder adhäsive Seitenzahnfüllung außerhalb der Bulkfill-Regel. | [Q1] [Q10] [Q15] |
| ☐ | ja | GOZ 2100 | Kompositfüllung adhäsiv, dreiflächig | 13c | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt BEMA 13c, Patient die Differenz – nur Mehrfarbentechnik oder adhäsive Seitenzahnfüllung außerhalb der Bulkfill-Regel. | [Q1] [Q10] [Q15] |
| ☐ | ja | GOZ 2120 | Kompositfüllung adhäsiv, mehr als dreiflächig | 13d | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt BEMA 13d, Patient die Differenz – nur Mehrfarbentechnik oder adhäsive Seitenzahnfüllung außerhalb der Bulkfill-Regel. | [Q1] [Q10] [Q15] |
| ☐ | ja | GOZ 2150 | Einlagefüllung (Inlay), einflächig | 13a, 13b, 13c, 13d | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt die vergleichbare BEMA-13-Füllung, Patient den Rest; Begleitanästhesie und Kofferdam sind privat. | [Q1] [Q15] [Q10] |
| ☐ | ja | GOZ 2160 | Einlagefüllung (Inlay), zweiflächig | 13a, 13b, 13c, 13d | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt die vergleichbare BEMA-13-Füllung, Patient den Rest; Begleitanästhesie und Kofferdam sind privat. | [Q1] [Q15] [Q10] |
| ☐ | ja | GOZ 2170 | Einlagefüllung (Inlay), mehr als zweiflächig | 13a, 13b, 13c, 13d | Mehrkostenvereinbarung nach § 28 Abs. 2 SGB V: Kasse zahlt die vergleichbare BEMA-13-Füllung, Patient den Rest; Begleitanästhesie und Kofferdam sind privat. | [Q1] [Q15] [Q10] |
| ☐ | ja | GOZ 2197 | Adhäsive Befestigung | 34, 35, 18a | Privat vereinbar für adhäsive Befestigung des provisorischen Verschlusses, der Wurzelfüllung oder eines Glasfaserstifts (gleichartig). | [Q14] [Q6] [Q16] |
| ☐ | nein | GOZ 2330 | Indirekte Überkappung, je Kavität | 25 | Kassenleistung BEMA 25 – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | nein | GOZ 2340 | Direkte Überkappung, je Kavität | 26 | Kassenleistung BEMA 26 – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | nein | GOZ 2350 | Amputation und Versorgung der vitalen Pulpa (Pulpotomie) | 27 | Kassenleistung BEMA 27 (vitale Pulpotomie) – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |

### Zuzahlung – Endodontie

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 2360 | Vitalexstirpation, je Kanal | 28 | Kassenleistung BEMA 28 – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | nein | GOZ 2390 | Trepanation, als selbstständige Leistung | 31 | Kassenleistung BEMA 31 – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | ja | GOZ 2400 | Elektrometrische Längenbestimmung | 32 | Keine Kassenleistung; neben BEMA 32 privat nach § 8 Abs. 7 BMV-Z vor Behandlungsbeginn vereinbar. | [Q14] [Q6] [Q1] |
| ☐ | nein | GOZ 2410 | Wurzelkanalaufbereitung, je Kanal | 32 | Kassenleistung BEMA 32; nur wenn die ganze Endo richtlinienbedingt oder auf Wunsch privat ist, gilt GOZ 2410. | [Q1] [Q6] [Q17] |
| ☐ | ja | GOZ 2420 | Elektrophysikalisch-chemische Methoden, je Kanal | 32 | Keine Kassenleistung; neben BEMA 32 privat nach § 8 Abs. 7 BMV-Z vereinbar (je Kanal). | [Q14] [Q6] |
| ☐ | ja | GOZ 2430 | Medikamentöse Einlage | – | Nur ab der 4. medikamentösen Einlage privat vereinbar, weil BEMA 34 auf drei Sitzungen begrenzt ist; sonst BEMA 34. | [Q14] [Q1] |
| ☐ | nein | GOZ 2440 | Wurzelkanalfüllung | 35 | Kassenleistung BEMA 35; nur die adhäsive Befestigung (2197) ist privat vereinbar. | [Q1] [Q14] |

### Zuzahlung – Chirurgie

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 3000 | Extraktion, einwurzeliger Zahn / Implantat | 43 | Kassenleistung BEMA 43 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3010 | Extraktion, mehrwurzeliger Zahn | 44 | Kassenleistung BEMA 44 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3020 | Extraktion, tief frakturierter/zerstörter Zahn | 45 | Kassenleistung BEMA 45 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3030 | Osteotomie (Zahn/Implantat) | 47a | Kassenleistung BEMA 47a – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3040 | Osteotomie, retinierter/verlagerter Zahn | 48 | Kassenleistung BEMA 48 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3290 | Kontrolle nach chirurgischem Eingriff | 38 | Umstritten: Kontrolle ohne Nachbehandlung hat kein BEMA-Pendant, ist aber medizinisch notwendig; keine Quelle für private Vereinbarung gefunden. | [Q3] [Q1] |
| ☐ | nein | GOZ 3300 | Nachbehandlung nach chirurgischem Eingriff (z. B. Tamponieren) | 38 | Kassenleistung BEMA 38 (Nachbehandlung) – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | nein | GOZ 0500 | Zuschlag zu chirurgischen Leistungen (250–499 Punkte, auch 4090/4130) | – | Beim Kassenpatienten nie vorgeschlagen (Zuschlag nur für Privatpatienten); rechtlich nur zu privat vereinbarter GOZ-Chirurgie wie 4130 denkbar. | [Q18] [Q19] [Q4] |
| ☐ | nein | GOZ 0510 | Zuschlag zu chirurgischen Leistungen (500–799 Punkte) | – | Beim Kassenpatienten nie vorgeschlagen (Zuschlag nur für Privatpatienten); rechtlich nur zu privat vereinbarter GOZ-Chirurgie wie 4130 denkbar. | [Q18] [Q19] [Q4] |
| ☐ | nein | GOZ 0520 | Zuschlag zu chirurgischen Leistungen (800–1199 Punkte) | – | Beim Kassenpatienten nie vorgeschlagen (Zuschlag nur für Privatpatienten); rechtlich nur zu privat vereinbarter GOZ-Chirurgie wie 4130 denkbar. | [Q18] [Q19] [Q4] |
| ☐ | nein | GOZ 0530 | Zuschlag zu chirurgischen Leistungen (ab 1200 Punkte) | – | Beim Kassenpatienten nie vorgeschlagen (Zuschlag nur für Privatpatienten); rechtlich nur zu privat vereinbarter GOZ-Chirurgie wie 4130 denkbar. | [Q18] [Q19] [Q4] |

### Zuzahlung – Prophylaxe

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | ja | GOZ 1020 | Lokale Fluoridierung, je Sitzung | – | Erwachsene: keine Sachleistung, privat vereinbar; 6–17 J. und Kleinkinder sind IP4/FLA Kassenleistung. | [Q13] [Q1] |
| ☐ | ja | GOZ 1000 | Mundhygienestatus und Unterweisung (mind. 25 min) | – | Erwachsene: keine Sachleistung, privat vereinbar; 6–17 J. nur über die IP1/IP2-Häufigkeit hinaus. | [Q12] [Q13] |
| ☐ | ja | GOZ 1040 | Professionelle Zahnreinigung, je Zahn | – | Keine Kassenleistung; privat vereinbar, auch in derselben Sitzung nach vollständig erbrachter BEMA 107. | [Q13] [Q20] |

### Zuzahlung – PAR

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 4000 | Parodontalstatus | 4 | Kassenleistung BEMA 4 in der PAR-Strecke; privat nur bei rein privater PAR-Behandlung außerhalb der Richtlinie. | [Q3] [Q20] |
| ☐ | nein | GOZ 4005 | Gingival-/Parodontalindex (z. B. PSI) | 04 | Kassenleistung BEMA 04 (alle zwei Jahre); keine Quelle für private Zwischenerhebung gefunden. | [Q3] [Q13] |
| ☐ | nein | GOZ 4020 | Lokalbehandlung Mundschleimhaut / Taschenspülung | 105 | Kassenleistung BEMA 105 – privat nicht zusätzlich berechenbar. | [Q3] |
| ☐ | nein | GOZ 4050 | Zahnsteinentfernung, einwurzeliger Zahn | 107 | Kassenleistung BEMA 107; privat nur, wenn 107 im Kalenderjahr verbraucht ist – dafür nur kommerzielle Quelle, nie neben 107 in derselben Sitzung. | [Q21] [Q13] |
| ☐ | nein | GOZ 4055 | Zahnsteinentfernung, mehrwurzeliger Zahn | 107 | Kassenleistung BEMA 107; privat nur, wenn 107 im Kalenderjahr verbraucht ist – dafür nur kommerzielle Quelle, nie neben 107 in derselben Sitzung. | [Q21] [Q13] |
| ☐ | ja | GOZ 4070 | Geschlossene Kürettage, einwurzeliger Zahn | – | Nur außerhalb einer richtliniengemäßen PAR-Behandlung privat; in der Kassen-PAR gilt AITa/UPTe. | [Q13] [Q20] |
| ☐ | ja | GOZ 4075 | Geschlossene Kürettage, mehrwurzeliger Zahn | – | Nur außerhalb einer richtliniengemäßen PAR-Behandlung privat; in der Kassen-PAR gilt AITb/UPTf. | [Q13] [Q20] |

## Erweiterter Katalog (Saat für Phase 2, wird nicht geladen)

### Paare BEMA ↔ GOZ/GOÄ

| ☐ | BEMA | Kurztext | Privat | Kurztext | Hinweis | Quelle |
|---|---|---|---|---|---|---|
| ☐ | 10 | Behandlung überempfindlicher Zähne | GOZ 2010 | Behandlung überempfindlicher Zahnflächen, je Kiefer |  | [Q1] [Q4] |
| ☐ | CPTa | Chirurgische Therapie, einwurzeliger Zahn | GOZ 4090 | Lappenoperation Frontzahn, je Parodontium | GOZ 4090 gilt nur im Frontzahnbereich; einwurzelige Prämolaren sind GOZ 4100 – prüfen | [Q1] [Q4] |
| ☐ | CPTb | Chirurgische Therapie, mehrwurzeliger Zahn | GOZ 4100 | Lappenoperation Seitenzahn, je Parodontium |  | [Q1] [Q4] |
| ☐ | 19 | Provisorische Krone / provisorisches Brückenglied | GOZ 2270 | Provisorium direkt, mit Abformung |  | [Q1] [Q4] |
| ☐ | 19 | Provisorische Krone / provisorisches Brückenglied | GOZ 2260 | Provisorium direkt, ohne Abformung |  | [Q1] [Q4] |
| ☐ | 20a | Metallische Vollkrone | GOZ 2210 | Vollkrone, Hohlkehl-/Stufenpräparation |  | [Q1] [Q4] |
| ☐ | 20a | Metallische Vollkrone | GOZ 2200 | Vollkrone, Tangentialpräparation |  | [Q1] [Q4] |
| ☐ | 91a | Brückenanker: metallische Vollkrone, je Pfeiler | GOZ 5010 | Brückenanker Vollkrone, Hohlkehl-/Stufenpräparation, je Pfeiler |  | [Q1] [Q4] |
| ☐ | 91a | Brückenanker: metallische Vollkrone, je Pfeiler | GOZ 5000 | Brückenanker Vollkrone, Tangentialpräparation, je Pfeiler |  | [Q1] [Q4] |
| ☐ | 91b | Brückenanker: Verblendkrone, je Pfeiler | GOZ 5010 | Brückenanker Vollkrone, Hohlkehl-/Stufenpräparation, je Pfeiler |  | [Q1] [Q4] |
| ☐ | 91d | Teleskop-/Konuskrone, je Pfeiler | GOZ 5040 | Teleskop-/Konuskrone, je Pfeiler |  | [Q1] [Q4] |

### Zuzahlung – Diagnostik

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 0030 | Heil- und Kostenplan | – | Umstritten/nicht belegt: ob für den privaten HKP beim Kassenpatienten GOZ 0030 berechnet werden darf, ließ sich nicht klären. | [Q22] [Q23] |

### Zuzahlung – Konservierend

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 2010 | Behandlung überempfindlicher Zahnflächen, je Kiefer | 10 | Kassenleistung BEMA 10 – privat nicht zusätzlich berechenbar. | [Q1] [Q3] |
| ☐ | nein | GOZ 2050 | Plastische Füllung, einflächig | 13a, 13b, 13c, 13d | Einfache plastische Füllung (einflächig) ist Kassenleistung BEMA 13 – keine Mehrkosten möglich. | [Q1] [Q15] |
| ☐ | nein | GOZ 2070 | Plastische Füllung, zweiflächig | 13a, 13b, 13c, 13d | Einfache plastische Füllung (zweiflächig) ist Kassenleistung BEMA 13 – keine Mehrkosten möglich. | [Q1] [Q15] |
| ☐ | nein | GOZ 2090 | Plastische Füllung, dreiflächig | 13a, 13b, 13c, 13d | Einfache plastische Füllung (dreiflächig) ist Kassenleistung BEMA 13 – keine Mehrkosten möglich. | [Q1] [Q15] |
| ☐ | nein | GOZ 2110 | Plastische Füllung, mehr als dreiflächig | 13a, 13b, 13c, 13d | Einfache plastische Füllung (mehr als dreiflächig) ist Kassenleistung BEMA 13 – keine Mehrkosten möglich. | [Q1] [Q15] |
| ☐ | ja | GOZ 2130 | Kontrolle/Politur einer Restauration in separater Sitzung | – | Keine BEMA-Leistung; Politur/Kontrolle in separater Sitzung privat vereinbar. | [Q13] [Q12] |
| ☐ | ja | GOZ 2180 | Plastischer Aufbau zur Aufnahme einer Krone | 13a, 13b | Mehrkosten nur für mehrschichtigen adhäsiven Aufbau (KZVB) oder im gleichartigen Zahnersatz; einfacher Aufbau ist BEMA 13a/b. | [Q10] [Q16] [Q1] |
| ☐ | nein | GOZ 2190 | Gegossener Stiftaufbau | 18b | Gegossener Stiftaufbau ist Regelversorgung BEMA 18b; GOZ 2190 nur bei andersartiger Versorgung (dann ganzer Fall nach GOZ). | [Q3] [Q16] |
| ☐ | ja | GOZ 2195 | Schraubenaufbau / Glasfaserstift | 18a | Gleichartiger Zahnersatz: adhäsiv befestigter Glasfaser-/Keramikstift privat, Kasse zahlt Festzuschuss 1.4. | [Q16] [Q24] |
| ☐ | ja | GOZ 2200 | Vollkrone, Tangentialpräparation | 20a | Gleichartiger Zahnersatz (§ 55 Abs. 4 SGB V): Krone nach GOZ, Kasse zahlt Festzuschuss; bei Implantatkrone andersartig. | [Q16] [Q24] |
| ☐ | ja | GOZ 2210 | Vollkrone, Hohlkehl-/Stufenpräparation | 20a, 20b | Gleichartiger Zahnersatz (§ 55 Abs. 4 SGB V): z. B. Vollkeramik- oder vollverblendete Krone nach GOZ, Provisorium bleibt BEMA 19. | [Q16] [Q24] |
| ☐ | ja | GOZ 2220 | Teilkrone / Veneer | 20c | Gleichartiger Zahnersatz: z. B. vollkeramische Teilkrone nach GOZ, Kasse zahlt Festzuschuss 1.2. | [Q16] [Q24] |
| ☐ | ja | GOZ 2250 | Konfektionierte Kinderkrone | – | Nur zahnfarbene/verblendete Kinderkrone privat; konfektionierte Stahlkrone ist BEMA 14. | [Q25] |

### Zuzahlung – Endodontie

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | ja | GOZ 2380 | Milchzahn-Pulpaamputation (avital) | – | Avitale Milchzahn-Amputation hat keine vergleichbare Sachleistung; privat vereinbar. | [Q6] |

### Zuzahlung – Chirurgie

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 3045 | Osteotomie, extrem verlagert/retiniert (umfangreich) | 48 | Extrem verlagerter Zahn ist beim Kassenpatienten BEMA 48; keine private Zuzahlung. | [Q3] [Q5] |
| ☐ | nein | GOZ 3050 | Blutstillung, als selbstständige Leistung | 36 | Kassenleistung BEMA 36 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3060 | Blutstillung durch Umstechen/Abbinden/Knochenbolzung | 37 | Kassenleistung BEMA 37 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |
| ☐ | nein | GOZ 3070 | Exzision Schleimhaut/Granulationsgewebe | 49 | Kassenleistung BEMA 49 – privat nicht zusätzlich berechenbar (Zuzahlungsverbot). | [Q3] [Q5] |

### Zuzahlung – Prophylaxe

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | ja | GOZ 1010 | Kontrolle des Übungserfolgs (mind. 15 min) | – | Erwachsene: keine Sachleistung, privat vereinbar; 6–17 J. nur über die IP-Häufigkeit hinaus. | [Q12] [Q13] |
| ☐ | ja | GOZ 1030 | Medikamentenschiene: lokale Anwendung, je Kiefer | – | Keine BEMA-Leistung; privat vereinbar. | [Q12] |

### Zuzahlung – PAR

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | ja | GOZ 4060 | Kontrolle/Nachreinigung nach Zahnstein/PZR, je Zahn | – | Keine BEMA-Leistung; Nachkontrolle nach PZR/Zahnsteinentfernung privat vereinbar. | [Q13] |
| ☐ | nein | GOZ 4080 | Gingivektomie / Gingivoplastik, je Parodontium | AITa, AITb | In AIT/CPT enthalten bzw. BEMA 49 – privat nicht zusätzlich berechenbar. | [Q3] |
| ☐ | ja | GOZ 4090 | Lappenoperation Frontzahn, je Parodontium | – | Nur an Zähnen außerhalb der PAR-Richtlinie auf Wunsch privat; sonst CPTa/CPTb. | [Q20] |
| ☐ | ja | GOZ 4100 | Lappenoperation Seitenzahn, je Parodontium | – | Nur an Zähnen außerhalb der PAR-Richtlinie auf Wunsch privat; sonst CPTa/CPTb. | [Q20] |
| ☐ | ja | GOZ 4110 | Auffüllen parodontaler Knochendefekte | CPTa, CPTb | Auffüllen von Knochendefekten ist keine Sachleistung; neben Kassen-CPT/AIT/WSR privat vereinbar. | [Q18] [Q20] |
| ☐ | ja | GOZ 4120 | Verlegen eines gestielten Schleimhautlappens | – | Plastische Parodontalchirurgie gehört nicht zur Kassenversorgung; privat vereinbar. | [Q19] |
| ☐ | ja | GOZ 4130 | Schleimhauttransplantat, je Transplantat | – | Plastische Parodontalchirurgie gehört nicht zur Kassenversorgung; privat vereinbar. | [Q19] |
| ☐ | ja | GOZ 4150 | Kontrolle/Nachbehandlung nach PAR-Chirurgie, je Zahn | – | Nur nach privat erbrachter PAR-Chirurgie (4090/4100/4120/4130); nach Kassen-CPT gilt BEMA 111. | [Q20] [Q19] [Q3] |

### Zuzahlung – Prothetik

| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |
|---|---|---|---|---|---|---|
| ☐ | nein | GOZ 2260 | Provisorium direkt, ohne Abformung | 19 | Provisorium bleibt auch bei gleichartigem Zahnersatz BEMA 19; GOZ nur bei andersartiger Versorgung. | [Q16] |
| ☐ | nein | GOZ 2270 | Provisorium direkt, mit Abformung | 19 | Provisorium bleibt auch bei gleichartigem Zahnersatz BEMA 19; GOZ nur bei andersartiger Versorgung. | [Q16] |
| ☐ | ja | GOZ 2320 | Wiederherstellung Krone/Verblendung | 24, 95 | Nur bei gleichartiger Wiederherstellung (Befundklasse 6) nach GOZ; sonst BEMA 24/95. | [Q16] [Q3] |
| ☐ | ja | GOZ 5000 | Brückenanker Vollkrone, Tangentialpräparation, je Pfeiler | 91a | Gleichartiger Zahnersatz: Brückenanker nach GOZ, Kasse zahlt Festzuschuss; sonst BEMA 91a. | [Q16] [Q24] |
| ☐ | ja | GOZ 5010 | Brückenanker Vollkrone, Hohlkehl-/Stufenpräparation, je Pfeiler | 91a, 91b | Gleichartiger Zahnersatz: z. B. Verblendung außerhalb des Verblendbereichs oder Vollkeramik; übrige Teile bleiben BEMA. | [Q16] [Q24] |
| ☐ | ja | GOZ 5040 | Teleskop-/Konuskrone, je Pfeiler | 91d | Gleichartiger Kombinationszahnersatz: Teleskopkronen nach GOZ, Prothese und Provisorien BEMA. | [Q16] [Q24] |
| ☐ | ja | GOZ 5070 | Brückenglied / Prothesenspanne | 92 | Gleichartiger Zahnersatz: vollkeramisches/vollverblendetes Brückenglied nach GOZ; sonst BEMA 92. | [Q16] [Q24] |
| ☐ | nein | GOZ 5170 | Anatomische Abformung mit individuellem Löffel | 98a | Individueller Löffel ist Kassenleistung BEMA 98a; GOZ 5170 nur bei andersartiger Versorgung. | [Q3] [Q16] |
| ☐ | nein | GOZ 5200 | Teilprothese mit gebogenen Klammern | 96a, 96b, 96c | Klammerprothese ist Regelversorgung BEMA 96; GOZ 5200 nur bei andersartiger Versorgung. | [Q3] [Q16] |
| ☐ | nein | GOZ 5210 | Modellgussprothese | 96a, 96b, 96c | Modellguss bleibt bei gleichartiger Versorgung BEMA (96/98g); GOZ 5210 nur im andersartigen Fall. | [Q16] [Q3] |
| ☐ | nein | GOZ 5220 | Totalprothese Oberkiefer | 97a | Totalprothese ist Regelversorgung BEMA 97a; GOZ 5220 nur bei Suprakonstruktion/andersartig. | [Q16] [Q3] |

## Quellen

- Q1: [KZBV BEMA Gesamtfassung 2026-01-01](https://www.kzbv.de/wp-content/uploads/KZBV_BEMA_2026-01-01.pdf)
- Q2: [GOÄ Anlage (gesetze-im-internet.de)](https://www.gesetze-im-internet.de/go__1982/anlage.html)
- Q3: [KZV BW: Gegenüberstellung BEMA- und GOZ-Honorare (2022)](https://www.kzvbw.de/wp-content/uploads/Gegenueberstellung-der-BEMA-GOZ-final_29-03-2022.pdf)
- Q4: [GOZ Anlage 1 (gesetze-im-internet.de)](https://www.gesetze-im-internet.de/goz_1987/anlage_1.html)
- Q5: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Zuzahlung zur Sachleistung (ZE-Versorgung)](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/regularien-zur-vertragszahnaerztlichen-versorgung/zuzahlung-sachleistung/ze-versorgung)
- Q6: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Endodontie, Wurzelkanalfüllung](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/endodontische-leistungen/wurzelkanalfuellung)
- Q7: [ZÄK Berlin: DVT (GOÄ 5370/5377)](https://www.zaek-berlin.de/dateien/Content/Dokumente/Zahn%C3%A4rzte/GOZ/GOZ_2012_Stellungnahmen/D/DVT.pdf)
- Q8: [GOZ § 6](https://www.gesetze-im-internet.de/goz_1987/__6.html)
- Q9: [abrechnung-dental.de (kommerziell) GOZ 0080](https://www.abrechnung-dental.de/goz/0080-intraorale-oberflaechenanaesthesie-je-kieferhaelfte-oder-frontzahnbereich)
- Q10: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Füllungsleistungen](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/fuellungsleistungen)
- Q11: [BZÄK Beratungsforum Beschluss 22: Computergesteuerte Anästhesie](https://www.bzaek.de/goz/beratungsforum/beschluss/computergesteuerte-anaesthesie.html)
- Q12: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Prophylaxe, Patienten zwischen 6 und 17 Jahren](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/prophylaxe-und-frueherkennung-von-zahnerkrankungen/patienten-zwischen--und--jahren)
- Q13: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Prophylaxe, erwachsene Patienten](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/prophylaxe-und-frueherkennung-von-zahnerkrankungen/erwachsene-patienten)
- Q14: [KZVB: Privatleistungen bei Wurzelkanalbehandlungen nach Bema](https://www.kzvb.de/fileadmin/user_upload/Abrechnung/Tipps/Privatleistungen_Wurzelkanalbehandlungen_Bema.pdf)
- Q15: [SGB V § 28](https://www.gesetze-im-internet.de/sgb_5/__28.html)
- Q16: [KZBV Festzuschuss-Kompendium 2025](https://www.kzbv.de/wp-content/uploads/KZBV_FZ-Kompendium_2025-01-01_2.pdf)
- Q17: [ZÄK Berlin: GOZ-Frage des Monats (NiTi-Feilen)](https://www.zaek-berlin.de/presse/meldungen/meldungen-detail/article/goz-frage-des-monats-24.html)
- Q18: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Auffüllen parodontaler Knochendefekte (GBR/GTR)](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/chirurgische-leistungen-knochenmanagement/auffuellen-parodontaler-knochendefekte-gbr-bzw-gtr)
- Q19: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Plastische Parodontalchirurgie](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/parodontologische-leistungen/plastische-parodontalchirurgie)
- Q20: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Systematische PAR-Behandlungsstrecke](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/parodontologische-leistungen/systematische-parbehandlungsstrecke)
- Q21: [abrechnung-dental.de (kommerziell) GOZ 4050](https://www.abrechnung-dental.de/goz/4050-entfernung-harter-und-weicher-zahnbelaege-einwurzeliger-zahn-implantate-brueckenglieder)
- Q22: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Privatbehandlung von GKV-Versicherten](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/regularien-zur-vertragszahnaerztlichen-versorgung/privatbeh-gkv)
- Q23: [GOZ § 2](https://www.gesetze-im-internet.de/goz_1987/__2.html)
- Q24: [SGB V § 55](https://www.gesetze-im-internet.de/sgb_5/__55.html)
- Q25: [KZVB Abrechnungsmappe, Schnittstellen Bema/GOZ: Kinderkronen in der pädiatrischen Zahnheilkunde](https://abrechnungsmappe.kzvb.de/leistungskataloge/schnittstellen-bema-und-goz/kinderkronen-in-der-paediatrischen-zahnheilkunde)
