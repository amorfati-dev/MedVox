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
        ("1, 6, 2, 6", False, "16, 26"),
        ("1 6 2 6", False, "16 26"),
        ("3 6, 3 7, 4", True, "36, 37, 4"),  # Regel 1: Paare bleiben Paare, die Anzahl vor der Einheit nicht
        ("3 6, 3", True, "36, 3"),
        ("3, 5, 6", True, "3, 5, 6"),  # Regel 3: Messwertliste vor einer Einheit
        ("2,3", True, "2,3"),
        ("3 6", True, "3 6"),  # Regel 2: direkt vor einer Einheit wird nicht gepaart
        ("3 6, 1, 6", False, "36, 16"),
        ("3 9", False, "3 9"),  # kein FDI-Zahn
        ("2, 9, 1, 6", False, "2, 9, 16"),
    ],
)
def test_pair_digit_run_rules(run, unit_follows, expected):
    assert pair_digit_run(run, unit_follows) == expected
