"""Praxisregeln des Behandlers im Katalog prüfen: ``analog``, ``conflicts`` und ``repeat`` (Aufbau: README.md)."""

from __future__ import annotations


def check_praxis(entries: list[dict], by_key: dict) -> list[str]:
    return _check_conflicts(entries, by_key) + _check_repeat(entries, by_key)


def _check_conflicts(entries: list[dict], by_key: dict) -> list[str]:
    """analog nur ohne BEMA-Paar/Zuzahlung; conflicts: Ziel vorhanden, Paare tragen den Konflikt mit dem Paar des Ziels."""
    errors: list[str] = []
    for e in entries:
        label = f"{e['system']} {e['code']}"
        if "analog" in e and (e["system"] == "BEMA" or e.get("equivalent") or e.get("zuzahlung", {}).get("allowed")):
            errors.append(f"{label}: 'analog' nur bei GOZ/GOÄ ohne BEMA-Paar und ohne erlaubte Zuzahlung")
        for c in e.get("conflicts", []):
            target = by_key.get((c["system"], c["code"]))
            if target is None or target is e:
                errors.append(f"{label}: Konflikt {c['system']} {c['code']} fehlt in dieser Datei oder ist die eigene Ziffer")
                continue
            for link in e.get("equivalent", []):
                have = {(x["system"], x["code"]) for x in by_key.get((link["system"], link["code"]), {}).get("conflicts", [])}
                errors += [f"{label}: Paar {link['system']} {link['code']} trägt den Konflikt mit {w[0]} {w[1]} nicht"
                           for w in [(x["system"], x["code"]) for x in target.get("equivalent", [])] if w not in have]
    return errors


def _check_repeat(entries: list[dict], by_key: dict) -> list[str]:
    """repeat: Ziele (only_with) stehen in derselben Datei und sind nicht die eigene Ziffer."""
    errors: list[str] = []
    for e in entries:
        for t in e.get("repeat", {}).get("only_with", []):
            target = by_key.get((t["system"], t["code"]))
            if target is None or target is e:
                errors.append(f"{e['system']} {e['code']}: repeat-Ziel {t['system']} {t['code']} fehlt in dieser Datei "
                              "oder ist die eigene Ziffer")
    return errors
