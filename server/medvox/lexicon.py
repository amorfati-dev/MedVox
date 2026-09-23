"""Kuratiertes deutsches Dental-Lexikon mit Fuzzy-Korrektur der Whisper-Ausgabe (WP-6).

``correct(text)`` korrigiert bekannte Verhörer aus ``ALIASES`` ("Psycho" ->
"PSI", "bis Registrat" -> "Bissregistrat") sowie Tokens mit Levenshtein-Distanz
1 zu einem Lexikon-Begriff ("Artikein" -> "Artikain"). Im Zweifel bleibt das
Token stehen: Distanz 2 wird nicht mehr geraten, weil das den klinischen Sinn
verändert hat ("schwere" -> "Schmerz").
Häufige deutsche Wörter werden nie korrigiert, Codes und Zahlen nie angefasst,
und jede Korrektur wird zurückgegeben, damit die UI sie anzeigen kann. Läuft
vor ``normalize``. Rein, ohne I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Correction:
    original: str
    corrected: str
    start: int  # Zeichen-Offsets im Eingabetext
    end: int


# Begriffe in kanonischer Schreibweise (aus Testset und Fehlerliste des
# Reports). Tokens, die einem Begriff bis auf Groß-/Kleinschreibung gleichen,
# werden nie verändert.
TERMS: tuple[str, ...] = (
    # Anästhesie
    "Artikain", "Lidocain", "Mepivacain", "Infiltrationsanästhesie", "Leitungsanästhesie",
    "Lokalanästhesie", "Oberflächenanästhesie", "Anästhesie", "intraligamentär",
    # Diagnostik
    "Untersuchung", "Befund", "Vitalitätsprüfung", "Kältetest", "Perkussion", "Perkussionstest",
    "Palpation", "Sondierung", "Sondierungstiefe", "Sondierungstiefen", "Zahnfilm", "Röntgen", "OPG",
    "OPT", "Orthopantomogramm", "Bissflügel", "PSI", "Sextant", "Sextanten", "BOP", "PBI", "SBI", "API", "IPR", "Lockerungsgrad",
    "Furkation", "Funktion",
    # Befunde
    "Karies", "kariös", "profunda", "media", "Sekundärkaries", "Pulpitis", "Parodontitis", "Gingivitis",
    "Perikoronitis", "Nekrose", "Fistel", "Abszess", "Zyste", "Längsfraktur", "Fraktur", "retiniert",
    "verlagert", "Attrition", "Erosion", "Dentin", "Schmelz", "Pulpa", "apikal", "vital", "avital", "Sprung", "Sprünge", "Aufbissbeschwerden",
    "Hypersensibilität", "Schmerz", "Schmerzen",
    # Füllung
    "Füllung", "Kompositfüllung", "Komposit", "Amalgam", "Amalgamfüllung", "Adhäsivtechnik", "Adhäsiv",
    "Bonding", "Ätzung", "Phosphorsäure", "Glasionomerzement", "GIZ", "Unterfüllung", "Aufbaufüllung", "Matrize", "Matrix",
    "Kofferdam", "einflächig", "zweiflächig", "dreiflächig", "mehrflächig", "Politur", "Okklusion",
    "Kontaktpunkt", "Fissurenversiegelung", "Versiegelung",
    # Endo
    "Trepanation", "Vitalexstirpation", "Wurzelkanalaufbereitung", "Wurzelkanalbehandlung", "Wurzelkanal",
    "Wurzelkanäle", "Kanal", "Kanäle", "Kanüle", "elektrometrisch", "Längenbestimmung", "medikamentös", "Einlage",
    "Kalziumhydroxid", "Wurzelfüllung", "Guttapercha", "provisorisch", "Verschluss",
    "Wurzelspitzenresektion", "Revision",
    # Chirurgie
    "Extraktion", "Osteotomie", "Wundversorgung", "Naht", "Nahtentfernung", "Wundkontrolle", "Nachkontrolle",
    "Inzision", "Drainage", "Alveole", "Alveolitis", "mehrwurzelig", "einwurzelig", "Oralchirurg",
    "Oralchirurgen", "Überweisung", "Aufklärung", "Indikation", "Implantat", "Implantation",
    # Prothetik
    "Präparation", "Stufenpräparation", "Vollkeramikkrone", "Krone", "Kronen", "Teilkrone", "Brücke", "Veneer",
    "Inlay", "Onlay", "Abformung", "Polyether", "Silikon", "Alginat", "Bissregistrat", "Bissnahme",
    "Provisorium", "Provisorien", "Kunststoff", "eingegliedert", "Eingliederung", "Farbnahme", "Zementierung", "Zement",
    "Stiftaufbau", "Prothese", "Unterfütterung",
    # Paro / Prophylaxe
    "Zahnreinigung", "Beläge", "Zahnstein", "Fluoridierung", "Elmex", "Mundhygieneinstruktion", "Mundhygiene",
    "Kürettage", "Kürette", "UPT", "PZR", "PAR", "antiinfektiös", "Therapie", "Chlorhexidin", "Spülung", "Stadium", "Grad",
    "Blutung", "blutet", "Nachblutung", "Blutungsneigung", "Sickerblutung", "Milchzahn", "Milchzähne", "IP",
    # Medikation / Verwaltung
    "Ibuprofen", "Amoxicillin", "Clindamycin", "Paracetamol", "Wiedervorlage", "verordnet", "Rezept",
    # Flächen und Lage
    "mesial", "distal", "okklusal", "bukkal", "vestibulär", "lingual", "palatinal", "inzisal", "zervikal",
    "approximal", "MOD", "Oberkiefer", "Unterkiefer", "Quadrant", "Quadranten", "Molar", "Molaren",
    "Prämolar", "Prämolaren", "Frontzahn", "Frontzähne", "Eckzahn", "Eckzähne", "Schneidezahn",
    "Schneidezähne", "Weisheitszahn", "Weisheitszähne",
    # Abrechnung, Sonstiges
    "BEMA", "GOZ", "GOÄ", "Faktor", "Zusatzleistung", "Ziffer", "Schienung", "Aufbissschiene", "Knirscherschiene",
    "Kieferorthopädie", "Kieferorthopäde",
)

# Bekannte Verhörer, die für die Distanzregel zu weit entfernt sind
# (kleingeschriebene Token-Fenster aus ein oder zwei Wörtern -> Ersatz).
ALIASES: dict[tuple[str, ...], str] = {
    ("psycho",): "PSI", ("goetz",): "GOZ", ("götz",): "GOZ",
    ("occlusal",): "okklusal", ("perichoronitis",): "Perikoronitis",
    ("bis", "registrat"): "Bissregistrat", ("biss", "registrat"): "Bissregistrat",
    ("composite",): "Komposit",
    ("kalzium", "hydroxid"): "Kalziumhydroxid", ("gutta", "percha"): "Guttapercha",
}

# Häufige deutsche Wörter, die nie zu einem Begriff "korrigiert" werden dürfen.
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
fest fester festen festes festem belegt Grat paar Part denken viral virale
Nervus alveolaris lingualis buccalis palatinus mandibularis maxillaris mentalis infraorbitalis inferior
""".split())

