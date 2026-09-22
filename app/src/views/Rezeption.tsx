// Rezeptions-Ansicht (/transfer): Kurzcode eingeben, Text und Ziffern abholen.
import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, CODE_LENGTH, joinCodes, normalizeCode, type TransferData } from "../api";
import { CopyButton } from "../components/CopyButton";

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

  const both = data ? `${data.transcript}\n\nZiffern: ${joinCodes(data.codes)}` : "";

  return (
    <main className="page narrow">
      <header className="topbar">
        <h1>MedVox · Rezeption</h1>
        <nav>
          <a href="/">Diktat</a>
        </nav>
      </header>
      <form onSubmit={submit} className="card">
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
        <button type="submit" className="btn btn-primary" disabled={busy || code.length !== CODE_LENGTH}>
          {busy ? "Hole …" : "Abrufen"}
        </button>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </form>
      {data && (
        <section className="card">
          <h2>Diktat</h2>
          <p className="transcript">{data.transcript || <span className="muted">(leer)</span>}</p>
          <h2>Ziffern</h2>
          <p className="codes-line">{data.codes.length ? joinCodes(data.codes) : <span className="muted">keine</span>}</p>
          <div className="actions">
            <CopyButton label="Text kopieren" text={data.transcript} primary />
            <CopyButton label="Ziffern kopieren" text={joinCodes(data.codes)} />
            <CopyButton label="Beides kopieren" text={both} />
          </div>
        </section>
      )}
    </main>
  );
}
