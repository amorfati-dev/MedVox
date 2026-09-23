// Diktat-Ansicht: links die Steuerung (Schalter Kasse/Privat, Statusfeld, Aufnahmeknopf),
// rechts das Ergebnis (Transkript, Ziffern, Kopieren, Übergabe an die Rezeption).
// Im Querformat (≥ 900 px) zwei Spalten, im Hochformat untereinander (styles/diktat.css).
import { useMemo, useState } from "react";
import { api, ApiError, evidentLines, evidentOf, evidentText } from "../api";
import { CodeChips } from "../components/CodeChips";
import { CopyButton } from "../components/CopyButton";
import { EvidentLines } from "../components/EvidentLines";
import { Controls } from "../components/Controls";
import { MoreMenu } from "../components/MoreMenu";
import { PATIENT_LABEL, PatientSwitch } from "../components/PatientSwitch";
import { StatusPanel } from "../components/StatusPanel";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { TransferPanel } from "../components/TransferPanel";
import { useDictation } from "../hooks/useDictation";
import { usePatientType } from "../hooks/usePatientType";
import { formatSeconds, plural, uiState } from "../status";
import { Login } from "./Login";

type Props = { onLogout: () => void };

const UNSUPPORTED = "Dieser Browser kann nicht aufnehmen – bitte Safari auf dem iPad verwenden.";

export function Diktat({ onLogout }: Props) {
  const [patientType, setPatientType] = usePatientType();
  const d = useDictation(patientType);
  // Abgewählte Ziffern merken; neu vorgeschlagene gelten damit automatisch als gewählt.
  const [deselected, setDeselected] = useState<ReadonlySet<string>>(() => new Set());
  const activeCodes = useMemo(() => d.codes.filter((c) => !deselected.has(c)), [d.codes, deselected]);
  // Kopier- und Übergabeformat für Evident: je Zahn eine Zeile, Zahn vorn.
  const evident = useMemo(() => evidentLines(d.suggestions, activeCodes), [d.suggestions, activeCodes]);
  // Dieselben Zeilen nur mit amtlichen Ziffern („Nur Ziffern“) und die Kurzformen für die Chips.
  const numbers = useMemo(() => evidentLines(d.suggestions, activeCodes, false), [d.suggestions, activeCodes]);
  const forms = useMemo(() => evidentOf(d.suggestions), [d.suggestions]);
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

  const toggleCode = (code: string) =>
    setDeselected((prev) => {
      const next = new Set(prev);
      if (!next.delete(code)) next.add(code);
      return next;
    });

  const startNew = () => {
    setDeselected(new Set());
    void d.start();
  };

  const clear = () => {
    d.reset();
    setDeselected(new Set());
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

  const state = uiState({ ...d, error: d.supported ? d.error : UNSUPPORTED });
  const summary = [
    d.lastLatency !== null ? formatSeconds(d.lastLatency) : "",
    plural(activeCodes.length, "Ziffer", "Ziffern"),
  ]
    .filter(Boolean)
    .join(" · ");

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
            error={d.supported ? d.error : UNSUPPORTED}
            rejected={d.discardable}
            summary={summary}
          />
          <Controls state={state} d={d} onNew={startNew} onClear={clear} handedOver={false} />
        </div>
        {logoutError && (
          <p role="alert" className="error">
            {logoutError}
          </p>
        )}
      </aside>

      <main className="result">
        <section className="card">
          <h2>Transkript</h2>
          <p className="transcript" aria-live="polite">
            {d.transcript || <span className="muted">Noch nichts diktiert.</span>}
          </p>
          <div className="actions">
            <CopyButton label="Text kopieren" text={d.transcript} primary />
          </div>
        </section>

        <section className="card">
          <div className="section-head">
            <h2>Ziffern</h2>
            {d.resultType && (
              <span className={`badge badge-${d.resultType}`}>für {PATIENT_LABEL[d.resultType]}</span>
            )}
          </div>
          {d.resultType && d.resultType !== patientType && !recording && !sending && !resumable && (
            <p className="notice">
              Diese Ziffern gelten für einen {PATIENT_LABEL[d.resultType]}en. „Aufnehmen“ beginnt ein neues Diktat als{" "}
              {PATIENT_LABEL[patientType]}.
            </p>
          )}
          <CodeChips all={d.codes} active={activeCodes} kinds={d.kinds} forms={forms} onToggle={toggleCode} />
          {evident.length > 0 && <EvidentLines lines={evident} />}
          <div className="actions">
            <CopyButton label="Ziffern kopieren" text={evidentText(evident)} />
            <CopyButton label="Nur Ziffern" text={evidentText(numbers)} />
          </div>
        </section>

        <TransferPanel transcript={d.transcript} codes={evident} onUnauthorized={d.sessionExpired} />
      </main>
    </div>
  );
}
