// Rechte Spalte der Diktat-Ansicht: Kurzcode, Hinweise, Kopfzeile, Transkript, Liste nach Zahn,
// Kopiervorschau und die Leiste Text · Ziffern · An Rezeption. Nur Anzeige – Zustand und Aktionen
// kommen aus der Diktat-Ansicht (useDictation, useSelection, useTransfer, useCorrection). Solange das
// Transkript bearbeitet wird, sind Liste und Leiste ausgeblendet (die Bildschirmtastatur braucht den Platz).
import { evidentText, type PatientType, type Suggestion } from "../api";
import type { Correction } from "../hooks/useCorrection";
import type { Dictation } from "../hooks/useDictation";
import type { Selection } from "../hooks/useSelection";
import type { Transfer } from "../hooks/useTransfer";
import type { Counts } from "../result";
import type { UiState } from "../status";
import { CopyButton } from "./CopyButton";
import { CatalogSheet } from "./CatalogSheet";
import { CopyPreview } from "./CopyPreview";
import { Icon } from "./Icon";
import { PATIENT_LABEL } from "./PatientSwitch";
import { RecalcNote } from "./RecalcNote";
import { ResultHead, ResultList } from "./ResultList";
import { TranscriptEditor } from "./TranscriptEditor";
import { TransferBoard } from "./TransferBoard";
import { TranscriptText } from "./TranscriptText";

type Props = {
  d: Dictation;
  sel: Selection;
  plans: Suggestion[];
  counts: Counts;
  state: UiState;
  patientType: PatientType;
  running: boolean;
  hasResult: boolean;
  closed: boolean; // schon übertragen: wird nicht mehr gespeichert
  transfer: Transfer;
  c: Correction;
  onClear: () => void; // neues Diktat beginnen (Bildschirm leeren)
  onHandover: () => void; // „An Rezeption“
};

// Rechte Spalte, solange noch kein Ergebnis da ist.
const EMPTY: Partial<Record<UiState, string>> = {
  bereit: "Noch nichts diktiert – „Aufnehmen“ antippen und sprechen.",
  aufnahme: "Aufnahme läuft – das Ergebnis erscheint nach „Stopp“.",
  senden: "Der Praxis-Mac schreibt ab …",
  fortsetzbar: "Das Aufgenommene ist gesichert und wird gesendet, sobald der Praxis-Mac antwortet.",
};

export function ResultPane({ d, sel, plans, counts, state, patientType, running, hasResult, closed, transfer, c, onClear, onHandover }: Props) {
  // Korrigieren nur mit fertigem Ergebnis, das noch gespeichert wird – nie während Aufnahme oder Senden.
  const editable = state === "fertig" && !closed && d.resultType !== null;
  if (c.editing) {
    return (
      <main className="result">
        <TranscriptEditor initial={d.transcript} busy={c.busy} error={c.error} onApply={(t) => void c.applyText(t)} onCancel={c.cancelEdit} />
      </main>
    );
  }
  return (
    <main className="result">
      {transfer.result && <TransferBoard result={transfer.result} />}
      {closed && (
        <div className="notice" role="alert">
          <p>Dieses Diktat wurde bereits übertragen – es wird nicht mehr gespeichert.</p>
          <button type="button" className="btn btn-primary" onClick={onClear}>
            Neues Diktat beginnen
          </button>
        </div>
      )}
      {c.notice && !running && <RecalcNote title={c.notice.title} changes={c.notice.changes} onUndo={c.undo} />}
      {hasResult ? (
        <ResultHead counts={counts} resultType={d.resultType} numbersText={evidentText(sel.numbers)} />
      ) : (
        <p className="muted empty">{EMPTY[state] ?? EMPTY.bereit}</p>
      )}
      {d.resultType && d.resultType !== patientType && !running && (
        <p className="notice">
          Diese Ziffern gelten für einen {PATIENT_LABEL[d.resultType]}en. „{state === "fertig" ? "Neu" : "Aufnehmen"}“ beginnt ein neues Diktat als{" "}
          {PATIENT_LABEL[patientType]}.
        </p>
      )}
      {d.transcript && (
        <section className="transcript-box">
          <div className="box-head">
            <h2>
              Transkript
              {d.corrected && d.transcript !== d.original.transcript && <span className="tag-corr">korrigiert</span>}
            </h2>
            {editable && (
              <button type="button" className="btn btn-edit" onClick={c.startEdit}>
                <Icon name="edit" />
                Bearbeiten
              </button>
            )}
          </div>
          <TranscriptText text={d.transcript} original={d.corrected ? d.original.transcript : null} />
        </section>
      )}
      {hasResult && (
        <ResultList
          groups={sel.groups}
          planned={plans}
          notes={d.notes}
          onToggle={sel.toggleCode}
          onAdopt={sel.toggleOption}
          onEdit={editable ? (tooth) => c.openSheet(tooth === undefined ? "wählen" : { tooth }) : undefined}
          onRemove={editable ? c.remove : undefined}
        />
      )}
      {hasResult && <CopyPreview blocks={sel.blocks} kasse={d.resultType === "kasse"} />}

      <footer className="bottom-bar">
        {transfer.error && (
          <p role="alert" className="error bottom-error">
            {transfer.error}
          </p>
        )}
        <CopyButton label="Text kopieren" text={d.transcript} />
        <CopyButton label="Ziffern kopieren" text={evidentText(sel.evident)} />
        <button type="button" className="btn btn-primary" disabled={transfer.busy || !d.transcript || closed} onClick={onHandover}>
          <Icon name="send" />
          {transfer.busy ? "Sende …" : "An Rezeption"}
        </button>
      </footer>
      {c.sheet !== null && d.resultType && (
        <CatalogSheet
          target={c.sheet}
          patientType={d.resultType}
          suggestions={d.suggestions}
          entries={c.catalog}
          error={c.catalogError}
          onTarget={c.openSheet}
          onAdd={c.add}
          onReplace={c.replace}
          onClose={c.closeSheet}
        />
      )}
    </main>
  );
}
