// Rezeptions-Ansicht (/transfer): Kurzcode eingeben, Text und Ziffern abholen – ohne Anmeldung.
// Am PC zwei Spalten: links der Code, rechts das Diktat mit Patiententyp, Evident-Zeilen und
// einer kleinen Tabelle für Zuzahlung und Kassenanteil (nur Anzeige, kopiert wird wie bisher).
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, CODE_LENGTH, evidentText, normalizeCode, type PositionKind, type TransferData } from "../api";
import { CopyButton } from "../components/CopyButton";
import { EvidentLines } from "../components/EvidentLines";
import { PATIENT_LABEL } from "../components/PatientSwitch";
import { ThemeSwitch } from "../components/ThemeSwitch";

const KIND_LABEL: Partial<Record<PositionKind, string>> = {
  kassenanteil: "Kassenanteil – Kasse zahlt",
  zuzahlung: "Zuzahlung – Patient zahlt",
};

export function Rezeption() {
  const [code, setCode] = useState(() => normalizeCode(new URLSearchParams(window.location.search).get("code") ?? ""));
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<TransferData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lookup = async (value: string) => {
    if (value.length !== CODE_LENGTH) return;
    setBusy(true);
    setError(null);
    setData(null);
    try {
      setData(await api.getTransfer(value));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setError("Kein Diktat unter diesem Code – vielleicht vertippt oder älter als 15 Minuten?");
      } else {
        setError(e instanceof ApiError ? e.message : "Abruf fehlgeschlagen.");
      }
    } finally {
      setBusy(false);
    }
  };

  // Code aus dem QR-Link (?code=…) direkt abrufen.
  useEffect(() => {
    if (code.length === CODE_LENGTH) void lookup(code);
  }, []);

  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    void lookup(code);
  };

  // `codes` sind die Evident-Zeilen vom iPad ("36,Ä925a,l1,13a"), eine je Zahn, siehe evidentLines.
  const codes = data ? evidentText(data.codes) : "";
  const both = data ? `${data.transcript}\n\nZiffern:\n${codes}` : "";
  const extra = (data?.positions ?? []).filter((p) => KIND_LABEL[p.kind]);

  return (
    <main className="page wide rezeption">
      <header className="topbar">
        <h1>MedVox · Rezeption</h1>
        <nav>
          <ThemeSwitch />
          <a className="btn" href="/">
            Diktat
          </a>
        </nav>
      </header>
      <div className="rezeption-grid">
        <form onSubmit={submit} className="card code-card">
          <label htmlFor="code">Kurzcode vom iPad</label>
          <input
            id="code"
            className="code-input"
            inputMode="text"
            autoCapitalize="characters"
            autoComplete="off"
            spellCheck={false}
            maxLength={CODE_LENGTH}
            value={code}
            onChange={(ev) => setCode(normalizeCode(ev.target.value))}
            placeholder="ABC234"
            autoFocus
          />
          <button type="submit" className="btn btn-primary btn-block" disabled={busy || code.length !== CODE_LENGTH}>
            {busy ? "Hole …" : "Abrufen"}
          </button>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <p className="muted small">Der Code gilt 15 Minuten und kann mehrfach abgerufen werden.</p>
        </form>

        {data ? (
          <section className="card">
            <div className="section-head">
              <h2>Diktat</h2>
              {data.patient_type && (
                <span className={`badge badge-${data.patient_type}`}>{PATIENT_LABEL[data.patient_type]}</span>
              )}
            </div>
            <p className="transcript">{data.transcript || <span className="muted">(leer)</span>}</p>
            <h2>Ziffern für Evident</h2>
            <EvidentLines lines={data.codes} />
            {extra.length > 0 && (
              <table className="copay-table">
                <caption>Mehrkosten – Vereinbarung mit dem Patienten nötig</caption>
                <thead>
                  <tr>
                    <th scope="col">Zahn</th>
                    <th scope="col">Ziffer</th>
                    <th scope="col">Art</th>
                  </tr>
                </thead>
                <tbody>
                  {extra.map((p) => (
                    <tr key={`${p.tooth}-${p.code}`} className={`copay-${p.kind}`}>
                      <td>{p.tooth ?? "ohne Zahn"}</td>
                      <td className="mono">{p.code}</td>
                      <td>{KIND_LABEL[p.kind]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="actions">
              <CopyButton label="Text kopieren" text={data.transcript} primary />
              <CopyButton label="Ziffern kopieren" text={codes} />
              <CopyButton label="Beides kopieren" text={both} />
            </div>
            <p className="muted small">Danach in Evident mit Strg+V einfügen.</p>
          </section>
        ) : (
          <section className="card placeholder">
            <p className="muted">Code eingeben oder den QR-Code vom iPad scannen – das Diktat erscheint hier.</p>
          </section>
        )}
      </div>
    </main>
  );
}
