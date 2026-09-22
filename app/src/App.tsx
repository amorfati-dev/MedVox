import { useEffect, useState } from "react";

type Health = { status: string; whisper: string };

type HealthState =
  | { kind: "lade" }
  | { kind: "ok"; health: Health }
  | { kind: "fehler"; meldung: string };

export function App() {
  const [state, setState] = useState<HealthState>({ kind: "lade" });

  useEffect(() => {
    let aktiv = true;
    fetch("/api/v1/health")
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return (await res.json()) as Health;
      })
      .then((health) => aktiv && setState({ kind: "ok", health }))
      .catch((e: unknown) => {
        if (aktiv) setState({ kind: "fehler", meldung: String(e) });
      });
    return () => {
      aktiv = false;
    };
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "1.5rem" }}>
      <h1>MedVox</h1>
      <p>Lokale Diktat-Transkription für die Praxis.</p>
      <h2>Server-Status</h2>
      {state.kind === "lade" && <p>Prüfe Server …</p>}
      {state.kind === "ok" && (
        <ul>
          <li>Server: {state.health.status}</li>
          <li>Whisper: {state.health.whisper}</li>
        </ul>
      )}
      {state.kind === "fehler" && (
        <p role="alert">Server nicht erreichbar ({state.meldung}).</p>
      )}
    </main>
  );
}
