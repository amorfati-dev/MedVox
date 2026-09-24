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
     "Vital", "Sprung", "Sprünge", "denken", "viral", "virale", "alveolaris", "lingualis", "buccalis",
     "palatinus", "mandibularis", "maxillaris", "mentalis", "infraorbitalis", "Nervus", "inferior",
     "SBI", "PBI", "API"],
)
def test_common_words_and_inflections_are_never_corrected(token):
    assert correct_token(token) is None


def test_common_german_words_are_never_guessed_at():
    raw = "Blutung stillt schnell, schwere Parodontitis, Medikament verordnet, Sulcus gingivalis"
    assert correct(raw) == (raw, [])


def test_anatomical_phrases_keep_their_meaning():
    raw = "Leitungsanästhesie am Nervus alveolaris inferior, Nervus lingualis geschont, SBI 20 Prozent"
    assert correct(raw) == (raw, [])


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


def test_bleeding_terms_are_kept():
    raw = ("Blutung auf Sondierung positiv, BOP 30 Prozent, 36 blutet, keine Nachblutung, "
           "Blutungsneigung bekannt, Sickerblutung gestillt, Blutungen, bluten, Blut")
    assert correct(raw) == (raw, [])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Bludung auf Sondierung", "Blutung auf Sondierung"),
        ("Nachbludung", "Nachblutung"),
        ("Sickerbludung", "Sickerblutung"),
        ("Blutungsneigunk", "Blutungsneigung"),
    ],
)
def test_bleeding_mishearings_are_corrected(raw, expected):
    assert correct(raw)[0] == expected


@pytest.mark.parametrize("raw, expected", [
    ("PTE 3x, WK", "VitE 3x, WK"),
    ("PTE mal drei", "VitE mal drei"),
    ("PTE*3", "VitE*3"),
    ("PTE dreimal", "VitE dreimal"),
])
def test_pte_is_vite_only_before_a_count(raw, expected):
    assert correct(raw)[0] == expected


@pytest.mark.parametrize("short", ["PTE", "WD"])
@pytest.mark.parametrize("raw, expected", [
    ("2x {}, 2x WK", "2x VitE, 2x WK"), ("{} 2x", "VitE 2x"), ("{} mal zwei", "VitE mal zwei"),
    ("zweimal {}", "zweimal VitE"), ("2 mal {}", "2 mal VitE"), ("{}*2", "VitE*2"),
])
def test_vite_mishearing_with_count_on_either_side(short, raw, expected):
    assert correct(raw.format(short))[0] == expected


@pytest.mark.parametrize("raw", ["PTE", "PTE besprochen", "Zahn 46 PTE, WK mal drei", "PTE 36",
                                 "WD", "WD besprochen", "Zahn 46 WD, WK mal drei", "WD 36", "2 WD", "Zahn 25 WD"])
def test_pte_elsewhere_is_left_alone(raw):
    assert correct(raw) == (raw, [])


@pytest.mark.parametrize("raw, expected", [
    ("Röntgen zwei, WK", "Rö2, WK"), ("Rö zwei.", "Rö2."), ("Röntgen 2", "Rö2"), ("Röntgen fünf", "Rö5"),
    ("Röntgen zwei sechs", "Röntgen zwei sechs"),  # Zahn 26, keine Kurzform
    ("Röntgen 2 6", "Röntgen 2 6"),
])
def test_spoken_xray_short_form(raw, expected):
    assert correct(raw)[0] == expected


@pytest.mark.parametrize("raw", ["Röntgen, zwei Kanäle aufbereitet.", "Röntgen. Zwei Kanäle aufbereitet.",
                                 "Füllung 2, flächig", "Gutta. Percha", "bis, Registrat"])
def test_word_windows_never_span_punctuation(raw):
    assert correct(raw) == (raw, [])


@pytest.mark.parametrize("raw, expected", [
    ("2 flächig", "zweiflächig"), ("3-flächig", "dreiflächig"), ("4flächig", "vierflächig"),
    ("zwei flächig", "zweiflächig"), ("1 flächig", "einflächig"),
])
def test_surface_count_as_digit_becomes_the_word(raw, expected):
    assert correct(f"Füllung {raw}")[0] == f"Füllung {expected}"


def test_captains_spellings_of_endo_words():
    assert correct_token("Vitalextirpation") == "Vitalexstirpation"
    assert correct_token("längenbestimungen") == "Längenbestimmungen"


@pytest.mark.parametrize("raw, expected", [
    ("Zahn 25 Wurzelkanalbehandlung beginnen, 2x WD, 2x WK, MET, Zahn 46 Füllung",
     "Zahn 25 Wurzelkanalbehandlung beginnen, 2x VitE, 2x WK, med, Zahn 46 Füllung"),
    ("Zahn drei sechs MET, WK mal drei", "Zahn drei sechs med, WK mal drei"),
    ("Trepanation, MET, Verschluss", "Trepanation, med, Verschluss"),
])
def test_met_is_med_next_to_a_root_canal_treatment(raw, expected):
    assert correct(raw)[0] == expected


@pytest.mark.parametrize("raw", [
    "MET", "Zahn 36 Füllung, MET", "Zahn 25 WK mal drei, Zahn 46 MOD, MET",
    "Zahn 46 MET, Zahn 25 Wurzelkanalbehandlung", "36 WK 2x, 46 MET", "Zahn 25 2 WD, MET",
])
def test_met_elsewhere_is_left_alone(raw):
    assert correct(raw) == (raw, [])


@pytest.mark.parametrize("raw, expected", [
    ("Bisflügel", "Bissflügel"), ("Bisflügelaufnahme rechts", "Bissflügelaufnahme rechts"),
    ("Bisflügelaufnahmen", "Bissflügelaufnahmen"),
])
def test_bitewing_with_one_s(raw, expected):
    assert correct(raw)[0] == expected
