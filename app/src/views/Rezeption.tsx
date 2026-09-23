// Rezeptions-Ansicht (/transfer): Kurzcode eingeben, Text und Ziffern abholen – ohne Anmeldung.
// Am PC zwei Spalten: links der Code, rechts das Diktat mit Patiententyp, Evident-Zeilen und
// einer kleinen Tabelle für Zuzahlung und Kassenanteil (nur Anzeige, kopiert wird wie bisher).
import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  CODE_LENGTH,
  evidentText,
  normalizeCode,
  splitBlocks,
  type TransferData,
} from "../api";
import { CopayTable } from "../components/CopayTable";
import { CopyButton } from "../components/CopyButton";
import { EvidentLines } from "../components/EvidentLines";
import { HandoverWarning } from "../components/HandoverWarning";
import { PATIENT_LABEL } from "../components/PatientSwitch";
import { ThemeSwitch } from "../components/ThemeSwitch";

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
  // Kassenpatient: Kassenblock, Leerzeile, Privatblock (Privatpositionen immer zuletzt, siehe evidentBlocks).
  const kasse = data?.patient_type === "kasse";
  const positions = data?.positions ?? [];
  const allPrivate = positions.length > 0 && positions.every((p) => p.kind === "goz" || p.kind === "zuzahlung");
  const blocks = splitBlocks(data?.codes ?? [], allPrivate);

  return (
    <main className="page wide rezeption">
      <header className="topbar">
        <h1>MedVox · Rezeption</h1>
        <nav>
          <ThemeSwitch />
          <a className="btn" href="/patienten">
            Patienten
          </a>
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
            <HandoverWarning earlier={data.earlier ?? []} current={data.codes} />
            <p className="transcript">{data.transcript || <span className="muted">(leer)</span>}</p>
            <h2>Ziffern für Evident</h2>
            <EvidentLines blocks={blocks} labelled={kasse} />
            <CopayTable positions={positions} />
            <div className="actions">
              <CopyButton label="Text kopieren" text={data.transcript} primary />
              <CopyButton label="Ziffern kopieren" text={codes} />
              <CopyButton label="Beides kopieren" text={both} />
            </div>
            {kasse && blocks.kasse.length > 0 && blocks.privat.length > 0 && (
              <div className="actions">
                <CopyButton label="Kassenleistungen kopieren" text={evidentText(blocks.kasse)} />
                <CopyButton label="Privatleistungen kopieren" text={evidentText(blocks.privat)} />
              </div>
            )}
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
