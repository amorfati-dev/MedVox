"""WP-5: Normalisierer-Fälle aus dem Testset des Reports (Anhang B) und den rohen whisper.cpp-Ausgaben (Anhang C)."""

import pytest

from medvox.normalize import ToothRef, normalize, number_value


def teeth(text: str) -> list[int]:
    return [t.fdi for t in normalize(text).teeth]


# --- gesprochene Ziffernpaare und Whisper-Schreibweisen -------------------------

@pytest.mark.parametrize(
    "raw, expected_text, expected_teeth",
    [
        ("Zahn drei sechs Karies", "Zahn 36 Karies", [36]),
        ("Zahn 36 Karies", "Zahn 36 Karies", [36]),
        ("Zahn 3,6 Karies", "Zahn 36 Karies", [36]),
        ("Zahn 3-6 Karies", "Zahn 36 Karies", [36]),
        ("Zahn 3 6 Karies", "Zahn 36 Karies", [36]),
        ("Extraktion 4-7 wegen Längsfraktur", "Extraktion 47 wegen Längsfraktur", [47]),
        ("Vitalitätsprüfung an 1,6 positiv", "Vitalitätsprüfung an 16 positiv", [16]),
        ("Zwei fünf Pulpitis, Trepanation", "25 Pulpitis, Trepanation", [25]),
        ("Präparation zwei sechs für Vollkeramikkrone", "Präparation 26 für Vollkeramikkrone", [26]),
        ("drei acht retiniert und verlagert", "38 retiniert und verlagert", [38]),
        ("Vier acht Perikoronitis", "48 Perikoronitis", [48]),
        ("Milchzahn fünf fünf kariös", "Milchzahn 55 kariös", [55]),
        ("GOZ zwei null acht null zwei sechs", "GOZ 2080 26", [26]),
        ("GOZ 2100 Faktor 2,3, 1, 6", "GOZ 2100 Faktor 2,3, 1, 6", []),
        ("Zahn drei sechs, drei Kanäle aufbereitet", "Zahn 36, 3 Kanäle aufbereitet", [36]),
        ("Kompositfüllung eins vier, drei Flächen", "Kompositfüllung 14, 3 Flächen", [14]),
        ("Rezession an drei sechs, zwei Millimeter", "Rezession an 36, 2 Millimeter", [36]),
        ("Regio 36 Implantat inseriert", "Regio 36 Implantat inseriert", [36]),
        ("Regio drei sechs Implantat inseriert", "Regio 36 Implantat inseriert", [36]),
        ("Zahn drei sechs Kanal aufbereitet", "Zahn 36 Kanal aufbereitet", [36]),
        ("Zahn 36 Wurzel frakturiert", "Zahn 36 Wurzel frakturiert", [36]),
        ("Zahn drei sechs Wurzel frakturiert", "Zahn 36 Wurzel frakturiert", [36]),
        ("Karies. 36 okklusal", "Karies. 36 o", [36]),
        ("Zahn 36.", "Zahn 36.", [36]),
        ("36: Karies", "36: Karies", [36]),
    ],
)
def test_single_tooth_forms(raw, expected_text, expected_teeth):
    result = normalize(raw)
    assert result.text == expected_text
    assert [t.fdi for t in result.teeth] == expected_teeth


