"""WP-8 Abnahme: die zwölf Diktate aus Anhang B des Planungsberichts.

``EXPECTED`` ist die fachlich richtige Abrechnung, beschränkt auf Katalog v1 (Ziffer -> Anzahl,
nur erbrachte Hauptvorschläge; Privat-Alternativen zählen nicht). ``KNOWN`` hält fest, wo die
Regeln davon abweichen – jede Abweichung steht auch unter „Bekannte Grenzen“ in server/README.md.
Precision/Recall werden auf Ziffernebene je Diktat gezählt und hier festgeschrieben.
"""

from __future__ import annotations

from collections import Counter

import pytest

from medvox.extract import Extraction, analyze, billable_codes
from medvox.lexicon import correct
from medvox.normalize import normalize

DICTATIONS = {
    "d01": ("Zahn drei sechs mesial okklusal distal Karies profunda, Infiltrationsanästhesie mit Artikain, "
            "Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt."),
    "d02": ("Eingehende Untersuchung, PSI Code drei im zweiten und dritten Sextanten, Vitalitätsprüfung an "
            "eins sechs positiv, Zahnfilm eins sechs angefertigt."),
    "d03": ("Extraktion vier sieben wegen Längsfraktur, Leitungsanästhesie, Zahn mehrwurzelig, Wundversorgung "
            "mit Naht, Nachkontrolle in einer Woche."),
    "d04": ("Zwei fünf Pulpitis, Trepanation, Vitalexstirpation, Wurzelkanalaufbereitung ein Kanal, "
            "elektrometrische Längenbestimmung, medikamentöse Einlage mit Kalziumhydroxid, provisorischer Verschluss."),
    "d05": ("Professionelle Zahnreinigung, achtundzwanzig Zähne, Entfernung harter und weicher Beläge, Politur, "
            "lokale Fluoridierung mit Elmex Gelee, Mundhygieneinstruktion."),
    "d06": ("Eins vier distal okklusal Sekundärkaries unter alter Amalgamfüllung, Amalgam entfernt, Unterfüllung "
            "mit Glasionomerzement, Kompositfüllung MOD, dreiflächig, GOZ zwei eins null null als Zusatzleistung."),
    "d07": ("Präparation zwei sechs für Vollkeramikkrone, Stufenpräparation, Abformung mit Polyether, "
            "Bissregistrat, Provisorium aus Kunststoff eingegliedert, Farbnahme A drei."),
    "d08": ("Kind acht Jahre, Fissurenversiegelung eins sechs, zwei sechs, drei sechs und vier sechs, IP fünf, "
            "vorher Reinigung und Ätzung mit Phosphorsäure."),
    "d09": ("OPG angefertigt, drei acht retiniert und verlagert, Indikation zur Osteotomie, Aufklärung über "
            "Risiken erfolgt, Überweisung zum Oralchirurgen, BEMA Ziffer Ä neun drei fünf d."),
    "d10": ("Parodontitis Stadium drei Grad B, antiinfektiöse Therapie geschlossen, Kürettage eins sieben bis "
            "zwei sieben, Sondierungstiefen bis sechs Millimeter, Blutung auf Sondierung positiv, UPT in drei Monaten."),
    "d11": ("Drei sechs, drei sieben okklusal Karies, Füllungen mit Komposit, jeweils einflächig, BEMA dreizehn a "
            "zweimal, Zusatzleistung GOZ zwei null sechs null."),
    "d12": ("Vier acht Perikoronitis, Spülung mit Chlorhexidin, Einlage, Ibuprofen sechshundert verordnet, "
            "Wiedervorlage in zwei Tagen, danach Extraktion vier acht planen."),
}

