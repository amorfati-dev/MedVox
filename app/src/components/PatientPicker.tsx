// Patient wählen: Evident-Nummer über ein großes Tastenfeld (Handschuhe) oder einen offenen Patienten
// aus der Liste antippen. Am PC geht auch die Tastatur (Ziffern, Rücktaste, Eingabe, Esc). Darunter auf
// Wunsch das Kürzel (Initialen) zum Wiederfinden in Evident; leer lässt ein vorhandenes stehen.
import { useEffect, useState } from "react";
import { api, ApiError, type PatientSummary } from "../api";
import { clock, isLabel, LABEL_LETTERS, NUMBER_MAX, normalizeLabel, normalizeNumber, pickable } from "../patients";
import { plural } from "../status";
import { Icon } from "./Icon";

type Props = {
  title: string;
  current: string | null;
  onChoose: (number: string | null, label: string | null) => void; // label: Kürzel, null = keins
  onClose: () => void;
  allowNone?: boolean; // „Ohne Patient weiter“ anbieten (am Stuhl)
};

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"];

export function PatientPicker({ title, current, onChoose, onClose, allowNone }: Props) {
  const [digits, setDigits] = useState("");
  const [label, setLabel] = useState("");
  const [open, setOpen] = useState<PatientSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const initials = normalizeLabel(label);
  const labelOk = isLabel(initials);

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
      const known = open?.find((p) => p.number === digits)?.label ?? null;
      if (digits && labelOk) onChoose(digits, initials || known);
    } else if (key === "⌫") setDigits((d) => d.slice(0, -1));
    else setDigits((d) => normalizeNumber(d + key));
  };

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const typing = ev.target instanceof HTMLInputElement; // im Kürzel-Feld nur Esc und Eingabe
      if (ev.key === "Escape") onClose();
      else if (ev.key === "Enter") press("OK");
      else if (typing) return;
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
            <input
              className="initials-input"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              aria-invalid={!labelOk}
              placeholder="Kürzel (optional), z. B. M.K."
              aria-label="Kürzel des Patienten, optional"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="characters"
              spellCheck={false}
              enterKeyHint="done"
            />
            {!labelOk && (
              <p className="error small" role="alert">
                Nur Initialen, z. B. M.K. – höchstens {LABEL_LETTERS} Buchstaben, keine Namen.
              </p>
            )}
            <div className="keypad">
              {KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={key === "OK" ? "btn btn-primary key" : "btn key"}
                  disabled={((key === "OK" || key === "⌫") && !digits) || (key === "OK" && !labelOk)}
                  aria-label={key === "⌫" ? "Letzte Ziffer löschen" : key === "OK" ? "Nummer übernehmen" : key}
                  onClick={() => press(key)}
                >
                  {key}
                </button>
              ))}
            </div>
            <p className="muted small">
              Patientennummer aus Evident, höchstens {NUMBER_MAX} Ziffern; dazu auf Wunsch nur die Initialen (höchstens {LABEL_LETTERS} Buchstaben, z. B. M.K.) – keine Namen.
            </p>
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
                      onClick={() => onChoose(p.number, p.label ?? null)}
                    >
                      <span className="pick-number">
                        {p.number}
                        {p.label && <span className="initials">{p.label}</span>}
                      </span>
                      <span className="pick-meta">
                        {p.dictations > 0 ? `${plural(p.dictations, "Diktat", "Diktate")} · ${clock(p.updated_at)}` : "noch kein Diktat"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {allowNone && (
              <button type="button" className="btn btn-quiet btn-block" onClick={() => onChoose(null, null)}>
                Ohne Patient weiter – später zuordnen
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
