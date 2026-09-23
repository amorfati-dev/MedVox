// Eigene Strich-Symbole (24er Raster, Farbe vom Text) statt eines Icon-Pakets.
// Symbole sind Beiwerk: jedes steht neben einem Wort und ist für Screenreader verborgen.
export type IconName =
  | "mic"
  | "stop"
  | "check"
  | "pause"
  | "x"
  | "warn"
  | "info"
  | "calendar"
  | "moon"
  | "sun"
  | "auto"
  | "more"
  | "copy"
  | "send"
  | "spinner"
  | "plus"
  | "user"
  | "badge";

const PATHS: Record<IconName, string> = {
  mic: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3M8 21h8",
  stop: "M6 6h12v12H6z",
  check: "M4 12.5l5 5L20 6.5",
  pause: "M8 5v14M16 5v14",
  x: "M6 6l12 12M18 6L6 18",
  warn: "M12 3.5L2.5 20h19L12 3.5zM12 10v4.5M12 17.2v.3",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v6M12 7.5v.3",
  calendar: "M4 6h16v14H4zM4 10h16M8 3v5M16 3v5",
  moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  sun: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  auto: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 3v18",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  copy: "M9 9h11v11H9zM5 15H4V4h11v1",
  send: "M4 12l16-8-6 16-2.5-6.5L4 12z",
  spinner: "M12 3a9 9 0 1 0 9 9",
  plus: "M12 5v14M5 12h14",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
  badge: "M4 5h16v14H4zM9 12.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6 16.5a3 3 0 0 1 6 0M14.5 10h3.5M14.5 13.5h3",
};

type Props = { name: IconName; className?: string };

export function Icon({ name, className }: Props) {
  return (
    <svg
      className={["icon", name === "spinner" ? "icon-spin" : "", className ?? ""].filter(Boolean).join(" ")}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={name === "more" ? 4 : 2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
