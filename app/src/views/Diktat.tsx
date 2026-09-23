// Diktat-Ansicht: Schalter Kasse/Privat, großer Aufnahmeknopf, Pegel und Countdown,
// Transkript in gut lesbarer Schrift, Ziffern-Chips, Kopieren und Übergabe an die Rezeption.
import { useMemo, useState } from "react";
import { api, ApiError, evidentLines, evidentOf, evidentText } from "../api";
import { CodeChips } from "../components/CodeChips";
import { CopyButton } from "../components/CopyButton";
import { EvidentLines } from "../components/EvidentLines";
import { PATIENT_LABEL, PatientSwitch } from "../components/PatientSwitch";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { TransferPanel } from "../components/TransferPanel";
import { MAX_SECONDS, useDictation } from "../hooks/useDictation";
import { usePatientType } from "../hooks/usePatientType";
import { Login } from "./Login";

type Props = { onLogout: () => void };

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

  return (
    <main className="page ipad">
      <header className="topbar">
        <h1>MedVox</h1>
        <nav>
          <ThemeSwitch />
          <a href="/check">Gerätetest</a>
          <button type="button" className="link" onClick={logout}>
            Abmelden
          </button>
        </nav>
      </header>

      <section className="card recorder">
        <PatientSwitch value={patientType} onChange={setPatientType} disabled={recording || sending || resumable} />
        {(recording || sending || resumable) && (
          <p className="muted switch-hint">Der Patiententyp gilt für das ganze laufende Diktat.</p>
        )}
        {!d.supported && (
          <p role="alert" className="error">
            Dieser Browser unterstützt keine Audioaufnahme. Bitte Safari auf dem iPad verwenden.
          </p>
        )}
        <button
          type="button"
          className={recording ? "record record-active" : "record"}
          disabled={!d.supported || sending}
          onClick={recording ? d.stop : resumable ? d.resume : startNew}
          aria-label={recording ? "Aufnahme beenden" : resumable ? "Diktat fortsetzen" : "Aufnahme starten"}
        >
          {sending ? "Transkribiere …" : recording ? "Stopp" : resumable ? "Weiter" : "Aufnehmen"}
        </button>
        <div className="meter" aria-hidden="true">
          <div className="meter-fill" style={{ width: `${Math.round(d.level * 100)}%` }} />
        </div>
        <p className={recording && d.remaining <= 10 ? "countdown warn" : "countdown"} aria-live="polite">
          {recording
            ? `${d.seconds} s · noch ${d.remaining} s`
            : sending
              ? "Audio wird auf dem Praxis-Mac transkribiert …"
              : resumable
                ? d.discardable
                  ? "Dieser Abschnitt wird vom Server abgelehnt – verwerfen, damit die übrigen Abschnitte übertragen werden."
                  : d.waiting > 0
                    ? `Unterbrochen – „Erneut senden“ überträgt ${d.waiting === 1 ? "den wartenden Abschnitt" : `die ${d.waiting} wartenden Abschnitte`}, „Weiter“ überträgt und nimmt weiter auf.`
                    : "Unterbrochen – „Weiter“ hängt den nächsten Abschnitt an, „Neues Diktat“ beginnt neu."
                : `Bereit · maximal ${MAX_SECONDS} s pro Abschnitt`}
        </p>
        {d.retryable && (
          <button type="button" className="btn" onClick={d.retry}>
            Erneut senden
          </button>
        )}
        {d.discardable && (
          <button type="button" className="btn" onClick={d.dropSegment}>
            Diesen Abschnitt verwerfen
          </button>
        )}
        {resumable && (
          <button type="button" className="btn" onClick={clear}>
            Neues Diktat (nächster Patient)
          </button>
        )}
        {recording && (
          <button type="button" className="btn" onClick={d.next}>
            Weiter (Abschnitt hochladen, neuen starten)
          </button>
        )}
        {recording && d.uploading && <p className="muted">Vorheriger Abschnitt wird transkribiert …</p>}
        {d.error && (
          <p role="alert" className="error">
            {d.error}
          </p>
        )}
        {logoutError && (
          <p role="alert" className="error">
            {logoutError}
          </p>
        )}
      </section>

      <section className="card">
        <h2>Transkript</h2>
        <p className="transcript" aria-live="polite">
          {d.transcript || <span className="muted">Noch nichts diktiert.</span>}
        </p>
        {d.lastLatency !== null && <p className="muted">Transkription in {d.lastLatency.toFixed(1)} s.</p>}
        <div className="actions">
          <CopyButton label="Text kopieren" text={d.transcript} primary />
          <button type="button" className="btn" disabled={!d.transcript || recording || d.uploading} onClick={clear}>
            Verwerfen
          </button>
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
  );
}
