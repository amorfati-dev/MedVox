/**
 * Detects whether the current device is a tablet (iPad, large touch screen).
 * Returns true for touch devices with a minimum side of at least 768 px.
 * The result is stable for the lifetime of the page – device type does not change.
 */
export function useIsTablet(): boolean {
  return (
    navigator.maxTouchPoints > 0 &&
    Math.min(screen.width, screen.height) >= 768
  );
}