_FOLDS = (("chs", "x"), ("ck", "k"), ("ph", "f"), ("th", "t"), ("ß", "ss"))


def _fold(word: str) -> str:
    """Kleinschreibung, wobei von Whisper vertauschte Schreibweisen zusammenfallen ("Sechstant" ~ "Sextant")."""
    word = word.lower()
    for old, new in _FOLDS:
        word = word.replace(old, new)
    return word


_TERMS_LOWER: dict[str, str] = {t.lower(): t for t in TERMS}
_TERMS_FOLDED: dict[str, str] = {_fold(t): t for t in TERMS}
_NEVER_LOWER = frozenset(w.lower() for w in NEVER_CORRECT)
_INFLECTIONS = ("e", "en", "er", "es", "em", "n", "s", "is", "us")
_TOKEN = re.compile(r"\w+")
_L_CODE = re.compile(r"^[Ll](\d{3}[a-z]?)$")  # "L935d" -> "Ä935d" (Whisper verliert den Umlaut)


def levenshtein(a: str, b: str, limit: int) -> int:
    """Editierdistanz, aus Geschwindigkeitsgründen bei ``limit + 1`` gekappt."""
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
    """Höchstens eine Änderung, und bei drei Buchstaben nur für Abkürzungen in Großschreibung."""
    return 1 if len(token) > 3 or token.isupper() else 0


def _is_inflection(low: str, term_low: str) -> bool:
    return low.startswith(term_low) and low[len(term_low):] in _INFLECTIONS


def correct_token(token: str) -> str | None:
    """Kanonische Schreibweise für ein einzelnes verhörtes Token, sonst None."""
    low = token.lower()
    if alias := ALIASES.get((low,)):
        return alias
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
        if d > limit:
            continue
        if folded.endswith("n") and term_folded.endswith(("ung", "et")):
            continue
        if d < best_distance:
            best, best_distance, ambiguous = term, d, False
        elif d == best_distance:
            ambiguous = True
    return None if ambiguous else best


def correct(text: str) -> tuple[str, list[Correction]]:
    """Korrigierter Text und alle angewandten Korrekturen (Offsets beziehen sich auf ``text``)."""
    tokens = [(m.start(), m.end(), m.group()) for m in _TOKEN.finditer(text)]
    corrections: list[Correction] = []
    i = 0
    while i < len(tokens):
        pair = tuple(t[2].lower() for t in tokens[i : i + 2])
        if len(pair) == 2 and pair in ALIASES:
            start, end = tokens[i][0], tokens[i + 1][1]
            corrections.append(Correction(text[start:end], ALIASES[pair], start, end))
            i += 2
            continue
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
