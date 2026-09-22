// Einstieg: Route wählen; die Diktat-Ansicht verlangt eine Sitzung,
// Rezeption (/transfer) und Gerätetest (/check) sind ohne Anmeldung nutzbar.
import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { useRoute } from "./router";
import { Check } from "./views/Check";
import { Diktat } from "./views/Diktat";
import { Login } from "./views/Login";
import { Rezeption } from "./views/Rezeption";

type Session = "prüfe" | "angemeldet" | "abgemeldet" | "server-weg";

export function App() {
  const route = useRoute();
  const [session, setSession] = useState<Session>("prüfe");

  useEffect(() => {
    if (route !== "diktat") return;
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
  }, [route]);

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
      <main className="page narrow">
        <h1>MedVox</h1>
        <p role="alert" className="error">
          Server nicht erreichbar – WLAN und Praxis-Mac prüfen.
        </p>
        <p>
          <button type="button" className="btn" onClick={() => window.location.reload()}>
            Erneut versuchen
          </button>{" "}
          <a href="/check">Gerätetest</a>
        </p>
      </main>
    );
  }
  if (session === "abgemeldet") return <Login onLogin={() => setSession("angemeldet")} />;
  return <Diktat onLogout={() => setSession("abgemeldet")} />;
}
