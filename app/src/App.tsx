// Einstieg: Route wählen; Diktat, Patientenliste (/patienten, enthält Transkripte) und Behandlerliste
// (/behandler) verlangen eine Sitzung, Rezeption (/transfer) und Gerätetest (/check) sind ohne Anmeldung nutzbar.
import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { routeFromPath } from "./router";
import { Behandler } from "./views/Behandler";
import { Check } from "./views/Check";
import { Diktat } from "./views/Diktat";
import { Login } from "./views/Login";
import { Patienten } from "./views/Patienten";
import { Rezeption } from "./views/Rezeption";

type Session = "prüfe" | "angemeldet" | "abgemeldet" | "server-weg";

export function App() {
  const route = routeFromPath(window.location.pathname);
  const [session, setSession] = useState<Session>("prüfe");
  const needsSession = route === "diktat" || route === "patienten" || route === "behandler";

  useEffect(() => {
    if (!needsSession) return;
    let aktiv = true;
    api
      .session()
      .then(() => aktiv && setSession("angemeldet"))
      .catch((e: unknown) => {
        if (!aktiv) return;
        setSession(e instanceof ApiError && e.status === 401 ? "abgemeldet" : "server-weg");
      });
    return () => {
      aktiv = false;
    };
  }, [needsSession]);

  if (route === "rezeption") return <Rezeption />;
  if (route === "check") return <Check />;

  if (session === "prüfe") {
    return (
      <main className="page narrow">
        <p className="muted">Prüfe Anmeldung …</p>
      </main>
    );
  }
  if (session === "server-weg") {
    return (
      <main className="page narrow ipad">
        <h1>MedVox</h1>
        <p role="alert" className="error">
          Server nicht erreichbar – WLAN und Praxis-Mac prüfen.
        </p>
        <p className="actions">
          <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
            Erneut versuchen
          </button>
          <a className="btn" href="/check">
            Gerätetest
          </a>
        </p>
      </main>
    );
  }
  if (session === "abgemeldet") return <Login onLogin={() => setSession("angemeldet")} />;
  if (route === "patienten") return <Patienten onLogout={() => setSession("abgemeldet")} />;
  if (route === "behandler") return <Behandler onLogout={() => setSession("abgemeldet")} />;
  return <Diktat onLogout={() => setSession("abgemeldet")} />;
}
