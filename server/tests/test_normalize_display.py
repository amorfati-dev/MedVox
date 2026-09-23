"""Anzeigefassung des Transkripts (normalize_display): FDI und Codes wie `normalize`,
Flächen und übriger Wortlaut wie diktiert."""

import pytest

from medvox.normalize import normalize
from medvox.normalize_display import display_text


@pytest.mark.parametrize(
    ("dictated", "shown"),
    [
        (
            "Zahn drei sechs mesial okklusal distal, Karies profunda, Kompositfüllung in Adhäsivtechnik",
            "Zahn 36 mesial okklusal distal, Karies profunda, Kompositfüllung in Adhäsivtechnik",
        ),
        ("BEMA dreizehn a, GOZ zwei eins null null.", "BEMA 13a, GOZ 2100."),
        ("OPG angefertigt, BEMA Ziffer Ä neun drei fünf d.", "OPG angefertigt, BEMA Ziffer Ä935d."),
        ("Kompositfüllung MOD, dreiflächig.", "Kompositfüllung MOD, dreiflächig."),
        ("Eins vier distale Karies.", "14 distale Karies."),
        ("Zahn 3-6 okklusal, Zahn 1 6 2 6 palatinal.", "Zahn 36 okklusal, Zahn 16 26 palatinal."),
        ("Zahn drei sechs MOD, Zahn drei sieben okklusal.", "Zahn 36 MOD, Zahn 37 okklusal."),
        (
            "Kompositfüllung MOD an drei sechs, vier sechs distal Karies.",
            "Kompositfüllung MOD an 36, 46 distal Karies.",
        ),
    ],
)
def test_display_keeps_surface_words(dictated: str, shown: str) -> None:
    assert display_text(dictated) == shown


@pytest.mark.parametrize(
    "line",
    [
        "Sondierungstiefen 3 2 3 2 2 3, BOP positiv.",
        "Ibuprofen 400 1-1-1.",
        "Mundhygieneinstruktion, Patient zufrieden.",
    ],
)
def test_display_leaves_other_wording_unchanged(line: str) -> None:
    assert display_text(line) == line


def test_internal_form_unchanged() -> None:
    text = "Zahn drei sechs mesial okklusal distal Kompositfüllung."
    assert normalize(text).text == "Zahn 36 mod Kompositfüllung."
    assert [(t.fdi, t.surfaces) for t in normalize(text).teeth] == [(36, "mod")]
