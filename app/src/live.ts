// Büro: Live-Aktualisierung über Server-Sent Events (`/api/v1/events`, server/medvox/events.py).
// Der Strom trägt nur eine Versionsnummer, nie Inhalte; bei jedem Ereignis lädt die Seite über die
// API neu. Ist der Strom weg, gleicht die Seite wie bisher alle 30 Sekunden ab, bis er wieder steht.

export const EVENTS_URL = "/api/v1/events";
export const POLL_MS = 30_000;
export const GRACE_MS = 5_000; // Neuverbinden des Browsers (retry 3 s) abwarten, bevor der Abgleich einspringt
export const REOPEN_MS = 15_000; // Strom abgewiesen (z. B. 401, Server aus): so lange bis zum nächsten Versuch
// Der Server schickt alle 15 s ein `ping`. Bleibt länger alles still, ist die Verbindung tot, ohne dass
// der Browser es merkt (Proxy hält sie offen, WLAN weg): schließen, abgleichen, neu verbinden.
export const SILENT_MS = 40_000;

export type LiveMode = "live" | "polling";

// Kleine Anzeige neben „Aktualisieren“ im Büro.
export const LIVE_TEXT: Record<LiveMode, { label: string; title: string }> = {
  live: { label: "Live", title: "Neue Diktate erscheinen sofort." },
  polling: {
    label: "Abgleich alle 30 s",
    title: "Live-Verbindung zum Praxis-Mac unterbrochen – die Liste gleicht alle 30 Sekunden ab, bis sie wieder steht.",
  },
};

const CLOSED = 2; // EventSource.CLOSED: der Browser versucht es nicht mehr von selbst

// Das Nötigste von EventSource, damit die Tests ohne Browser auskommen.
export type ChangeSource = {
  readonly readyState: number;
  onopen: ((event: Event) => unknown) | null;
  onerror: ((event: Event) => unknown) | null;
  addEventListener(type: "changed" | "ping", listener: () => void): void;
  close(): void;
};

type TimerId = ReturnType<typeof setTimeout>;
export type Timers = {
  setTimeout(fn: () => void, ms: number): TimerId;
  clearTimeout(id: TimerId): void;
  setInterval(fn: () => void, ms: number): TimerId;
  clearInterval(id: TimerId): void;
};

export type WatchOptions = {
  onChange: () => void;
  onMode: (mode: LiveMode) => void;
  open: ((url: string) => ChangeSource) | null; // null: Browser ohne EventSource, nur Abgleich
  timers?: Timers;
};

/** Beobachtet den Strom; liefert die Abmeldung (Strom schließen, alle Zeitgeber aus). */
export function watchChanges({ onChange, onMode, open, timers = globalThis }: WatchOptions): () => void {
  let source: ChangeSource | null = null;
  let poll: TimerId | null = null;
  let grace: TimerId | null = null;
  let reopen: TimerId | null = null;
  let silent: TimerId | null = null;
  let mode: LiveMode | null = null;

  const setMode = (next: LiveMode) => {
    if (next !== mode) onMode((mode = next));
  };
  const clearGrace = () => {
    if (grace !== null) timers.clearTimeout(grace);
    grace = null;
  };
  // Ohne Strom: sofort einmal abgleichen (Ereignisse können verpasst sein), dann alle 30 Sekunden.
  const fallBack = () => {
    clearGrace();
    if (mode === "polling") return;
    setMode("polling");
    onChange();
    poll = timers.setInterval(onChange, POLL_MS);
  };
  const clearSilent = () => {
    if (silent !== null) timers.clearTimeout(silent);
    silent = null;
  };
  const connect = () => {
    reopen = null;
    if (!open) return fallBack();
    const current = open(EVENTS_URL);
    source = current;
    grace ??= timers.setTimeout(fallBack, GRACE_MS);
    const alive = () => {
      clearSilent();
      silent = timers.setTimeout(() => {
        silent = null;
        current.close();
        fallBack();
        connect();
      }, SILENT_MS);
    };
    alive();
    current.onopen = () => {
      alive();
      clearGrace();
      if (poll !== null) timers.clearInterval(poll);
      poll = null;
      setMode("live"); // der Server schickt gleich die aktuelle Version – das lädt die Liste neu
    };
    current.addEventListener("changed", () => {
      alive();
      onChange();
    });
    current.addEventListener("ping", alive);
    current.onerror = () => {
      if (current.readyState !== CLOSED) {
        grace ??= timers.setTimeout(fallBack, GRACE_MS); // der Browser verbindet sich selbst neu
        return;
      }
      current.close();
      source = null;
      clearSilent();
      fallBack();
      reopen = timers.setTimeout(connect, REOPEN_MS);
    };
  };

  connect();
  return () => {
    source?.close();
    clearGrace();
    clearSilent();
    if (poll !== null) timers.clearInterval(poll);
    if (reopen !== null) timers.clearTimeout(reopen);
  };
}

/** Höchstens ein Abruf gleichzeitig; Aufrufe währenddessen führen zu genau einem weiteren danach. */
export function coalesce(run: () => Promise<void>): () => Promise<void> {
  let running: Promise<void> | null = null;
  let again = false;
  const next = (): Promise<void> => {
    if (running) {
      again = true;
      return running;
    }
    running = (async () => {
      try {
        do {
          again = false;
          await run();
        } while (again);
      } finally {
        running = null;
      }
    })();
    return running;
  };
  return next;
}
