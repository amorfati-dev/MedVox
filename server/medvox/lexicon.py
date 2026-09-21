"""Curated German dental lexicon with fuzzy correction of Whisper output (WP-6).

``correct(text)`` fixes tokens that are within a small Levenshtein distance of
a lexicon term ("Artikein" -> "Artikain") and known mishearings ("Psycho" ->
"PSI", "bis Registrat" -> "Bissregistrat"). Common German words are never
corrected, codes and numbers are never touched, and every correction is
returned so the UI can show it. Runs before ``normalize``. Pure, no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Correction:
    original: str
    corrected: str
    start: int  # character offsets into the input text
    end: int


# Terms in their canonical spelling (seeded from the report's test set and error
# list). Tokens equal to a term, ignoring case, are never changed.
TERMS: tuple[str, ...] = (
    # Anästhesie
    "Artikain", "Lidocain", "Mepivacain", "Infiltrationsanästhesie", "Leitungsanästhesie",
    "Lokalanästhesie", "Oberflächenanästhesie", "Anästhesie", "intraligamentär",
    # Diagnostik
    "Untersuchung", "Befund", "Vitalitätsprüfung", "Kältetest", "Perkussion", "Perkussionstest",
    "Palpation", "Sondierung", "Sondierungstiefe", "Sondierungstiefen", "Zahnfilm", "Röntgen", "OPG",
    "OPT", "Orthopantomogramm", "Bissflügel", "PSI", "Sextant", "Sextanten", "BOP", "Lockerungsgrad",
    "Furkation",
    # Befunde
    "Karies", "profunda", "media", "Sekundärkaries", "Pulpitis", "Parodontitis", "Gingivitis",
    "Perikoronitis", "Nekrose", "Fistel", "Abszess", "Zyste", "Längsfraktur", "Fraktur", "retiniert",
    "verlagert", "Attrition", "Erosion", "Dentin", "Schmelz", "Pulpa", "apikal", "Aufbissbeschwerden",
    "Hypersensibilität",
    # Füllung
    "Füllung", "Kompositfüllung", "Komposit", "Amalgam", "Amalgamfüllung", "Adhäsivtechnik", "Adhäsiv",
    "Bonding", "Ätzung", "Phosphorsäure", "Glasionomerzement", "Unterfüllung", "Aufbaufüllung", "Matrize",
    "Kofferdam", "einflächig", "zweiflächig", "dreiflächig", "mehrflächig", "Politur", "Okklusion",
    "Kontaktpunkt", "Fissurenversiegelung", "Versiegelung",
    # Endo
    "Trepanation", "Vitalexstirpation", "Wurzelkanalaufbereitung", "Wurzelkanalbehandlung", "Wurzelkanal",
    "Wurzelkanäle", "Kanal", "Kanäle", "elektrometrische", "Längenbestimmung", "medikamentöse", "Einlage",
    "Kalziumhydroxid", "Wurzelfüllung", "Guttapercha", "provisorisch", "provisorischer", "Verschluss",
    "Wurzelspitzenresektion", "Revision",
    # Chirurgie
    "Extraktion", "Osteotomie", "Wundversorgung", "Naht", "Nahtentfernung", "Wundkontrolle", "Nachkontrolle",
    "Inzision", "Drainage", "Alveole", "Alveolitis", "mehrwurzelig", "einwurzelig", "Oralchirurg",
    "Oralchirurgen", "Überweisung", "Aufklärung", "Indikation", "Implantat", "Implantation",
    # Prothetik
    "Präparation", "Stufenpräparation", "Vollkeramikkrone", "Krone", "Kronen", "Teilkrone", "Brücke", "Veneer",
    "Inlay", "Onlay", "Abformung", "Polyether", "Silikon", "Alginat", "Bissregistrat", "Bissnahme",
    "Provisorium", "Kunststoff", "eingegliedert", "Eingliederung", "Farbnahme", "Zementierung", "Zement",
    "Stiftaufbau", "Prothese", "Unterfütterung",
    # Paro / Prophylaxe
    "Zahnreinigung", "Beläge", "Zahnstein", "Fluoridierung", "Elmex", "Mundhygieneinstruktion", "Mundhygiene",
    "Kürettage", "UPT", "PZR", "antiinfektiöse", "Therapie", "Chlorhexidin", "Spülung", "Stadium", "Grad",
    "Blutung", "Milchzahn", "Milchzähne", "IP",
    # Medikation / Verwaltung
    "Ibuprofen", "Amoxicillin", "Clindamycin", "Paracetamol", "Wiedervorlage", "verordnet", "Rezept",
    # Flächen und Lage
    "mesial", "distal", "okklusal", "bukkal", "vestibulär", "lingual", "palatinal", "inzisal", "zervikal",
    "approximal", "MOD", "Oberkiefer", "Unterkiefer", "Quadrant", "Quadranten", "Molar", "Molaren",
    "Prämolar", "Prämolaren", "Frontzahn", "Eckzahn", "Schneidezahn", "Weisheitszahn",
    # Abrechnung, Sonstiges
    "BEMA", "GOZ", "Zusatzleistung", "Ziffer", "Schienung", "Aufbissschiene", "Knirscherschiene",
    "Kieferorthopädie",
)

# Known mishearings that are too far for the distance rule (lower-cased token
# windows of one or two words -> replacement).
ALIASES: dict[tuple[str, ...], str] = {
    ("psycho",): "PSI", ("goetz",): "GOZ", ("götz",): "GOZ", ("gotz",): "GOZ",
    ("bis", "registrat"): "Bissregistrat", ("biss", "registrat"): "Bissregistrat",
    ("composite",): "Komposit", ("kofferdamm",): "Kofferdam", ("caries",): "Karies",
    ("occlusal",): "okklusal", ("preparation",): "Präparation", ("perichoronitis",): "Perikoronitis",
    ("kalzium", "hydroxid"): "Kalziumhydroxid", ("gutta", "percha"): "Guttapercha",
}

# Common German words that must never be "corrected" into a term.
NEVER_CORRECT: frozenset[str] = frozenset("""
der die das den dem des ein eine einer einem einen und oder mit ohne bei in im am an auf aus für von vom
zu zum zur nach vor über unter bis seit wegen durch gegen um als wie ist sind war waren wird werden wurde
wurden hat haben hatte kann können soll sollen muss nicht kein keine noch schon dann danach vorher jetzt
heute morgen gestern sowie bzw ca etwa rechts links oben unten alt alte alter alten neu neue neuen
Zahn Zähne Zahnes Tag Tage Tagen Woche Wochen Monat Monate Monaten Jahr Jahre Jahren Stunde Stunden Minute
Minuten Kind Kinder Patient Patientin gelegt entfernt angefertigt erfolgt positiv negativ geplant planen
jeweils beide beiden alle alles nichts etwas mehr weniger wieder erneut später dabei damit dazu hier dort
Nacht nahe nah Teil Zeit Sitzung Termin Woche Moment Belege grau medial digital Abbau OP OK UK PA PS
null eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf zwanzig dreißig hundert tausend
erste ersten zweite zweiten dritte dritten vierte vierten fünften sechsten einmal zweimal dreimal
Karte Kasse privat Code Nummer Ziffern Stück Seite Seiten oben unten hinten vorne mittig komplett
""".split())

_FOLDS = (("chs", "x"), ("ck", "k"), ("ph", "f"), ("th", "t"), ("ß", "ss"))


def _fold(word: str) -> str:
    """Lower-case with German spellings that Whisper swaps merged ("Sechstant" ~ "Sextant")."""
    word = word.lower()
    for old, new in _FOLDS:
        word = word.replace(old, new)
    return word


_TERMS_LOWER: dict[str, str] = {t.lower(): t for t in TERMS}
_TERMS_FOLDED: dict[str, str] = {_fold(t): t for t in TERMS}
_NEVER_LOWER = frozenset(w.lower() for w in NEVER_CORRECT)
_INFLECTIONS = ("e", "en", "er", "es", "em", "n", "s")
_TOKEN = re.compile(r"\w+")
_L_CODE = re.compile(r"^[Ll](\d{3}[a-z]?)$")  # "L935d" -> "Ä935d" (Whisper drops the umlaut)


def levenshtein(a: str, b: str, limit: int) -> int:
    """Edit distance, capped at ``limit + 1`` for speed."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def _max_distance(token: str) -> int:
    """Short tokens get little slack; 3-letter tokens only when written as an abbreviation."""
    if len(token) <= 3:
        return 1 if token.isupper() else 0
    return 1 if len(token) <= 5 else 2


