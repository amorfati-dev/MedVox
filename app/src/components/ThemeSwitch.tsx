// Schalter für das Farbschema (Röntgenraum): Auto → Hell → Dunkel.
import { useTheme } from "../hooks/useTheme";
import { THEME_LABEL } from "../theme";
import { Icon } from "./Icon";

const ICON = { auto: "auto", hell: "sun", dunkel: "moon" } as const;

export function ThemeSwitch() {
  const [mode, cycle] = useTheme();
  return (
    <button
      type="button"
      className="btn btn-icon theme-switch"
      onClick={cycle}
      aria-label={`Farbschema: ${THEME_LABEL[mode]} – antippen zum Wechseln`}
      title={`Farbschema: ${THEME_LABEL[mode]}`}
    >
      <Icon name={ICON[mode]} />
      <span className="theme-label">{THEME_LABEL[mode]}</span>
    </button>
  );
}