@pytest.mark.parametrize(
    "raw, expected_text, expected_teeth",
    [
        ("Fissurenversiegelung 1 6, 2 6", "Fissurenversiegelung 16, 26", [16, 26]),
        ("Fissurenversiegelung 1, 6, 2, 6", "Fissurenversiegelung 1, 6, 2, 6", []),
        ("Sondierungstiefen 3 2 3 2 2 3", "Sondierungstiefen 3 2 3 2 2 3", []),
        ("Zahn drei sechs drei sieben Karies", "Zahn 36 37 Karies", [36, 37]),
        ("1 6 2 6", "1 6 2 6", []),
        ("Sondierungstiefen 3, 2, 3, 2, 2, 3", "Sondierungstiefen 3, 2, 3, 2, 2, 3", []),
        ("Fissurenversiegelung eins sechs, zwei sechs, drei sechs und vier sechs, IP fünf",
         "Fissurenversiegelung 16, 26, 36 und 46, IP5", [16, 26, 36, 46]),
        ("IP fünf, eins sechs, zwei sechs", "IP5, 16, 26", [16, 26]),
        ("PSI 3 3 2 2 3 3, 36 okklusal Karies", "PSI 3 3 2 2 3 3, 36 o Karies", [36]),
        ("PSI 3, 36 Karies", "PSI 3, 36 Karies", [36]),
        ("PSI 3 3 2 2 3 3 36 okklusal Karies", "PSI 3 3 2 2 3 3 36 o Karies", [36]),
        ("PSI drei drei zwei zwei drei drei drei sechs okklusal", "PSI 3 3 2 2 3 3 36 o", [36]),
        ("PSI drei, drei sechs Karies", "PSI 3, 36 Karies", [36]),
        ("drei sechs, drei sieben, zwei mesial", "36, 37, 2 m", [36, 37]),
        ("Kürettage drei sechs, drei sieben, vier Sitzungen", "Kürettage 36, 37, 4 Sitzungen", [36, 37]),
        ("Drei sechs, drei sieben okklusal Karies", "36, 37 o Karies", [36, 37]),
        ("36, 37 okklusal, Karies", "36, 37 o, Karies", [36, 37]),
        ("36-37 okklusal Karies", "36-37 o Karies", [36, 37]),
        ("Füllungen 34-37", "Füllungen 34-37", [34, 35, 36, 37]),
        ("Kürettage eins sieben bis zwei sieben", "Kürettage 17-27",
         [17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27]),
        ("Fissurenversiegelung 1626", "Fissurenversiegelung 16, 26", [16, 26]),
    ],
)
def test_tooth_lists_and_ranges(raw, expected_text, expected_teeth):
    result = normalize(raw)
    assert result.text == expected_text
    assert [t.fdi for t in result.teeth] == expected_teeth


# --- Quadrantenangaben --------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected_text, expected_teeth",
    [
        ("Oberkiefer rechts sechs Karies", "16 Karies", [16]),
        ("Oberkiefer links 6 Karies", "26 Karies", [26]),
        ("Unterkiefer links Zahn sieben", "Zahn 37", [37]),
        ("Unterkiefer rechts acht Perikoronitis", "48 Perikoronitis", [48]),
        ("erster Quadrant Zahn vier", "Zahn 14", [14]),
        ("im vierten Quadranten Zahn sieben", "Zahn 47", [47]),
        ("Zahn sechs im zweiten Quadranten", "Zahn 26", [26]),
        ("im dritten Quadranten 6 Karies", "36 Karies", [36]),
        ("Oberkiefer rechts zwei mesial Karies", "12 m Karies", [12]),
        ("im vierten Quadranten Zahn sieben extrahiert", "Zahn 47 extrahiert", [47]),
        ("Unterkiefer links Zahn sieben Wurzelkanalbehandlung", "Zahn 37 Wurzelkanalbehandlung", [37]),
        ("Oberkiefer rechts sechs extrahiert", "16 extrahiert", [16]),
        ("Oberkiefer links acht Osteotomie", "28 Osteotomie", [28]),
        ("Unterkiefer links Regio sechs Implantat gesetzt", "Regio 36 Implantat gesetzt", [36]),
        ("Oberkiefer rechts Zahn sechs Wurzel frakturiert", "Zahn 16 Wurzel frakturiert", [16]),
        ("Oberkiefer rechts an zwei Stellen Blutung", "Oberkiefer rechts an 2 Stellen Blutung", []),
        ("Unterkiefer links an drei Zähnen", "Unterkiefer links an 3 Zähnen", []),
        ("Oberkiefer rechts zwei Kronen eingegliedert", "Oberkiefer rechts 2 Kronen eingegliedert", []),
        ("im ersten Quadranten drei Extraktionen", "im ersten Quadranten 3 Extraktionen", []),
        ("Oberkiefer rechts ein Provisorium eingegliedert",
         "Oberkiefer rechts ein Provisorium eingegliedert", []),
        ("Oberkiefer rechts drei Zähne fehlen", "Oberkiefer rechts 3 Zähne fehlen", []),
        ("Unterkiefer links 2 Implantate", "Unterkiefer links 2 Implantate", []),
        ("Sondierung im ersten Quadranten", "Sondierung im ersten Quadranten", []),
    ],
)
def test_quadrant_phrases(raw, expected_text, expected_teeth):
    result = normalize(raw)
    assert result.text == expected_text
    assert [t.fdi for t in result.teeth] == expected_teeth


