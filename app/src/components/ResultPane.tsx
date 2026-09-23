// Rechte Spalte der Diktat-Ansicht: Kurzcode, Hinweise, Kopfzeile, Transkript, Liste nach Zahn,
// Kopiervorschau und die Leiste Text · Ziffern · An Rezeption. Nur Anzeige – Zustand und Aktionen
// kommen aus der Diktat-Ansicht (useDictation, useSelection, useTransfer).
import { evidentText, type PatientType, type Suggestion } from "../api";
import type { Dictation } from "../hooks/useDictation";
import type { Selection } from "../hooks/useSelection";
import type { Transfer } from "../hooks/useTransfer";
import type { Counts } from "../result";
import type { UiState } from "../status";
import { CopyButton } from "./CopyButton";
import { CopyPreview } from "./CopyPreview";
import { Icon } from "./Icon";
import { PATIENT_LABEL } from "./PatientSwitch";
import { ResultHead, ResultList } from "./ResultList";
import { TransferBoard } from "./TransferBoard";

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

export function ResultPane({ d, sel, plans, counts, state, patientType, running, hasResult, closed, transfer, onClear, onHandover }: Props) {
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
          <h2>Transkript</h2>
          <p className="transcript" aria-live="polite">
            {d.transcript}
          </p>
        </section>
      )}
      {hasResult && (
        <ResultList groups={sel.groups} planned={plans} notes={d.notes} onToggle={sel.toggleCode} onAdopt={sel.toggleOption} />
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
    </main>
  );
}
