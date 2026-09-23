// „An Rezeption“: legt einen Kurzcode für Transkript und Evident-Zeilen an.
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type HandoverLink, type TransferCreated, type TransferDetails } from "../api";

export type Transfer = {
  busy: boolean;
  result: TransferCreated | null;
  error: string | null;
  // `link`: gespeichertes Diktat, das der Abruf schließt; `dentist`: sein Behandler (für die Rezeption)
  send: (link: HandoverLink | null, dentist?: number | null) => Promise<void>;
};

// `details`: Patiententyp und Art je Position, nur zur Anzeige an der Rezeption (E6).
export function useTransfer(
  transcript: string,
  codes: string[],
  details: TransferDetails | null,
  onUnauthorized: () => void,
): Transfer {
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
  }, [transcript, codes, details]);

  const send = async (link: HandoverLink | null, dentist?: number | null) => {
    const sent = version.current;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createTransfer(transcript, codes, details ?? undefined, link, dentist);
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
