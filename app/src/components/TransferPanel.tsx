// "An Rezeption senden": legt einen Kurzcode an und zeigt ihn groß plus als QR-Code.
import { useEffect, useState } from "react";
import { api, ApiError, type TransferCreated } from "../api";
import { QrCanvas } from "./QrCanvas";

type Props = { transcript: string; codes: string[]; onUnauthorized: () => void };

function formatTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

export function TransferPanel({ transcript, codes, onUnauthorized }: Props) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TransferCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Ein Kurzcode gehört genau zu dem Inhalt, mit dem er erzeugt wurde.
  useEffect(() => {
    setResult(null);
    setError(null);
  }, [transcript, codes]);

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.createTransfer(transcript, codes));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized();
        return;
      }
      setError(e instanceof ApiError ? e.message : "Übergabe fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  // QR enthält die Rezeptions-URL mit Code, damit auch ein Handy-Scan direkt landet.
  const url = result ? `${window.location.origin}/transfer?code=${result.code}` : "";

  return (
    <section className="card">
      <button type="button" className="btn btn-primary" disabled={busy || !transcript} onClick={send}>
        {busy ? "Sende …" : "An Rezeption senden"}
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {result && (
        <div className="transfer-result">
          <p className="muted">Code an der Rezeption eingeben (gültig bis {formatTime(result.expires_at)} Uhr):</p>
          <p className="transfer-code" aria-label="Kurzcode">
            {result.code}
          </p>
          <QrCanvas text={url} label={`QR-Code für Kurzcode ${result.code}`} />
        </div>
      )}
    </section>
  );
}