EXPECTED: dict[str, dict[str, int]] = {
    "d01": {"13c": 1, "25": 1, "40": 1, "12": 1},
    "d02": {"01": 1, "04": 1, "8": 1, "Ä925a": 1},
    "d03": {"45": 1, "41a": 1},  # X3 wegen Längsfraktur (Katalog-Keyword), Behandler bestätigt oder wählt 44
    "d04": {"28": 1, "32": 1, "34": 1},  # 31 in 28, 11 in 34 enthalten
    "d05": {"1040": 28},
    "d06": {"13c": 1, "2100": 1},
    "d07": {},  # Prothetik steht nur im erweiterten Katalog, der nicht geladen wird
    "d08": {"IP5": 4},
    "d09": {"Ä935d": 1, "Ä1": 1},  # Osteotomie nur indiziert -> geplant
    "d10": {"AITa": 8, "AITb": 6},
    "d11": {"13a": 2, "2060": 2},
    "d12": {"105": 1},  # Extraktion nur geplant
}
EXPECTED_PLANNED = {"d09": [("48", (38,))], "d12": [("44", (48,))]}

# Abweichungen der Regeln: (zusätzlich vorgeschlagen, nicht erkannt)
KNOWN: dict[str, tuple[set[str], set[str]]] = {
    "d05": ({"IP4", "MHU"}, set()),  # Keywords "fluoridierung"/"mundhygieneinstruktion" ohne Alters-/PAR-Kontext
    "d12": (set(), {"105"}),  # "Spülung mit Chlorhexidin" trifft das Keyword "chlorhexidin spülung" nicht
}


def run(dictation: str) -> Extraction:
    corrected, _ = correct(dictation)
    n = normalize(corrected)
    return analyze(n.text, n.teeth)


def billed(result: Extraction) -> Counter[str]:
    counts: Counter[str] = Counter()
    for s in result.suggestions:
        if not s.planned and not s.alternative:
            counts[s.code] += s.count
    return counts


@pytest.mark.parametrize("key", sorted(DICTATIONS))
def test_dictation(key):
    result = run(DICTATIONS[key])
    extra, missing = KNOWN.get(key, (set(), set()))
    expected = {code: n for code, n in EXPECTED[key].items() if code not in missing}
    got = billed(result)
    assert {code: n for code, n in got.items() if code not in extra} == expected
    assert set(got) & extra == extra
    planned = [(s.code, s.teeth) for s in result.suggestions if s.planned]
    assert planned == EXPECTED_PLANNED.get(key, [])
    assert all(s.reason for s in result.suggestions)


def test_precision_and_recall():
    tp = fp = fn = 0
    for key, dictation in DICTATIONS.items():
        got, want = set(billed(run(dictation))), set(EXPECTED[key])
        tp, fp, fn = tp + len(got & want), fp + len(got - want), fn + len(want - got)
    assert (tp, fp, fn) == (23, 2, 1)
    assert round(tp / (tp + fp), 3) == 0.92  # Precision
    assert round(tp / (tp + fn), 3) == 0.958  # Recall


@pytest.mark.parametrize(("whisper", "key"), [
    ("Zahn 36 mesial okklusal, Distal, Karies profunda, Infiltrationsanästhesie mit Artikein, "
     "Kompositfüllung in Adhäsivtechnik, Dreiflächig, Kofferdarm gelegt.", "d01"),
    ("36, 37 okklusal, Karies, Füllungen mit Komposit, jeweils einflächig, BEMA 13A zweimal, "
     "Zusatzleistung GOZ 2060.", "d11"),
    ("36-37 Occlusal Caries, Füllungen mit Composite, jeweils einflächig, BEMA 13a 2x, "
     "Zusatzleistung Goetz 2060.", "d11"),
])
def test_whisper_output_gives_same_codes(whisper, key):
    """Anhang C: echte whisper-Ausgaben ergeben nach Lexikon und Normalisierer dieselben Ziffern."""
    assert billed(run(whisper)) == Counter(EXPECTED[key])


def test_copy_format():
    assert billable_codes(run(DICTATIONS["d08"]).suggestions) == ["4x IP5"]
    assert billable_codes(run(DICTATIONS["d01"]).suggestions) == ["13c", "25", "40", "12"]
