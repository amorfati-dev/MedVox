"""Prüftabellen für den Behandler: Paare BEMA <-> GOZ/GOÄ und die Zuzahlungs-Liste.

``python -m medvox.catalog.validate --markdown`` druckt beide für Katalog v1 und den erweiterten Katalog
als Markdown, je Zeile ein ☐ zum Abhaken oder Streichen; daraus entsteht ``PRUEFLISTE.md``
(``make catalog-review``). ``text_sections`` hängt sie als Text an die Review-Tabelle.
"""
from __future__ import annotations

AREAS = ("Diagnostik", "Röntgen", "Anästhesie", "Konservierend", "Endodontie", "Chirurgie", "Prophylaxe", "PAR", "Prothetik")


def _label(e: dict) -> str:
    return f"{e['system']} {e['code']}"


def pairs(catalog: dict) -> list[tuple[dict, dict, str | None]]:
    """(BEMA-Eintrag, GOZ/GOÄ-Eintrag, Hinweis) je hinterlegtem Paar, nach Fachbereich der BEMA-Seite."""
    by_key = {(e["system"], e["code"]): e for e in catalog["entries"]}
    rows = []
    for area in AREAS:
        for e in catalog["entries"]:
            if e["system"] != "BEMA" or e["area"] != area:
                continue
            for link in e.get("equivalent", []):
                other = by_key.get((link["system"], link["code"]))
                if other:
                    back = next((x for x in other.get("equivalent", []) if x["code"] == e["code"]), {})
                    rows.append((e, other, link.get("note") or back.get("note")))
    return rows


def co_payments(catalog: dict) -> list[dict]:
    """Alle GOZ/GOÄ-Einträge mit Zuzahlungs-Angabe, nach Fachbereich."""
    return [e for area in AREAS for e in catalog["entries"] if e["area"] == area and e.get("zuzahlung")]


def text_sections(catalog: dict) -> list[str]:
    lines = ["== Paare BEMA <-> GOZ/GOÄ (Patiententyp wählt eine Seite) =="]
    for bema, other, note in pairs(catalog):
        lines.append(f"  {bema['code']:<7}<-> {_label(other):<11}{bema['title'][:40]:<42}{note or ''}")
    lines += ["", "== Zuzahlungs-Liste (Kassenpatient, Vorschlag zur Prüfung) =="]
    for e in co_payments(catalog):
        z = e["zuzahlung"]
        basis = "/".join(z["basis"]) or "–"
        lines.append(f"  {'ja  ' if z['allowed'] else 'nein'} {_label(e):<11}{basis:<14}{e['title'][:44]}")
    return lines + [""]


HEADER = """# Prüfliste Patiententyp: Paare und Zuzahlungs-Liste

Erzeugt aus `catalog_v1.json` und `catalog_extended.json` mit `make catalog-review` – nicht von Hand
ändern, sondern den Katalog. Bewusst nicht aufgenommene Leistungen: `README.md`, Abschnitt „Patiententyp“.
**Vorschlag zur Prüfung durch den Behandler, keine Rechtsberatung.** Je Zeile abhaken oder streichen.

- **Paar:** dieselbe diktierte Leistung in BEMA und GOZ/GOÄ; der Patiententyp wählt genau eine Ziffer
  (Kassenpatient BEMA, Privatpatient GOZ/GOÄ), nie beide. Der Hinweis erscheint beim Umstellen als Prüfpunkt.
- **Zuzahlung „ja“:** der Extraktor schlägt die Privatleistung auch beim Kassenpatienten vor, als
  `zuzahlung` markiert. „nein“: beim Kassenpatienten nie (Kassenleistung, umstritten oder nicht belegt).
- **BEMA-Bezug:** bei „ja“ die BEMA-Position, neben der sie üblich ist (– = eigenständige Privatleistung),
  bei „nein“ die Kassenleistung, die sie abdeckt.
"""


def markdown(parts: list[tuple[str, dict]]) -> str:
    """Prüftabellen je Katalog (Überschrift, Katalog) als Markdown mit gemeinsam nummerierten Quellen."""
    refs: dict[str, int] = {}
    names: dict[str, str] = {}

    def cite(urls: list[str]) -> str:
        return " ".join(f"[Q{refs.setdefault(u, len(refs) + 1)}]" for u in urls)

    out: list[str] = []
    for heading, catalog in parts:
        names |= {src["url"]: src["name"] for src in catalog["meta"]["sources"]}
        pair_sources = catalog["meta"].get("paar_quellen", [])
        out += [f"## {heading}", "", "### Paare BEMA ↔ GOZ/GOÄ", "",
                "| ☐ | BEMA | Kurztext | Privat | Kurztext | Hinweis | Quelle |", "|---|---|---|---|---|---|---|"]
        for bema, other, note in pairs(catalog):
            out.append(f"| ☐ | {bema['code']} | {bema['title']} | {_label(other)} | {other['title']} | {note or ''} | "
                       f"{cite(bema['sources'][:1] + other['sources'][:1] + pair_sources)} |")
        for area in AREAS:
            rows = [e for e in co_payments(catalog) if e["area"] == area]
            if not rows:
                continue
            out += ["", f"### Zuzahlung – {area}", "",
                    "| ☐ | Zuzahlung | Ziffer | Kurztext | BEMA-Bezug | übliche Grundlage | Quelle |",
                    "|---|---|---|---|---|---|---|"]
            for e in rows:
                z = e["zuzahlung"]
                out.append(f"| ☐ | {'ja' if z['allowed'] else 'nein'} | {_label(e)} | {e['title']} | "
                           f"{', '.join(z['basis']) or '–'} | {z['note']} | {cite(z['sources'])} |")
        out.append("")
    out += ["## Quellen", ""] + [f"- Q{n}: [{names.get(url, url)}]({url})" for url, n in refs.items()]
    return "\n".join(out)
