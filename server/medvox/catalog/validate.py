"""Prüft einen Katalog (Standard: catalog_v1.json) gegen schema.json und fachliche Regeln, druckt die Review-Tabelle.

Aufruf:  python -m medvox.catalog.validate [--catalog PFAD] [--schema PFAD] [--quiet]
Exit 0 = gültig, Exit 1 = Fehler (werden einzeln aufgelistet).

Bewusst ohne Fremdbibliothek: ein kleiner Prüfer für genau die Schema-Schlüsselwörter,
die schema.json verwendet. Unbekannte Schlüsselwörter sind ein Fehler, damit das Schema
nichts verspricht, was hier nicht geprüft wird.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "catalog_v1.json"
SCHEMA_PATH = HERE / "schema.json"

# Ziffernformat je System (Ä925a, 13a, IP5, AITa ... / 2080 / Ä5004)
CODE_FORMAT = {
    "BEMA": re.compile(r"^(Ä\d{1,3}[a-d]?|\d{1,3}[a-h]?|IP[1-5]|FU(1|2|Pr)|FLA|ATG|MHU|AIT[ab]|BEV[ab]|CPT[ab]|UPT[a-g])$"),
    "GOZ": re.compile(r"^\d{4}$"),
    "GOÄ": re.compile(r"^Ä\d{1,4}$"),
}
ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs"}
# Reihenfolge der Fachbereiche in der Review-Tabelle (GOZ-Nummern springen zwischen Bereichen)
AREAS = ("Diagnostik", "Röntgen", "Anästhesie", "Konservierend", "Endodontie", "Chirurgie", "Prophylaxe", "PAR", "Prothetik")
TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
    "integer": int, "number": (int, float),
}


# ----------------------------------------------------------------- Schema
def _is_type(value, name: str) -> bool:
    if name in ("integer", "number") and isinstance(value, bool):
        return False
    if name == "integer" and isinstance(value, float):
        return value.is_integer()
    return isinstance(value, TYPES[name])


def _resolve(ref: str, root: dict) -> dict:
    node = root
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def check_schema(value, schema: dict, root: dict, path: str, errors: list[str]) -> None:
    """Rekursive Prüfung; jede Verletzung wird als Text an errors angehängt."""
    if "$ref" in schema:
        check_schema(value, _resolve(schema["$ref"], root), root, path, errors)
        return
    unknown = set(schema) - ANNOTATIONS - {
        "type", "enum", "pattern", "minLength", "maxLength", "minimum", "properties",
        "required", "additionalProperties", "items", "minItems", "uniqueItems",
    }
    if unknown:
        errors.append(f"{path}: Schema verwendet ungeprüfte Schlüsselwörter {sorted(unknown)}")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, t) for t in types):
            errors.append(f"{path}: erwartet {'/'.join(types)}, ist {type(value).__name__}")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} nicht in {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} passt nicht auf /{schema['pattern']}/")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: {value!r} kürzer als {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: {value!r} länger als {schema['maxLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} kleiner als {schema['minimum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: Pflichtfeld '{key}' fehlt")
        if schema.get("additionalProperties") is False:
            for key in set(value) - set(props):
                errors.append(f"{path}: unbekanntes Feld '{key}'")
        for key, sub in props.items():
            if key in value:
                check_schema(value[key], sub, root, f"{path}.{key}", errors)
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: weniger als {schema['minItems']} Einträge")
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True, ensure_ascii=False) for v in value]
            for dup in {s for s in seen if seen.count(s) > 1}:
                errors.append(f"{path}: doppelt {dup}")
        if "items" in schema:
            for i, item in enumerate(value):
                check_schema(item, schema["items"], root, f"{path}[{i}]", errors)


# ------------------------------------------------------------ Fachregeln
def check_rules(catalog: dict) -> tuple[list[str], list[str]]:
    """Regeln, die ein JSON-Schema nicht ausdrücken kann. Liefert (errors, infos)."""
    errors: list[str] = []
    infos: list[str] = []
    entries = catalog["entries"]
    by_key = {(e["system"], e["code"]): e for e in entries}
    meta_urls = {s["url"] for s in catalog["meta"]["sources"]}

    for (system, code), n in Counter((e["system"], e["code"]) for e in entries).items():
        if n > 1:
            errors.append(f"{system} {code}: {n}× vorhanden (Ziffer muss je System eindeutig sein)")

    kw_owner: dict[tuple[str, str], list[str]] = defaultdict(list)
    for e in entries:
        label = f"{e['system']} {e['code']}"
        if not CODE_FORMAT[e["system"]].match(e["code"]):
            errors.append(f"{label}: Ziffernformat passt nicht zum System")
        if "abbrev" in e and e["system"] != "BEMA":
            errors.append(f"{label}: 'abbrev' gibt es nur bei BEMA")
        for kw in e["keywords"]:
            if kw != kw.strip() or "  " in kw:
                errors.append(f"{label}: Keyword {kw!r} hat überflüssige Leerzeichen")
            kw_owner[(e["system"], kw)].append(e["code"])
        for url in e["sources"]:
            if url not in meta_urls:
                errors.append(f"{label}: Quelle {url} fehlt in meta.sources")
        fam = e.get("surfaces_to_code")
        if fam:
            if e["code"] not in fam.values():
                errors.append(f"{label}: eigene Ziffer fehlt in surfaces_to_code")
            for n_surf, target in fam.items():
                other = by_key.get((e["system"], target))
                if other is None:
                    errors.append(f"{label}: surfaces_to_code[{n_surf}] zeigt auf unbekannte Ziffer {target}")
                elif other.get("surfaces_to_code") != fam:
                    errors.append(f"{label}: {target} trägt eine andere surfaces_to_code-Familie")

    for (system, kw), codes in kw_owner.items():
        if len(codes) > 1:
            errors.append(f"{system}: Keyword {kw!r} bei mehreren Ziffern {codes} (exakt gleiches Keyword)")
    cross = defaultdict(set)
    for (system, kw), codes in kw_owner.items():
        cross[kw].add(system)
    shared = sorted(kw for kw, systems in cross.items() if len(systems) > 1)
    if shared:
        infos.append(f"{len(shared)} Keywords kommen in mehreren Systemen vor (erlaubt): {', '.join(shared)}")
    return errors, infos


# ---------------------------------------------------------- Review-Tabelle
def review_table(catalog: dict) -> str:
    entries = catalog["entries"]
    lines = [f"{catalog['meta']['name']} – Version {catalog['meta']['version']}", ""]
    for system in ("BEMA", "GOZ", "GOÄ"):
        rows = [e for e in entries if e["system"] == system]
        if not rows:
            continue
        lines.append(f"== {system} ({len(rows)} Positionen) ==")
        for area in AREAS:
            area_rows = [e for e in rows if e["area"] == area]
            if not area_rows:
                continue
            lines.append(f"-- {area}")
            for e in area_rows:
                points = "?" if e["points"] is None else str(e["points"])
                abbrev = f" ({e['abbrev']})" if e.get("abbrev") else ""
                lines.append(
                    f"  {e['code']:<7}{points:>5}  {e['title'] + abbrev:<64} kw={len(e['keywords']):<3}"
                    f"{e['review']['status']}"
                )
        lines.append("")
    unverified = [f"{e['system']} {e['code']}" for e in entries if e["points"] is None]
    status = Counter(e["review"]["status"] for e in entries)
    lines.append(f"Gesamt: {len(entries)} Positionen, Status: {dict(status)}")
    lines.append("Punkte nicht verifiziert (bitte prüfen): " + (", ".join(unverified) or "keine"))
    return "\n".join(lines)


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(catalog_path: Path = CATALOG_PATH, schema_path: Path = SCHEMA_PATH) -> tuple[list[str], list[str], dict]:
    catalog = load(catalog_path)
    schema = load(schema_path)
    errors: list[str] = []
    check_schema(catalog, schema, schema, "$", errors)
    if not errors:
        rule_errors, infos = check_rules(catalog)
        errors.extend(rule_errors)
    else:
        infos = []
    return errors, infos, catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--quiet", action="store_true", help="keine Review-Tabelle ausgeben")
    args = parser.parse_args(argv)
    errors, infos, catalog = validate(args.catalog, args.schema)
    if not args.quiet and not errors:
        print(review_table(catalog))
    for info in infos:
        print(f"INFO: {info}")
    for err in errors:
        print(f"FEHLER: {err}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} Fehler in {args.catalog.name}", file=sys.stderr)
        return 1
    print(f"OK: {args.catalog.name} ist gültig ({len(catalog['entries'])} Positionen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
