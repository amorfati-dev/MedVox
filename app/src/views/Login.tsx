// Anmeldung: ein Praxis-Passwort, Sitzung per HttpOnly-Cookie.
import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api";

type Props = { onLogin: () => void; notice?: string };

export function Login({ onLogin, notice }: Props) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(password);
      setPassword("");
      onLogin();
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 401 ? "Passwort falsch." : e instanceof ApiError ? e.message : "Anmeldung fehlgeschlagen.";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="page narrow ipad">
      <h1>MedVox</h1>
      <p className="muted">Lokale Diktat-Transkription für die Praxis.</p>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      <form onSubmit={submit} className="card">
        <label htmlFor="password">Praxis-Passwort</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(ev) => setPassword(ev.target.value)}
          required
          autoFocus
        />
        <button type="submit" className="btn btn-primary" disabled={busy || !password}>
          {busy ? "Anmelden …" : "Anmelden"}
        </button>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </form>
      <p className="muted">
        <a href="/check">Gerätetest</a> · <a href="/transfer">Rezeption</a>
      </p>
    </main>
  );
}
