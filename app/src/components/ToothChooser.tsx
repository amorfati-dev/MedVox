// Zahn mit zwei Tipps wählen (Quadrant, Zahn) oder „Ohne Zahn“ – für Ziffern ohne Zahn oder an einem
// Zahn ohne eigenen Block (Katalog-Blatt). Tasten wie das Tastenfeld der Patientenauswahl (≥ 64 px).
import { useState } from "react";

type Props = { onChoose: (tooth: number | null) => void };

// FDI: 1–4 bleibende Zähne (je 8), 5–8 Milchzähne (je 5)
const QUADRANTS: { q: number; label: string }[] = [
  { q: 1, label: "oben rechts" },
  { q: 2, label: "oben links" },
  { q: 4, label: "unten rechts" },
  { q: 3, label: "unten links" },
  { q: 5, label: "Milchzahn oben rechts" },
  { q: 6, label: "Milchzahn oben links" },
  { q: 8, label: "Milchzahn unten rechts" },
  { q: 7, label: "Milchzahn unten links" },
];

export function ToothChooser({ onChoose }: Props) {
  const [quadrant, setQuadrant] = useState<number | null>(null);
  if (quadrant === null) {
    return (
      <div className="keypad-box">
        <p className="cat-note">Erst den Quadranten, dann den Zahn antippen.</p>
        <button type="button" className="btn btn-block" onClick={() => onChoose(null)}>
          Ohne Zahn – in Evident manuell eintragen
        </button>
        <div className="keypad keypad-2">
          {QUADRANTS.map(({ q, label }) => (
            <button key={q} type="button" className="btn key" aria-label={`Quadrant ${q}, ${label}`} onClick={() => setQuadrant(q)}>
              {q}
              <small>{label}</small>
            </button>
          ))}
        </div>
      </div>
    );
  }
  const teeth = Array.from({ length: quadrant <= 4 ? 8 : 5 }, (_, i) => quadrant * 10 + i + 1);
  return (
    <div className="keypad-box">
      <p className="cat-note">Quadrant {quadrant}: Zahn antippen.</p>
      <div className="keypad">
        {teeth.map((t) => (
          <button key={t} type="button" className="btn key" aria-label={`Zahn ${t}`} onClick={() => onChoose(t)}>
            {t}
          </button>
        ))}
      </div>
      <button type="button" className="btn btn-quiet btn-block" onClick={() => setQuadrant(null)}>
        Anderer Quadrant
      </button>
    </div>
  );
}
