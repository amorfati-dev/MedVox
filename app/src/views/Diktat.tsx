// Diktat-Ansicht: großer Aufnahmeknopf, Pegel und Countdown, Transkript in
// gut lesbarer Schrift, Ziffern-Chips, Kopieren und Übergabe an die Rezeption.
import { useMemo, useState } from "react";
import { api, joinCodes } from "../api";
import { CodeChips } from "../components/CodeChips";
import { CopyButton } from "../components/CopyButton";
import { TransferPanel } from "../components/TransferPanel";
import { MAX_SECONDS, useDictation } from "../hooks/useDictation";
import { Login } from "./Login";

type Props = { onLogout: () => void };

export function Diktat({ onLogout }: Props) {
  const d = useDictation();
  // Abgewählte Ziffern merken; neu vorgeschlagene gelten damit automatisch als gewählt.
  const [deselected, setDeselected] = useState<ReadonlySet<string>>(() => new Set());
  const activeCodes = useMemo(() => d.codes.filter((c) => !deselected.has(c)), [d.codes, deselected]);
  const recording = d.phase === "aufnahme";
  const sending = d.phase === "sende";
  const resumable = d.phase === "fortsetzbar";
  const [transferUnauthorized, setTransferUnauthorized] = useState(false);

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      onLogout();
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

  // Sitzung abgelaufen: Anmeldung anzeigen, Diktat bleibt im Speicher.
  if (d.sessionLost || transferUnauthorized) {
    return (
      <Login
        notice="Sitzung abgelaufen – bitte erneut anmelden. Das aktuelle Diktat bleibt erhalten."
        onLogin={() => {
          setTransferUnauthorized(false);
          d.relogin();
        }}
      />
    );
  }

  return (
    <main className="page">
      <header className="topbar">
        <h1>MedVox</h1>
        <nav>
          <a href="/check">Gerätetest</a>
          <button type="button" className="link" onClick={logout}>
            Abmelden
          </button>
        </nav>
      </header>

      <section className="card recorder">
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
                ? "Zeitlimit erreicht – „Weiter“ hängt den nächsten Abschnitt an, „Neues Diktat“ beginnt neu."
                : `Bereit · maximal ${MAX_SECONDS} s pro Abschnitt`}
        </p>
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
      </section>

      <section className="card">
        <h2>Transkript</h2>
        <p className="transcript" aria-live="polite">
          {d.transcript || <span className="muted">Noch nichts diktiert.</span>}
        </p>
        {d.lastLatency !== null && <p className="muted">Transkription in {d.lastLatency.toFixed(1)} s.</p>}
        <div className="actions">
          <CopyButton label="Text kopieren" text={d.transcript} primary />
          <button type="button" className="btn" disabled={!d.transcript} onClick={clear}>
            Verwerfen
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Ziffern</h2>
        <CodeChips all={d.codes} active={activeCodes} onToggle={toggleCode} />
        <div className="actions">
          <CopyButton label="Ziffern kopieren" text={joinCodes(activeCodes)} />
        </div>
      </section>

      <TransferPanel transcript={d.transcript} codes={activeCodes} onUnauthorized={() => setTransferUnauthorized(true)} />
    </main>
  );
}
