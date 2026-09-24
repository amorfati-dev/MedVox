// Büro: „Original vor der Korrektur“ eines am iPad korrigierten Diktats, aufklappbar – geänderte Wörter
// durchgestrichen und eingefügt, darunter die Ziffernänderungen je Zahn. Nur lesen (Entscheidung F3).
import { Fragment, useMemo } from "react";
import { codeOf, type StoredDictation } from "../api";
import { byCode, mainPositions, type Original } from "../catalog";
import { useCatalog } from "../hooks/useCatalog";
import { codeChanges, describe, excerpt, wordDiff } from "../textdiff";

type Props = { d: StoredDictation; original: Original };

export function OriginalDiff({ d, original }: Props) {
  const catalog = useCatalog(d.patient_type); // Familien für „13b → 13c“; ohne Katalog: entfällt/ergänzt
  const parts = useMemo(() => excerpt(wordDiff(original.transcript, d.transcript)), [original.transcript, d.transcript]);
  const codes = useMemo(() => {
    const off = new Set(d.deselected);
    const chosen = new Set(d.codes.filter((c) => !off.has(c)).map(codeOf));
    const now = mainPositions(d.suggestions.filter((s) => chosen.has(s.code)));
    return describe(codeChanges(original.positions, now, byCode(catalog.entries ?? [])), "ergänzt");
  }, [d.codes, d.deselected, d.suggestions, original.positions, catalog.entries]);
  const changed = parts.some((p) => p.kind !== "same");
  return (
    <details className="orig">
      <summary>Original vor der Korrektur</summary>
      <p>
        {changed
          ? parts.map((p, i) => (
              <Fragment key={i}>
                {i > 0 && " "}
                {p.kind === "del" ? <del>{p.text}</del> : p.kind === "ins" ? <ins>{p.text}</ins> : p.text}
              </Fragment>
            ))
          : "Text unverändert."}
      </p>
      <p className="small muted">Ziffern: {codes || "unverändert"}</p>
    </details>
  );
}
