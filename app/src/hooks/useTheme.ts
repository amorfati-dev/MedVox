// Farbschema-Schalter: Auto/Hell/Dunkel pro Gerät (localStorage), sofort wirksam.
import { useCallback, useState } from "react";
import { applyTheme, loadTheme, nextTheme, THEME_KEY, type ThemeMode } from "../theme";

export function useTheme(): [ThemeMode, () => void] {
  const [mode, setMode] = useState<ThemeMode>(loadTheme);
  const cycle = useCallback(() => {
    setMode((prev) => {
      const next = nextTheme(prev);
      applyTheme(next);
      try {
        window.localStorage.setItem(THEME_KEY, next);
      } catch {
        /* nicht speicherbar: gilt nur bis zum Neuladen */
      }
      return next;
    });
  }, []);
  return [mode, cycle];
}
