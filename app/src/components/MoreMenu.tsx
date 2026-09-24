// ⋯-Menü in der Kopfzeile: seltene Aktionen (Patientenliste, Behandlerliste, Wörterbuch, Gerätetest, Abmelden) als große Menüzeilen,
// damit sie nicht als kleine Textlinks neben den Handschuh-Tippflächen stehen.
import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

type Props = { onLogout: () => void };

export function MoreMenu({ onLogout }: Props) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const outside = (ev: PointerEvent) => {
      if (!root.current?.contains(ev.target as Node)) setOpen(false);
    };
    const escape = (ev: KeyboardEvent) => ev.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  return (
    <div className="more" ref={root}>
      <button
        type="button"
        className="btn btn-icon"
        aria-label="Weitere Aktionen"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="more" />
      </button>
      {open && (
        <div className="more-menu" role="menu">
          <a className="more-item" role="menuitem" href="/patienten">
            Patientenliste (Büro)
          </a>
          <a className="more-item" role="menuitem" href="/behandler">
            Behandlerliste
          </a>
          <a className="more-item" role="menuitem" href="/woerterbuch">
            Wörterbuch
          </a>
          <a className="more-item" role="menuitem" href="/check">
            Gerätetest
          </a>
          <button
            type="button"
            className="more-item"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
          >
            Abmelden
          </button>
        </div>
      )}
    </div>
  );
}
