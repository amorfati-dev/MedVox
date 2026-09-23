// Patient wählen: Evident-Nummer über ein großes Tastenfeld (Handschuhe) oder einen offenen Patienten
// aus der Liste antippen. Am PC geht auch die Tastatur (Ziffern, Rücktaste, Eingabe, Esc).
import { useEffect, useState } from "react";
import { api, ApiError, type PatientSummary } from "../api";
import { clock, NUMBER_MAX, normalizeNumber, pickable } from "../patients";
import { plural } from "../status";
import { Icon } from "./Icon";

type Props = {
  title: string;
  current: string | null;
  onChoose: (number: string | null) => void;
  onClose: () => void;
  allowNone?: boolean; // „Ohne Patient weiter“ anbieten (am Stuhl)
};

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"];

export function PatientPicker({ title, current, onChoose, onClose, allowNone }: Props) {
  const [digits, setDigits] = useState("");
  const [open, setOpen] = useState<PatientSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .listPatients()
      .then((list) => alive && setOpen(pickable(list.patients)))
      .catch((e: unknown) => {
        if (!alive) return;
        setOpen([]);
        setError(e instanceof ApiError ? e.message : "Liste nicht erreichbar.");
      });
    return () => {
      alive = false;
    };
  }, []);

  const press = (key: string) => {
    if (key === "OK") {
      if (digits) onChoose(digits);
    } else if (key === "⌫") setDigits((d) => d.slice(0, -1));
    else setDigits((d) => normalizeNumber(d + key));
  };

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") onClose();
      else if (ev.key === "Enter") press("OK");
      else if (ev.key === "Backspace") press("⌫");
      else if (/^\d$/.test(ev.key)) press(ev.key);
      else return;
      ev.preventDefault();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  });

  return (
    <div className="picker-backdrop">
      <section className="picker" role="dialog" aria-modal="true" aria-label={title}>
        <header className="picker-head">
          <h2>{title}</h2>
          <button type="button" className="btn btn-icon" aria-label="Schließen" onClick={onClose}>
            <Icon name="x" />
          </button>
        </header>
        <div className="picker-body">
          <div className="keypad-box">
            <output className={digits ? "keypad-display" : "keypad-display keypad-empty"} aria-live="polite">
              {digits || "Evident-Nummer"}
            </output>
            <div className="keypad">
              {KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={key === "OK" ? "btn btn-primary key" : "btn key"}
                  disabled={(key === "OK" || key === "⌫") && !digits}
                  aria-label={key === "⌫" ? "Letzte Ziffer löschen" : key === "OK" ? "Nummer übernehmen" : key}
                  onClick={() => press(key)}
                >
                  {key}
                </button>
              ))}
            </div>
            <p className="muted small">Nur die Patientennummer aus Evident, höchstens {NUMBER_MAX} Ziffern – keine Namen.</p>
          </div>
          <div className="picker-list">
            <h3>Offene Patienten</h3>
            {error && <p className="error small">{error}</p>}
            {open === null ? (
              <p className="muted">Lade …</p>
            ) : open.length === 0 ? (
              <p className="muted">Noch keine – Nummer links eingeben.</p>
            ) : (
              <ul>
                {open.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      className={p.number === current ? "btn btn-block pick pick-on" : "btn btn-block pick"}
                      onClick={() => onChoose(p.number)}
                    >
                      <span className="pick-number">{p.number}</span>
                      <span className="pick-meta">
                        {p.dictations > 0 ? `${plural(p.dictations, "Diktat", "Diktate")} · ${clock(p.updated_at)}` : "noch kein Diktat"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {allowNone && (
              <button type="button" className="btn btn-quiet btn-block" onClick={() => onChoose(null)}>
                Ohne Patient weiter – später zuordnen
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
