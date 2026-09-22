// In die Zwischenablage kopieren; auf iPad/Safari nur aus einer Nutzeraktion heraus.
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
