// Behandlerliste pflegen (/behandler): Name wie angezeigt („Dr. Hartmann“), optional die Evident-/
// BEMA-Behandlernummer, aktiv oder nicht. Jede angemeldete Person darf das – es ist nur Zuordnung,
// keine Anmeldung und keine Rechte. Inaktive erscheinen nicht mehr zur Auswahl am iPad; gelöscht
// wird nie, damit alte Diktate ihren Behandler behalten.
import { useEffect, useState, type FormEvent } from "react";
import { ApiError } from "../api";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { dentistApi, type Dentist, type DentistChange } from "../dentists";

type Props = { onLogout: () => void };

export function Behandler({ onLogout }: Props) {
  const [roster, setRoster] = useState<Dentist[] | null>(null);
  const [drafts, setDrafts] = useState<Record<number, { name: string; practitioner_id: string }>>({});
  const [name, setName] = useState("");
  const [number, setNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Eine Aktion ausführen, danach die Liste neu laden; 401 führt zur Anmeldung.
  const act = async (work: () => Promise<string | null>) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const done = await work();
      const list = await dentistApi.list();
      setRoster(list.dentists);
      setDrafts({});
      setMessage(done);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) onLogout();
      else setError(e instanceof ApiError ? e.message : "Aktion fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void act(async () => null);
  }, []);

  const add = (ev: FormEvent) => {
    ev.preventDefault();
    void act(async () => {
      const created = await dentistApi.add(name.trim(), number.trim() || null);
      setName("");
      setNumber("");
      return `${created.name} ist angelegt und steht auf den iPads zur Auswahl.`;
    });
  };

  const change = (d: Dentist, patch: DentistChange, done: string) =>
    void act(async () => {
      await dentistApi.update(d.id, patch);
      return done;
    });
  const draft = (d: Dentist) => drafts[d.id] ?? { name: d.name, practitioner_id: d.practitioner_id ?? "" };
  const edit = (d: Dentist, field: "name" | "practitioner_id", value: string) =>
    setDrafts((all) => ({ ...all, [d.id]: { ...draft(d), [field]: value } }));

  return (
    <main className="page wide rezeption behandler">
      <header className="topbar">
        <h1>MedVox · Behandler</h1>
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
      <p className="muted">
        Wer diktiert, wählt am iPad seinen Namen – nur zur Zuordnung für Abrechnung und Nachvollziehbarkeit. Alle sehen
        weiterhin alle Patienten.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      <section className="card">
        <h2>Behandler</h2>
        {roster === null && <p className="muted">Lade …</p>}
        {roster?.map((d) => {
          const v = draft(d);
          const dirty = v.name.trim() !== d.name || (v.practitioner_id.trim() || null) !== d.practitioner_id;
          return (
            <div key={d.id} className={d.active ? "roster-row" : "roster-row roster-inactive"}>
              <div>
                <label htmlFor={`name-${d.id}`}>Name{d.active ? "" : " (inaktiv)"}</label>
                <input id={`name-${d.id}`} className="roster-name" value={v.name} maxLength={60} onChange={(ev) => edit(d, "name", ev.target.value)} />
              </div>
              <div>
                <label htmlFor={`nr-${d.id}`}>Behandlernummer (optional)</label>
                <input id={`nr-${d.id}`} value={v.practitioner_id} maxLength={20} onChange={(ev) => edit(d, "practitioner_id", ev.target.value)} />
              </div>
              <div className="roster-actions">
                {dirty && (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || !v.name.trim()}
                    onClick={() => change(d, { name: v.name.trim(), practitioner_id: v.practitioner_id.trim() || null }, "Gespeichert.")}
                  >
                    Speichern
                  </button>
                )}
                <button
                  type="button"
                  className="btn"
                  disabled={busy}
                  onClick={() =>
                    change(
                      d,
                      { active: !d.active },
                      d.active ? `${d.name} erscheint nicht mehr zur Auswahl; alte Diktate behalten den Namen.` : `${d.name} ist wieder aktiv.`,
                    )
                  }
                >
                  {d.active ? "Inaktiv setzen" : "Wieder aktiv"}
                </button>
              </div>
            </div>
          );
        })}
      </section>
      <form className="card" onSubmit={add}>
        <h2>Behandler hinzufügen</h2>
        <label htmlFor="new-name">Name, wie er angezeigt wird</label>
        <input id="new-name" value={name} maxLength={60} placeholder="z. B. Dr. Muster" onChange={(ev) => setName(ev.target.value)} />
        <label htmlFor="new-nr">Evident-/BEMA-Behandlernummer (optional)</label>
        <input id="new-nr" value={number} maxLength={20} onChange={(ev) => setNumber(ev.target.value)} />
        <button type="submit" className="btn btn-primary" disabled={busy || !name.trim()}>
          Hinzufügen
        </button>
      </form>
    </main>
  );
}
