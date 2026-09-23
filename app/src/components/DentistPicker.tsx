// „Wer diktiert?“: ein Tipp auf einen der aktiven Behandler. Gilt auf diesem iPad ab dem nächsten
// Diktat, bis jemand wechselt – keine Anmeldung, das Praxis-Passwort bleibt die einzige Schranke.
// Im Büro dieselbe Auswahl, um einem Diktat ohne Behandler seinen Behandler nachzutragen.
import { useEffect } from "react";
import { offerNone, type Dentist } from "../dentists";
import { Icon } from "./Icon";

type Props = {
  active: Dentist[] | null; // null = Liste noch nicht geladen
  current: number | null; // bisher am Gerät gewählt (hervorgehoben)
  error: string | null;
  onChoose: (id: number | null) => void; // null = ohne Behandler diktieren (nur bei leerer Liste)
  onClose: () => void;
  title?: string;
  hint?: string;
};

export function DentistPicker({
  active,
  current,
  error,
  onChoose,
  onClose,
  title = "Wer diktiert?",
  hint = "Gilt auf diesem iPad ab dem nächsten Diktat, bis jemand wechselt.",
}: Props) {
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => ev.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="picker-backdrop">
      <section className="picker dentist-picker" role="dialog" aria-modal="true" aria-labelledby="dentist-title">
        <header className="picker-head">
          <h2 id="dentist-title">{title}</h2>
          <button type="button" className="btn btn-icon" aria-label="Schließen" onClick={onClose}>
            <Icon name="x" />
          </button>
        </header>
        <p className="muted">{hint}</p>
        {error && <p className="error small">{error}</p>}
        {active === null ? (
          <p className="muted">Lade Behandlerliste …</p>
        ) : active.length === 0 ? (
          <p className="muted">Noch keine Behandler in der Liste – unten „Liste bearbeiten“.</p>
        ) : (
          <ul className="dentist-grid">
            {active.map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  className={d.id === current ? "btn btn-block pick pick-on" : "btn btn-block pick"}
                  aria-pressed={d.id === current}
                  onClick={() => onChoose(d.id)}
                >
                  <span className="dentist-pick">{d.name}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="actions dentist-more">
          {offerNone(active) && (
            <button type="button" className="btn btn-quiet" onClick={() => onChoose(null)}>
              Ohne Behandler diktieren
            </button>
          )}
          <a className="btn btn-quiet" href="/behandler">
            Liste bearbeiten
          </a>
        </div>
      </section>
    </div>
  );
}