# --- Flächen ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected_text, expected_teeth",
    [
        ("Zahn drei sechs mesial okklusal distal Karies profunda", "Zahn 36 mod Karies profunda", [ToothRef(36, "mod")]),
        ("Zahn 36 mesial okklusal, Distal, Karies profunda", "Zahn 36 mod, Karies profunda", [ToothRef(36, "mod")]),
        ("Eins vier distal okklusal Sekundärkaries", "14 do Sekundärkaries", [ToothRef(14, "do")]),
        ("Kompositfüllung MOD, dreiflächig", "Kompositfüllung mod, dreiflächig", []),
        ("mod Füllung 46", "mod Füllung 46", [ToothRef(46, "")]),
        ("MOD 46", "mod 46", [ToothRef(46, "mod")]),
        ("Zahn 11 palatinal, 21 inzisal", "Zahn 11 p, 21 i", [ToothRef(11, "p"), ToothRef(21, "i")]),
        ("24 bukkal und 25 vestibulär, 34 lingual", "24 b und 25 b, 34 l",
         [ToothRef(24, "b"), ToothRef(25, "b"), ToothRef(34, "l")]),
        ("Karies an der distalen Fläche 16", "Karies an der d Fläche 16", [ToothRef(16, "")]),
        ("Füllung am 36 in Adhäsivtechnik, Kontrolle im Mai", "Füllung am 36 in Adhäsivtechnik, Kontrolle im Mai",
         [ToothRef(36, "")]),
        ("36 mesial und distal Karies", "36 md Karies", [ToothRef(36, "md")]),
        ("Termin Mo 36", "Termin Mo 36", [ToothRef(36, "")]),
        ("36, 37 okklusal Karies", "36, 37 o Karies", [ToothRef(36, "o"), ToothRef(37, "o")]),
    ],
)
def test_surfaces(raw, expected_text, expected_teeth):
    result = normalize(raw)
    assert result.text == expected_text
    assert result.teeth == expected_teeth


# --- Zahlwörter und Codes ---------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected_text",
    [
        ("BEMA dreizehn a zweimal", "BEMA 13a 2x"),
        ("BEMA 13A zweimal", "BEMA 13a 2x"),
        ("BEMA 13a 2x", "BEMA 13a 2x"),
        ("GOZ zwei eins null null als Zusatzleistung", "GOZ 2100 als Zusatzleistung"),
        ("GOZ zwei null sechs null", "GOZ 2060"),
        ("BEMA Ziffer Ä neun drei fünf d", "BEMA Ziffer Ä935d"),
        ("BEMA Ziffer dreizehn a", "BEMA 13a"),
        ("BEMA Nr. 13", "BEMA 13"),
        ("Ä 935 d", "Ä935d"),
        ("Ä935d", "Ä935d"),
        ("Ä eins", "Ä1"),
        ("Ä 5", "Ä5"),
        ("BEMA 13 2 mal", "BEMA 13 2 mal"),
        ("GOZ 2100 2 x", "GOZ 2100 2 x"),
        ("GOZ 2060 3 Flächen", "GOZ 2060 3 Flächen"),
        ("GOZ zwei eins null null zwei mal", "GOZ 2100 2 mal"),
        ("GOZ 2100 Faktor 2,3", "GOZ 2100 Faktor 2,3"),
        ("GOZ 2100 zum 2,3-fachen Satz", "GOZ 2100 zum 2,3-fachen Satz"),
        ("PSI 33 22 33", "PSI 33 22 33"),
        ("PSI 3 X 2 2 3 3", "PSI 3 X 2 2 3 3"),
        ("Ibuprofen sechshundert verordnet", "Ibuprofen 600 verordnet"),
        ("Amoxicillin tausend", "Amoxicillin 1000"),
        ("Professionelle Zahnreinigung, achtundzwanzig Zähne", "Professionelle Zahnreinigung, 28 Zähne"),
        ("Kind acht Jahre", "Kind 8 Jahre"),
        ("PSI Code drei im zweiten und dritten Sextanten", "PSI Code 3 im zweiten und dritten Sextanten"),
        ("Parodontitis Stadium drei Grad B", "Parodontitis Stadium 3 Grad B"),
        ("Wurzelkanalaufbereitung ein Kanal", "Wurzelkanalaufbereitung 1 Kanal"),
        ("Sondierungstiefen bis sechs Millimeter", "Sondierungstiefen bis 6 Millimeter"),
        ("UPT in drei Monaten, Wiedervorlage in zwei Tagen", "UPT in 3 Monaten, Wiedervorlage in 2 Tagen"),
        ("Farbnahme A drei", "Farbnahme A 3"),
        ("Nachkontrolle in einer Woche", "Nachkontrolle in einer Woche"),
        ("Kontrolle in ein paar Tagen", "Kontrolle in ein paar Tagen"),
        ("Ibuprofen 600 1-1-1 für 3 Tage", "Ibuprofen 600 1-1-1 für 3 Tage"),
        ("Amoxicillin 1000, 1-1-1 über 5 Tage", "Amoxicillin 1000, 1-1-1 über 5 Tage"),
        ("Sondierungstiefen 4 5 4", "Sondierungstiefen 4 5 4"),
        ("GOZ-Ziffer 4133 und BEMA-Ziffer 13a abgerechnet", "GOZ 4133 und BEMA 13a abgerechnet"),
        ("Ziffer 4133", "Ziffer 4133"),
        ("zwölf, dreizehn, einundzwanzig", "12, 13, 21"),
        ("2100", "2100"),
        ("2060", "2060"),
    ],
)
def test_number_words_and_codes(raw, expected_text):
    assert normalize(raw).text == expected_text


