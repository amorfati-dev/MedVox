// „An Rezeption“: legt einen Kurzcode für Transkript und Evident-Zeilen an.
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type TransferCreated } from "../api";

export type Transfer = {
  busy: boolean;
  result: TransferCreated | null;
  error: string | null;
  send: () => Promise<void>;
};

export function useTransfer(transcript: string, codes: string[], onUnauthorized: () => void): Transfer {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TransferCreated | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Ein Kurzcode gehört genau zu dem Inhalt, mit dem er erzeugt wurde; ändert
  // sich der Inhalt, gelten auch verspätete Antworten der alten Anfrage nicht mehr.
  const version = useRef(0);
  useEffect(() => {
    version.current += 1;
    setResult(null);
    setError(null);
  }, [transcript, codes]);

  const send = async () => {
    const sent = version.current;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createTransfer(transcript, codes);
      if (sent !== version.current) return;
      setResult(created);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized();
        return;
      }
      if (sent !== version.current) return;
      setError(e instanceof ApiError ? e.message : "Übergabe fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  return { busy, result, error, send };
}
