"""WP-6: Dental-Lexikon und Fuzzy-Korrektur, Fälle aus der Fehlerliste des Reports (7.3) und Anhang C."""

import pytest

from medvox.lexicon import ALIASES, TERMS, Correction, correct, correct_token, levenshtein


@pytest.mark.parametrize(
    "token, expected",
    [
        ("Artikein", "Artikain"),
        ("Kofferdarm", "Kofferdam"),
        ("Kofferdamm", "Kofferdam"),
        ("Sechstanten", "Sextanten"),
        ("Polyeter", "Polyether"),
        ("Perichoronitis", "Perikoronitis"),
        ("MOT", "MOD"),
        ("COZ", "GOZ"),
        ("L935d", "Ä935d"),
        ("Occlusal", "okklusal"),
        ("Caries", "Karies"),
        ("Adhesivtechnik", "Adhäsivtechnik"),
        ("Kürrettage", "Kürettage"),
        ("Trepanazion", "Trepanation"),
        ("Fissurenversieglung", "Fissurenversiegelung"),
        ("Glasionomerzemnt", "Glasionomerzement"),
        ("Vitalexstirpazion", "Vitalexstirpation"),
        ("Osteotomi", "Osteotomie"),
        ("Vitall", "vital"),
        ("avitel", "avital"),
        ("Sondierungstiefe", None),
        ("Artikain", None),
        ("okklusal", None),
        ("Distal", None),  # nur die Schreibung unterscheidet sich: keine Korrektur
    ],
)
def test_correct_token(token, expected):
    assert correct_token(token) == expected


@pytest.mark.parametrize(
    "token",
    ["in", "am", "mit", "hat", "Zahn", "Zähne", "Nacht", "Teil", "medial", "digital", "Moment", "OP",
     "gelegt", "Kronen", "Zysten", "Füllungen", "Mode", "Karin", "bis", "sechs",
     "kariös", "kariöse", "Schmerz", "Schmerzen", "Faktor", "Funktion", "fester", "festen", "belegt", "GOÄ",
     "Grat", "Matrix", "Frontzähne", "Eckzähne", "Schneidezähne", "Weisheitszähne", "Provisorien",
     "elektrometrisch", "medikamentös", "antiinfektiös", "paar", "Part", "GIZ", "avital", "PBI",
     "Kieferorthopäden", "Kanüle", "Kürette", "spülen", "füllen", "versiegeln", "eingliedern", "abformen",
     "fluoridieren", "aufklären", "sondieren", "überweisen", "verordnen", "planen", "Schienen", "vital",
     "Vital", "Sprung", "Sprünge", "denken", "viral", "virale"],
)
def test_common_words_and_inflections_are_never_corrected(token):
    assert correct_token(token) is None


def test_par_is_not_rewritten_to_pzr():
    raw = "PAR-Status erhoben, PAR-Behandlung geplant"
    assert correct(raw) == (raw, [])


def test_common_dental_sentence_is_not_rewritten():
    raw = "Zahn 36 kariös, fester Sitz der Prothese, GOZ 2100 Faktor 2,3, Schmerz bei Perkussion"
    assert correct(raw) == (raw, [])


@pytest.mark.parametrize("token", ["36", "13a", "2100", "2x", "Ä935d", "3,6", "2060"])
def test_codes_and_numbers_are_never_touched(token):
    text, corrections = correct(f"Zahn {token} okklusal")
    assert text == f"Zahn {token} okklusal"
    assert corrections == []


def test_common_phrases_pass_through_the_fuzzy_path_unchanged():
    raw = "Kontrolle in ein paar Tagen, Zahn 36 vital, Sprung mesial, mit CHX spülen, Unterfüllung mit GIZ"
    assert correct(raw) == (raw, [])


def test_terms_are_unique_ignoring_case():
    lowered = [t.lower() for t in TERMS]
    assert len(lowered) == len(set(lowered))


