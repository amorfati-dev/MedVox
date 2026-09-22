"""WP-5: FDI-Hilfsfunktionen und die Item-Regeln für Ziffernläufe."""

import pytest

from medvox.normalize_digits import expand_range, is_fdi, pair_digit_run


def test_is_fdi():
    assert all(is_fdi(n) for n in (11, 18, 21, 28, 31, 38, 41, 48, 51, 55, 65, 75, 85))
    assert not any(is_fdi(n) for n in (0, 10, 19, 20, 29, 30, 49, 50, 56, 86, 90, 100))


def test_expand_range_across_the_arch_and_fallback():
    assert expand_range(36, 37) == [36, 37]
    assert expand_range(37, 36) == [37, 36]
    assert expand_range(13, 23) == [13, 12, 11, 21, 22, 23]
    assert expand_range(16, 46) == [16, 46]  # verschiedene Kiefer: nur die Endpunkte


@pytest.mark.parametrize(
    "run, unit_follows, expected",
    [
        ("3 6", False, "36"),
        ("3-6", False, "36"),
        ("3,6", False, "36"),
        ("3,5", True, "3,5"),
        ("1, 6, 2, 6", False, "1, 6, 2, 6"),  # über ein Komma hinweg wird nie gepaart
        ("1 6 2 6", False, "1 6 2 6"),
        ("3 2 3 2 2 3", False, "3 2 3 2 2 3"),  # Sechs-Punkt-Messung
        ("3 6, 3 7, 4", True, "36, 37, 4"),  # Regel 1: Paare bleiben Paare, die Anzahl vor der Einheit nicht
        ("3 6, 3", True, "36, 3"),
        ("3, 5, 6", True, "3, 5, 6"),  # Regel 3: Messwertliste vor einer Einheit
        ("2,3", True, "2,3"),
        ("3 6", True, "36"),  # Regel 1 schlägt die Einheit: ein Ziffernpaar bleibt ein Zahn
        ("2-3", True, "2-3"),  # Regel 2: Bindestrich-Bereich vor einer Einheit ist eine Anzahl
        ("3 5 6", True, "3 5 6"),
        ("1-1-1", False, "1-1-1"),  # Dosierungsschema, nie ein Zahn
        ("1-0-1", False, "1-0-1"),
        ("4 5 4", False, "4 5 4"),  # ungerade Messwertreihe
        ("3-6", False, "36"),
        ("3 6, 1, 6", False, "36, 1, 6"),
        ("3 9", False, "3 9"),  # kein FDI-Zahn
        ("2, 9, 1, 6", False, "2, 9, 1, 6"),
    ],
)
def test_pair_digit_run_rules(run, unit_follows, expected):
    assert pair_digit_run(run, unit_follows) == expected


@pytest.mark.parametrize(
    "run, expected",
    [("3 6 3 7", "36 37"), ("3 6", "36"), ("3 5 6", "3 5 6"), ("1 6 9 9", "1 6 9 9"),
     ("3-6 3-7", "3-6 3-7")],
)
def test_longer_runs_pair_only_after_a_tooth_marker(run, expected):
    assert pair_digit_run(run, False, marker_before=True) == expected
    assert pair_digit_run(run, False) == (expected if len(run) <= 3 else run)