@pytest.mark.parametrize(
    "raw",
    [
        "GOZ 2100 als Zusatzleistung",
        "Zusatzleistung GOZ 2060",
        "GOZ 2100",
        "2100",
        "BEMA Ziffer Ä935d",
        "BEMA 13a zweimal",
        "Ibuprofen 600",
        "Nachkontrolle am 15.04.",
        "Termin 14:30 Uhr",
        "Nachkontrolle am 15.11.",
        "Termin 14:15",
        "am 15.11.2026",
        "Spülung 15-20 Minuten",
        "Kontrolle in 14-21 Tagen",
        "PSI 3 3 2 2 3 3",
        "PSI 3/3/2/2/3/3",
        "PSI Code drei drei zwei zwei drei drei",
        "PSI: 3 3 2 2 3 3",
        "GOZ 2100 Faktor 2,3",
        "GOZ 2100 zum 2,3-fachen Satz",
        "GOZ 2100 3,5-fach",
        "PSI 33 22 33",
        "PSI 3 X 2 2 3 3",
        "PSI 3 3 2, 2 3 3",
        "PSI 3 3 2, X 3 3",
        "Sondierungstiefen 3, 5, 6 mm",
        "BEMA Ziffer 13 a",
        "GOZ-Ziffer 4133",
        "Ziffer 4133",
        "IP 5",
        "Sondierungstiefe 3,5 mm",
        "in 2-3 Tagen",
        "achtundzwanzig Zähne",
        "28 Zähne",
        "Kind 12 Jahre",
        "Ibuprofen 600, 2-3 mal täglich",
        "Ibuprofen 600 1-1-1 für 3 Tage",
        "Amoxicillin 1000, 1-1-1 über 5 Tage",
        "Sondierungstiefen 4 5 4",
        "Lockerungsgrad 1 2 1",
        "Unterkiefer links 2 Implantate",
        "Oberkiefer rechts ein Implantat",
        "Stadium 3 Grad B",
    ],
)
def test_codes_and_counts_are_not_teeth(raw):
    assert teeth(raw) == []


# --- Hilfsfunktionen --------------------------------------------------------------------

@pytest.mark.parametrize(
    "word, expected",
    [("drei", (3, True)), ("null", (0, True)), ("eins", (1, True)), ("dreizehn", (13, False)),
     ("achtundzwanzig", (28, False)), ("sechshundert", (600, False)), ("zweihundertfünfzig", (250, False)),
     ("tausend", (1000, False)), ("Kanal", None), ("und", None), ("sechsten", None), ("einer", None)],
)
def test_number_value(word, expected):
    assert number_value(word) == expected


def test_whitespace_and_dashes_are_tidied():
    assert normalize("  Zahn   36 –  37   okklusal ,  Karies ").text == "Zahn 36-37 o, Karies"