def _is_inflection(low: str, term_low: str) -> bool:
    return low.startswith(term_low) and low[len(term_low):] in _INFLECTIONS


def correct_token(token: str) -> str | None:
    """Canonical spelling for a single misheard token, or None to leave it alone."""
    low = token.lower()
    if low in _NEVER_LOWER or low in _TERMS_LOWER:
        return None
    if m := _L_CODE.match(token):
        return "Ä" + m.group(1)
    if any(ch.isdigit() for ch in token):
        return None
    limit = _max_distance(token)
    if limit == 0 or any(_is_inflection(low, t) for t in _TERMS_LOWER):
        return None
    folded = _fold(token)
    best, best_distance, ambiguous = None, limit + 1, False
    for term_folded, term in _TERMS_FOLDED.items():
        d = levenshtein(folded, term_folded, limit)
        if d > limit or (d == 2 and folded[0] != term_folded[0]):
            continue
        if d < best_distance:
            best, best_distance, ambiguous = term, d, False
        elif d == best_distance:
            ambiguous = True
    return None if ambiguous else best


def correct(text: str) -> tuple[str, list[Correction]]:
    """Return the corrected text and every correction applied (offsets refer to ``text``)."""
    tokens = [(m.start(), m.end(), m.group()) for m in _TOKEN.finditer(text)]
    corrections: list[Correction] = []
    i = 0
    while i < len(tokens):
        for width in (2, 1):
            window = tokens[i : i + width]
            key = tuple(t[2].lower() for t in window)
            if len(window) == width and key in ALIASES:
                start, end = window[0][0], window[-1][1]
                corrections.append(Correction(text[start:end], ALIASES[key], start, end))
                i += width
                break
        else:
            start, end, token = tokens[i]
            if (replacement := correct_token(token)) is not None:
                corrections.append(Correction(token, replacement, start, end))
            i += 1
    pieces, last = [], 0
    for c in corrections:
        pieces += [text[last : c.start], c.corrected]
        last = c.end
    pieces.append(text[last:])
    return "".join(pieces), corrections