def test_ambiguous_match_is_skipped():
    # "Anlay" ist je eine Änderung von "Inlay" und "Onlay" entfernt
    assert correct_token("Anlay") is None


def test_multi_word_aliases():
    text, corrections = correct("Abformung mit Polyether, bis Registrat, Provisorium")
    assert text == "Abformung mit Polyether, Bissregistrat, Provisorium"
    assert corrections == [Correction("bis Registrat", "Bissregistrat", 25, 38)]
    assert ("bis", "registrat") in ALIASES


def test_psycho_3_becomes_psi_3():
    text, corrections = correct("Psycho 3 im zweiten und dritten Sechstanten")
    assert text == "PSI 3 im zweiten und dritten Sextanten"
    assert [(c.original, c.corrected) for c in corrections] == [("Psycho", "PSI"), ("Sechstanten", "Sextanten")]


def test_d01_whisper_en_output():
    raw = ("Zahn 3-6 Mesial Occlusal Distal Caries Profunda, Infiltrationsanästhesie mit Artikein, "
           "Kompositfüllung in Adhesivtechnik, dreiflächig, Kofferdarm gelegt.")
    text, corrections = correct(raw)
    assert text == ("Zahn 3-6 Mesial okklusal Distal Karies Profunda, Infiltrationsanästhesie mit Artikain, "
                    "Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt.")
    assert [(c.original, c.corrected) for c in corrections] == [
        ("Occlusal", "okklusal"), ("Caries", "Karies"), ("Artikein", "Artikain"),
        ("Adhesivtechnik", "Adhäsivtechnik"), ("Kofferdarm", "Kofferdam"),
    ]


def test_d01_whisper_de_prompt_output():
    raw = ("Zahn 36 mesial okklusal, Distal, Karies profunda, Infiltrationsanästhesie mit Artikein, "
           "Kompositfüllung in Adhäsivtechnik, Dreiflächig, Kofferdarm gelegt.")
    text, corrections = correct(raw)
    assert [(c.original, c.corrected) for c in corrections] == [("Artikein", "Artikain"), ("Kofferdarm", "Kofferdam")]
    assert "Artikain" in text and "Kofferdam gelegt" in text


def test_d11_whisper_en_output():
    raw = ("36-37 Occlusal Caries, Füllungen mit Composite, jeweils einflächig, BEMA 13a 2x, "
           "Zusatzleistung Goetz 2060.")
    text, corrections = correct(raw)
    assert text == ("36-37 okklusal Karies, Füllungen mit Komposit, jeweils einflächig, BEMA 13a 2x, "
                    "Zusatzleistung GOZ 2060.")
    assert [c.corrected for c in corrections] == ["okklusal", "Karies", "Komposit", "GOZ"]


def test_clean_dictation_is_unchanged():
    raw = ("Zwei fünf Pulpitis, Trepanation, Vitalexstirpation, Wurzelkanalaufbereitung ein Kanal, "
           "elektrometrische Längenbestimmung, medikamentöse Einlage mit Kalziumhydroxid, provisorischer Verschluss.")
    assert correct(raw) == (raw, [])


def test_correction_offsets_point_into_the_input():
    raw = "Spülung, Kofferdarm gelegt"
    text, (c,) = correct(raw)
    assert raw[c.start : c.end] == "Kofferdarm"
    assert text == "Spülung, Kofferdam gelegt"


def test_l_code_alias_only_for_three_digit_codes():
    assert correct_token("L935d") == "Ä935d"
    assert correct_token("L1") is None
    assert correct("Ä935d")[1] == []


@pytest.mark.parametrize(
    "a, b, limit, expected",
    [("artikein", "artikain", 2, 1), ("kofferdarm", "kofferdam", 2, 1), ("mot", "mod", 1, 1),
     ("abc", "abc", 2, 0), ("abc", "xyz", 2, 3), ("kurz", "sehrlang", 2, 3)],
)
def test_levenshtein(a, b, limit, expected):
    assert levenshtein(a, b, limit) == expected


def test_empty_text():
    assert correct("") == ("", [])
