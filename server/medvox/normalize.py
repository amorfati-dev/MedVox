"""Deterministischer Normalisierer für deutsche Zahnarzt-Diktate (WP-5).

Wandelt ein (lexikon-korrigiertes) Transkript in die maschinenlesbare Form für
den Regel-Extraktor: gesprochene und von Whisper geschriebene Zahnformen ->
FDI-Nummern, Flächenwörter -> m/o/d/b/l/p/i, deutsche Zahlwörter -> Ziffern,
BEMA/GOZ/Ä-Codes zusammengefügt. Reine Funktion, ohne I/O.
``python -m medvox.normalize --demo`` gibt die Testdiktate des Reports zur
manuellen Prüfung aus.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Interne Marker, vor der Rückgabe entfernt. _NT ("no tooth") hängt hinter einer
# Zahl, die nie als Zahn gelesen werden darf (Anzahlen, zusammengefügte Codes,
# PSI-Codes); _SF markiert ein Token als normalisierte Flächenabkürzung.
_NT = "\x01"
_SF = "\x02"


@dataclass(frozen=True)
class ToothRef:
    fdi: int
    surfaces: str = ""  # z. B. "mod"; "" wenn keine Fläche diktiert wurde


@dataclass
class NormalizedText:
    text: str
    teeth: list[ToothRef] = field(default_factory=list)


# --- FDI ---------------------------------------------------------------------


def is_fdi(number: int) -> bool:
    """True für bleibende (11-48) und Milchzahn-FDI-Nummern (51-85)."""
    quadrant, tooth = divmod(number, 10)
    return (1 <= quadrant <= 4 and 1 <= tooth <= 8) or (5 <= quadrant <= 8 and 1 <= tooth <= 5)


def _arch(fdi: int) -> list[int]:
    """Alle Zähne des Kiefers (OK/UK, bleibend/Milch) in FDI-Reihenfolge."""
    quadrant = fdi // 10
    right, left = {1: (1, 2), 2: (1, 2), 3: (4, 3), 4: (4, 3), 5: (5, 6), 6: (5, 6), 7: (8, 7), 8: (8, 7)}[quadrant]
    last = 8 if quadrant <= 4 else 5
    return [right * 10 + t for t in range(last, 0, -1)] + [left * 10 + t for t in range(1, last + 1)]


def expand_range(first: int, last: int) -> list[int]:
    """Zähne von ``first`` bis ``last`` entlang des Kiefers ("17 bis 27" -> 14 Zähne)."""
    arch = _arch(first)
    if last not in arch:
        return [first, last]
    i, j = arch.index(first), arch.index(last)
    return arch[i : j + 1] if i <= j else arch[j : i + 1][::-1]


# --- Zahlwörter ---------------------------------------------------------------

_UNITS = {"null": 0, "ein": 1, "eins": 1, "zwei": 2, "zwo": 2, "drei": 3, "vier": 4, "fünf": 5,
          "fuenf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9}
_TEENS = {"zehn": 10, "elf": 11, "zwölf": 12, "zwoelf": 12, "dreizehn": 13, "vierzehn": 14,
          "fünfzehn": 15, "fuenfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19}
_TENS = {"zwanzig": 20, "dreißig": 30, "dreissig": 30, "vierzig": 40, "fünfzig": 50, "fuenfzig": 50,
         "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90}


def _alt(words) -> str:
    return "|".join(sorted(words, key=len, reverse=True))


_NUMBER_WORD = re.compile(
    rf"(?P<tausend>(?P<th>{_alt(_UNITS)})?tausend)?(?P<hundert>(?P<hu>{_alt(_UNITS)})?hundert)?"
    rf"(?:(?P<teen>{_alt(_TEENS)})|(?:(?P<tu>{_alt(_UNITS)})und)?(?P<tens>{_alt(_TENS)})|(?P<u>{_alt(_UNITS)}))?"
)
_WORD = re.compile(r"[^\W\d_]+")


def number_value(word: str) -> tuple[int, bool] | None:
    """(Wert, ist_einzelnes_Ziffernwort) für ein deutsches Zahlwort, sonst None."""
    m = _NUMBER_WORD.fullmatch(word.lower())
    if not m or not any(m.groupdict().values()):
        return None
    g = m.groupdict()
    value = 0
    if g["tausend"]:
        value += (_UNITS[g["th"]] if g["th"] else 1) * 1000
    if g["hundert"]:
        value += (_UNITS[g["hu"]] if g["hu"] else 1) * 100
    if g["teen"]:
        value += _TEENS[g["teen"]]
    elif g["tens"]:
        value += _TENS[g["tens"]] + (_UNITS[g["tu"]] if g["tu"] else 0)
    elif g["u"]:
        value += _UNITS[g["u"]]
    single = g["u"] is not None and not (g["tausend"] or g["hundert"])
    return value, single


def _number_words(text: str) -> str:
    def repl(m: re.Match) -> str:
        word = m.group()
        low = word.lower()
        if low.endswith("mal") and len(low) > 3 and (parsed := number_value(low[:-3])):
            return f"{parsed[0]}x"  # "zweimal" -> "2x"
        parsed = number_value(low)
        if parsed is None:
            return word
        value, single = parsed
        # Nur gesprochene Einzelziffern ("drei sechs") dürfen Zähne bilden; "achtundzwanzig" nie.
        return str(value) if single else f"{value}{_NT}"

    return _WORD.sub(repl, text)


# --- Codes ---------------------------------------------------------------------

_AE_CODE = re.compile(rf"\bÄ\s*(\d(?:\s\d){{0,3}}|\d+){_NT}*(?:\s*([a-kA-K]))?(?![^\W\d_]|\d)")
_PREFIX_CODE = re.compile(rf"\b(GOZ|BEMA)\s+(\d(?:\s\d){{1,4}}|\d+){_NT}*(?:\s*([a-kA-K]))?(?![^\W\d_]|\d)")
_PSI_CODES = re.compile(r"\bPSI\s+(\d(?:[\s,/-]*\d)*)(?![\w\x01])")


def _codes(text: str) -> str:
    def join(digits: str, letter: str | None) -> str:
        return re.sub(r"\s", "", digits) + (letter or "").lower() + _NT

    text = _AE_CODE.sub(lambda m: "Ä" + join(m.group(1), m.group(2)), text)
    text = _PREFIX_CODE.sub(lambda m: f"{m.group(1)} " + join(m.group(2), m.group(3)), text)
    return _PSI_CODES.sub(lambda m: "PSI " + re.sub(r"\d", lambda d: d.group() + _NT, m.group(1)), text)


# --- Flächen ---------------------------------------------------------------------

_SURFACE_WORDS = {"mesial": "m", "okklusal": "o", "occlusal": "o", "distal": "d", "bukkal": "b",
                  "buccal": "b", "vestibulär": "b", "vestibulaer": "b", "lingual": "l",
                  "palatinal": "p", "inzisal": "i", "incisal": "i"}
_SURFACE_WORD = re.compile(rf"\b({_alt(_SURFACE_WORDS)})(?:e|en|er|es|em)?\b", re.I)
_SURFACE_MOD = re.compile(r"(?<![^\W\d_])mod(?![^\W\d_])", re.I)
_SURFACE_RUN = re.compile(rf"[modblpi]{{1,5}}{_SF}(?:(?:\s*,\s*|\s+und\s+|\s+)[modblpi]{{1,5}}{_SF})+")


def _surfaces(text: str) -> str:
    text = _SURFACE_WORD.sub(lambda m: _SURFACE_WORDS[m.group(1).lower()] + _SF, text)
    text = _SURFACE_MOD.sub("mod" + _SF, text)
    # "m o, d" bzw. "m und d" (ein Token je diktiertem Wort) -> "mod" / "md"
    return _SURFACE_RUN.sub(lambda m: "".join(re.findall(rf"([modblpi]+){_SF}", m.group())) + _SF, text)


# --- Zähne ----------------------------------------------------------------------

_COUNT_NOUN = (r"\s*(?:Zähne|Zaehne|Zahn|Jahre?n?|Tage?n?|Wochen?|Monate?n?|Millimeter|mm|Minuten?|Stunden?"
               r"|Sekunden?|Prozent|%|mg|ml|Kanäle|Kanaele|Kanal|Wurzeln?|Sitzungen?|Grad|Uhr|Flächen|Implantate?|Mal|x)"
               r"(?![^\W\d_])")
_QUAD = (r"(?:(?P<jaw>Ober|Unter)kiefer\s+(?P<side>rechts|links)"
         r"|(?:im\s+|in\s+|des\s+|der\s+)?(?P<ord>erst|zweit|dritt|viert)(?:e|er|en|em|es)\s+Quadrant(?:en)?)")
_QUAD_THEN_DIGIT = re.compile(rf"{_QUAD}\s+(?P<zahn>Zahn\s+)?(?P<d>[1-8])(?![\w{_NT}])(?!{_COUNT_NOUN})", re.I)
_DIGIT_THEN_QUAD = re.compile(rf"(?<![\w{_NT}])(?P<d>[1-8])\s+(?:im\s+|in\s+)?{_QUAD}", re.I)
_DIGIT_RUN = re.compile(rf"(?<![\w{_NT}.])\d(?:(?:\s*,\s*|\s*-\s*|\s+)\d(?![\w{_NT}]))+(?![\w{_NT}])(?!{_COUNT_NOUN})")
_FOUR_DIGITS = re.compile(rf"(?<![\w{_NT}])(\d\d)(\d\d)(?![\w{_NT}])")
_TOOTH_RANGE = re.compile(rf"(?<![\w{_NT}])(\d\d)\s*(?:-|bis)\s*(\d\d)(?![\w{_NT}])")
_TOOTH = re.compile(
    rf"(?<![\w{_NT}])\d\d(?![\w{_NT}])(?!{_COUNT_NOUN})(?![.:]\d)(?!\s*-\s*\d+{_COUNT_NOUN})"
)
_RUN_GAP = re.compile(r"\s*(?:,|und|-)?\s*")
_SURFACES_AFTER = re.compile(rf"\s*,?\s*([modblpi]{{1,5}}){_SF}")
_SURFACES_BEFORE = re.compile(rf"([modblpi]{{1,5}}){_SF}\s+(?:Zahn\s+)?$")


def _quadrant(m: re.Match) -> int:
    if m.group("ord"):
        return {"erst": 1, "zweit": 2, "dritt": 3, "viert": 4}[m.group("ord").lower()]
    upper = m.group("jaw").lower() == "ober"
    right = m.group("side").lower() == "rechts"
    return {(True, True): 1, (True, False): 2, (False, False): 3, (False, True): 4}[(upper, right)]


def _quadrants(text: str) -> str:
    text = _QUAD_THEN_DIGIT.sub(lambda m: f"{m.group('zahn') or ''}{_quadrant(m)}{m.group('d')}", text)
    return _DIGIT_THEN_QUAD.sub(lambda m: f"{_quadrant(m)}{m.group('d')}", text)


def _pair_digits(m: re.Match) -> str:
    """"1 6, 2 6" -> "16, 26": Einzelziffern von links nach rechts paaren, wenn sie einen FDI-Zahn bilden."""
    parts = re.split(r"(\D+)", m.group())
    digits, seps = parts[0::2], parts[1::2]
    out: list[str] = []
    i = 0
    while i < len(digits):
        if i + 1 < len(digits) and is_fdi(int(digits[i] + digits[i + 1])):
            out.append(digits[i] + digits[i + 1])
            out.append(seps[i + 1] if i + 1 < len(seps) else "")
            i += 2
        else:
            out.append(digits[i])
            out.append(seps[i] if i < len(seps) else "")
            i += 1
    return "".join(out)


def _split_four(m: re.Match) -> str:
    a, b = int(m.group(1)), int(m.group(2))
    return f"{a}, {b}" if is_fdi(a) and is_fdi(b) else m.group()


def _range(m: re.Match) -> str:
    a, b = int(m.group(1)), int(m.group(2))
    return f"{a}-{b}" if is_fdi(a) and is_fdi(b) else m.group()


def _collect_teeth(text: str) -> list[ToothRef]:
    hits = [(m.start(), m.end(), int(m.group())) for m in _TOOTH.finditer(text) if is_fdi(int(m.group()))]
    teeth: list[ToothRef] = []
    i = 0
    while i < len(hits):
        run = [hits[i]]
        while i + 1 < len(hits) and _RUN_GAP.fullmatch(text, run[-1][1], hits[i + 1][0]):
            run.append(hits[i + 1])
            i += 1
        i += 1
        numbers: list[int] = []
        for k, (start, _end, fdi) in enumerate(run):
            if k and text[run[k - 1][1] : start].strip() == "-":
                numbers += expand_range(numbers.pop(), fdi)
            else:
                numbers.append(fdi)
        after = _SURFACES_AFTER.match(text, run[-1][1])
        before = _SURFACES_BEFORE.search(text, 0, run[0][0])
        surfaces = after.group(1) if after else before.group(1) if before else ""
        teeth += [ToothRef(n, surfaces) for n in numbers]
    return teeth


# --- Pipeline -------------------------------------------------------------------


def normalize(text: str) -> NormalizedText:
    text = unicodedata.normalize("NFC", text).replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    text = _number_words(text)
    text = _codes(text)
    text = _surfaces(text)
    text = _quadrants(text)
    text = _DIGIT_RUN.sub(_pair_digits, text)
    text = _FOUR_DIGITS.sub(_split_four, text)
    text = _TOOTH_RANGE.sub(_range, text)
    teeth = _collect_teeth(text)
    text = text.replace(_NT, "").replace(_SF, "")
    text = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s+", " ", text)).strip()
    return NormalizedText(text, teeth)


DEMO = (
    ("Zahn drei sechs mesial okklusal distal Karies profunda, Infiltrationsanästhesie mit Artikain, "
     "Kompositfüllung in Adhäsivtechnik, dreiflächig, Kofferdam gelegt."),
    ("Eins vier distal okklusal Sekundärkaries unter alter Amalgamfüllung, Kompositfüllung MOD, "
     "dreiflächig, GOZ zwei eins null null als Zusatzleistung."),
    "Kind acht Jahre, Fissurenversiegelung eins sechs, zwei sechs, drei sechs und vier sechs, IP fünf.",
    "OPG angefertigt, drei acht retiniert und verlagert, BEMA Ziffer Ä neun drei fünf d.",
    "Kürettage eins sieben bis zwei sieben, Sondierungstiefen bis sechs Millimeter, UPT in drei Monaten.",
    "Drei sechs, drei sieben okklusal Karies, BEMA dreizehn a zweimal, Zusatzleistung GOZ zwei null sechs null.",
    "Professionelle Zahnreinigung, achtundzwanzig Zähne. Ibuprofen sechshundert verordnet.",
    "Zahn 3-6 Mesial Occlusal Distal Caries Profunda. 36-37 Occlusal Caries, BEMA 13a 2x, GOZ 2060.",
    "Fissurenversiegelung 1, 6, 2, 6 und 1626. Oberkiefer rechts sechs, im vierten Quadranten Zahn sieben.",
)


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Normalisiert ein deutsches Zahnarzt-Diktat.")
    parser.add_argument("text", nargs="*", help="Diktattext (entfällt bei --demo)")
    parser.add_argument("--demo", action="store_true", help="die eingebauten Beispieldiktate ausführen")
    parser.add_argument("--raw", action="store_true", help="Lexikon-Korrektur überspringen")
    args = parser.parse_args(argv)
    for dictation in DEMO if args.demo else [" ".join(args.text)]:
        if not args.raw:
            from medvox.lexicon import correct

            dictation, corrections = correct(dictation)
            for c in corrections:
                print(f"  korrigiert: {c.original!r} -> {c.corrected!r}")
        result = normalize(dictation)
        print(result.text)
        print("  Zähne:", ", ".join(f"{t.fdi}{' ' + t.surfaces if t.surfaces else ''}" for t in result.teeth) or "-")


if __name__ == "__main__":
    main()
