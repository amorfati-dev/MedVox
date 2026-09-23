// Diktat-Ansicht: links die Steuerung (Schalter Kasse/Privat, Statusfeld, Aufnahmeknopf),
// rechts das Ergebnis (Kopfzeile, Transkript, Liste nach Zahn, Geplantes, Hinweise) mit der
// Leiste Text · Ziffern · An Rezeption. Im Querformat (≥ 900 px) zwei Spalten, im Hochformat
// untereinander (styles/diktat.css). Die Aufnahme- und Warteschlangenlogik liegt in useDictation.
import { useMemo, useState } from "react";
import { api, ApiError, evidentText } from "../api";
import { Controls } from "../components/Controls";
import { CopyButton } from "../components/CopyButton";
import { Icon } from "../components/Icon";
import { MoreMenu } from "../components/MoreMenu";
import { PATIENT_LABEL, PatientSwitch } from "../components/PatientSwitch";
import { ResultHead, ResultList } from "../components/ResultList";
import { StatusPanel } from "../components/StatusPanel";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { TransferBoard } from "../components/TransferBoard";
import { useDictation } from "../hooks/useDictation";
import { usePatientType } from "../hooks/usePatientType";
import { useSelection } from "../hooks/useSelection";
import { useTransfer } from "../hooks/useTransfer";
import { countGroups, positionsOf, uniquePlanned } from "../result";
import { formatSeconds, plural, uiState } from "../status";
import { Login } from "./Login";

type Props = { onLogout: () => void };

const UNSUPPORTED = "Dieser Browser kann nicht aufnehmen – bitte Safari auf dem iPad verwenden.";

export function Diktat({ onLogout }: Props) {
  const [patientType, setPatientType] = usePatientType();
  const d = useDictation(patientType);
  const sel = useSelection(d.codes, d.suggestions);
  const plans = useMemo(() => uniquePlanned(d.planned), [d.planned]);
  const counts = useMemo(() => countGroups(sel.groups, plans), [sel.groups, plans]);
  const details = useMemo(
    () => (d.resultType ? { patient_type: d.resultType, positions: positionsOf(sel.groups) } : null),
    [d.resultType, sel.groups],
  );
  const transfer = useTransfer(d.transcript, sel.evident, details, d.sessionExpired);
  const recording = d.phase === "aufnahme";
  const sending = d.phase === "sende";
  const resumable = d.phase === "fortsetzbar";
  const [logoutError, setLogoutError] = useState<string | null>(null);

  const logout = async () => {
    setLogoutError(null);
    try {
      await api.logout();
      onLogout();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onLogout();
        return;
      }
      setLogoutError(e instanceof ApiError ? e.message : "Abmelden fehlgeschlagen.");
    }
  };

  const startNew = () => {
    sel.clear();
    void d.start();
  };

  const clear = () => {
    d.reset();
    sel.clear();
  };

  // Sitzung abgelaufen: Anmeldung anzeigen, Diktat und offene Abschnitte bleiben im Speicher.
  if (d.sessionLost) {
    return (
      <Login
        notice="Sitzung abgelaufen – bitte erneut anmelden. Das aktuelle Diktat bleibt erhalten."
        onLogin={d.relogin}
      />
    );
  }

  const error = d.supported ? d.error : UNSUPPORTED;
  const state = uiState({ ...d, error });
  const summary = [
    d.lastLatency !== null ? formatSeconds(d.lastLatency) : "",
    plural(counts.positions, "Ziffer", "Ziffern"),
    counts.planned > 0 ? `${counts.planned} geplant` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  const hasResult = d.transcript !== "" || sel.groups.length > 0 || plans.length > 0;

  return (
    <div className="diktat ipad">
      <aside className="control" aria-label="Aufnahme">
        <header className="control-head">
          <h1>MedVox</h1>
          <ThemeSwitch />
          <MoreMenu onLogout={logout} />
        </header>
        <PatientSwitch value={patientType} onChange={setPatientType} disabled={recording || sending || resumable} />
        {(recording || sending || resumable) && (
          <p className="switch-hint">Der Patiententyp gilt für das ganze laufende Diktat.</p>
        )}
        <div className="control-main">
          <StatusPanel
            state={state}
            seconds={d.seconds}
            level={d.level}
            waiting={d.waiting}
            uploading={d.uploading}
            error={error}
            rejected={d.discardable}
            summary={summary}
          />
          <Controls state={state} d={d} onNew={startNew} onClear={clear} handedOver={transfer.result !== null} />
        </div>
        {logoutError && (
          <p role="alert" className="error">
            {logoutError}
          </p>
        )}
      </aside>

      <main className="result">
        {transfer.result && <TransferBoard result={transfer.result} />}
        {hasResult ? (
          <ResultHead counts={counts} resultType={d.resultType} numbersText={evidentText(sel.numbers)} />
        ) : (
          <p className="muted empty">Noch nichts diktiert – „Aufnehmen“ antippen und sprechen.</p>
        )}
        {d.resultType && d.resultType !== patientType && !recording && !sending && !resumable && (
          <p className="notice">
            Diese Ziffern gelten für einen {PATIENT_LABEL[d.resultType]}en. „Aufnehmen“ beginnt ein neues Diktat als{" "}
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
          <ResultList
            groups={sel.groups}
            planned={plans}
            notes={d.notes}
            onToggle={sel.toggleCode}
            onAdopt={sel.toggleOption}
          />
        )}

        <footer className="bottom-bar">
          {transfer.error && (
            <p role="alert" className="error bottom-error">
              {transfer.error}
            </p>
          )}
          <CopyButton label="Text kopieren" text={d.transcript} />
          <CopyButton label="Ziffern kopieren" text={evidentText(sel.evident)} />
          <button
            type="button"
            className="btn btn-primary"
            disabled={transfer.busy || !d.transcript}
            onClick={() => void transfer.send()}
          >
            <Icon name="send" />
            {transfer.busy ? "Sende …" : "An Rezeption"}
          </button>
        </footer>
      </main>
    </div>
  );
}
