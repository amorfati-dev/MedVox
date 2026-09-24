// Katalog-Blatt: Ziffer an einem Zahn ändern oder ergänzen, gebaut wie die Patientenauswahl (Vollbild,
// Tippflächen ≥ 64 px). Oben die Füllungsfamilie an diesem Zahn (Antippen ersetzt nur hier), darunter Suche,
// Fachbereiche und die Liste – nur aus dem Katalog, schon nach Patiententyp gefiltert. Keine freie
// Ziffern-Eingabe. Dieselbe Ziffer am selben Zahn noch einmal antippen zählt eins mehr („2×“).
import { useEffect, useMemo, useState } from "react";
import type { PatientType, Suggestion } from "../api";
import { areas, byCode, filterCatalog, toothOf, type CatalogEntry } from "../catalog";
import { countAt } from "../correction";
import type { SheetTarget } from "../hooks/useCorrection";
import { Icon } from "./Icon";
import { PATIENT_LABEL } from "./PatientSwitch";
import { ToothChooser } from "./ToothChooser";

type Props = {
  target: SheetTarget;
  patientType: PatientType;
  suggestions: Suggestion[];
  entries: CatalogEntry[] | null;
  error: string | null;
  onTarget: (target: SheetTarget) => void;
  onAdd: (entry: CatalogEntry, tooth: number | null) => void;
  onReplace: (tooth: number | null, from: string, to: CatalogEntry) => void;
  onClose: () => void;
};

// `partner`: Hinweis auf Zuzahlung bzw. BEMA-Basis derselben Füllung am Zahn, die beim Ersetzen mitwandert.
type Family = { code: string; replaced?: string; label: string; members: CatalogEntry[]; partner?: string };

// Füllungsfamilien der Hauptvorschläge an diesem Zahn: je vorgeschlagener Ziffer eine Reihe.
function families(suggestions: Suggestion[], tooth: number | null, catalog: Map<string, CatalogEntry>): Family[] {
  const found = new Map<string, Family>();
  for (const s of suggestions) {
    const own = catalog.get(s.code);
    if (s.alternative || toothOf(s) !== tooth || !own || own.family.length === 0 || found.has(s.code)) continue;
    const members = [...new Set(own.family)].flatMap((c) => catalog.get(c) ?? []);
    // wie correction.ts: nur bei eindeutiger Flächenzahl (nicht beim Inlay 2170 für drei und vier Flächen)
    const unique = new Set(own.family).size === own.family.length;
    const mate = !unique ? undefined : suggestions.find((p) => {
      const other = catalog.get(p.code);
      return toothOf(p) === tooth && other && other.system !== own.system && other.family.length > 0;
    });
    const what = !mate ? "" : mate.alternative ? "Die Zuzahlungs-Option" : mate.kind === "bema" ? "Der Kassenanteil" : "Die Zuzahlung";
    const partner = mate && `${what} ${mate.code} wandert mit.`;
    found.set(s.code, { code: s.code, replaced: s.replaced, label: own.title.split(",")[0], members, partner });
  }
  return [...found.values()];
}

export function CatalogSheet({ target, patientType, suggestions, entries, error, onTarget, onAdd, onReplace, onClose }: Props) {
  const tooth = target === "wählen" ? undefined : target.tooth;
  const catalog = useMemo(() => byCode(entries ?? []), [entries]);
  const fams = useMemo(() => (tooth ? families(suggestions, tooth, catalog) : []), [suggestions, tooth, catalog]);
  const [query, setQuery] = useState("");
  const [chosenArea, setArea] = useState<string | null | undefined>(undefined); // undefined: Fachbereich der Füllung
  const area = chosenArea === undefined ? (fams[0]?.members[0]?.area ?? null) : chosenArea;
  const inFamily = new Map(fams.flatMap((f) => f.members.map((m) => [m.code, f.code] as const)));
  const list = useMemo(() => filterCatalog(entries ?? [], query, area), [entries, query, area]);
  const where = tooth === undefined ? "Zahn wählen" : tooth === null ? "Ohne Zahn" : `Zahn ${tooth}`;
  const title = `${where} · Ziffer ${tooth ? "ändern oder ergänzen" : "ergänzen"} · ${PATIENT_LABEL[patientType]}`;

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => ev.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="picker-backdrop">
      <section className="picker cat" role="dialog" aria-modal="true" aria-label={title}>
        <header className="picker-head">
          <h2>{title}</h2>
          <button type="button" className="btn btn-icon" aria-label="Schließen" onClick={onClose}>
            <Icon name="x" />
          </button>
        </header>
        {tooth === undefined ? (
          <ToothChooser onChoose={(t) => onTarget({ tooth: t })} />
        ) : (
          <>
            {fams.map((f) => (
              <div key={f.code}>
                <div className="cat-family">
                  <span>
                    {f.label} an Zahn {tooth}:
                  </span>
                  {f.members.map((m) => (
                    <button
                      key={m.code}
                      type="button"
                      className={`btn fam${m.code === f.code ? " fam-on" : m.code === f.replaced ? " fam-now" : ""}`}
                      aria-pressed={m.code === f.code}
                      onClick={() => m.code !== f.code && onReplace(tooth, f.code, m)}
                    >
                      {m.code}
                    </button>
                  ))}
                </div>
                <p className="cat-note">
                  Antippen <b>ersetzt</b> {f.code} nur an Zahn {tooth}.
                  {f.partner && ` ${f.partner}`}
                </p>
              </div>
            ))}
            <div className="cat-search">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Suchen: Ziffer oder Wort, z. B. „Zahnstein“ oder „107“"
                aria-label="Katalog durchsuchen"
                autoCorrect="off"
                spellCheck={false}
              />
            </div>
            <div className="chips">
              {areas(entries ?? []).map((a) => (
                <button
                  key={a}
                  type="button"
                  className={a === area ? "btn chip-f chip-on" : "btn chip-f"}
                  aria-pressed={a === area}
                  onClick={() => setArea(a === area ? null : a)}
                >
                  {a}
                </button>
              ))}
            </div>
            {error && <p className="error">{error}</p>}
            {entries === null && !error && <p className="muted">Lade Katalog …</p>}
            {entries !== null && list.length === 0 && <p className="muted">Nichts gefunden – anderes Wort oder anderen Fachbereich wählen.</p>}
            <ul className="cat-list">
              {list.map((e) => {
                const n = countAt(suggestions, tooth, e.code);
                const privat = e.kind !== "bema";
                const hints = [
                  e.evident ? `Evident: ${e.evident}` : "",
                  n > 0 ? `${tooth ? `an Zahn ${tooth}` : "ohne Zahn"} schon gewählt – Antippen zählt ${n + 1}×` : "",
                  n === 0 && inFamily.has(e.code) ? `zusätzlich zu ${inFamily.get(e.code)} – zum Ersetzen oben antippen` : "",
                  e.kind === "zuzahlung" ? "Zuzahlung – nur mit Vereinbarung" : "",
                ].filter(Boolean);
                return (
                  <li key={`${e.system}-${e.code}`}>
                    <button type="button" className={privat ? "cat-row zz" : "cat-row"} onClick={() => onAdd(e, tooth)}>
                      <span className="row-code">{e.code}</span>
                      <span className="row-title">
                        {e.title}
                        {hints.length > 0 && <small>{hints.join(" · ")}</small>}
                      </span>
                      <span className="row-tag">{e.kind === "zuzahlung" ? "Zuzahlung" : e.system}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
