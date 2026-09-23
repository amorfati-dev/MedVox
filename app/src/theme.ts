// Farbschema je Gerät: „Auto“ folgt dem iPad (hell/dunkel), „Hell“ und „Dunkel“ sind fest.
// Gespeichert im localStorage; wirkt über das Attribut data-theme an <html> (styles/tokens.css).
export type ThemeMode = "auto" | "hell" | "dunkel";

export const THEME_KEY = "medvox.theme";
export const THEME_LABEL: Record<ThemeMode, string> = { auto: "Auto", hell: "Hell", dunkel: "Dunkel" };
const ORDER: ThemeMode[] = ["auto", "hell", "dunkel"];

// Unbekannte oder fehlende Werte gelten als „Auto“.
export function parseTheme(raw: string | null): ThemeMode {
  return raw === "hell" || raw === "dunkel" ? raw : "auto";
}

// Reihenfolge beim Antippen: Auto → Hell → Dunkel → Auto.
export function nextTheme(mode: ThemeMode): ThemeMode {
  return ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length];
}

// Wert für data-theme; null = Attribut entfernen (Gerät entscheidet).
export function themeAttr(mode: ThemeMode): "light" | "dark" | null {
  return mode === "hell" ? "light" : mode === "dunkel" ? "dark" : null;
}

export function loadTheme(): ThemeMode {
  try {
    return parseTheme(window.localStorage.getItem(THEME_KEY));
  } catch {
    return "auto"; // Speicher gesperrt (privates Surfen)
  }
}

export function applyTheme(mode: ThemeMode): void {
  const attr = themeAttr(mode);
  if (attr) document.documentElement.dataset.theme = attr;
  else delete document.documentElement.dataset.theme;
}
