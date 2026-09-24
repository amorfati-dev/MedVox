// Büro-Liste live: jedes Ereignis des Stroms lädt sofort neu; ohne Strom gleicht die Liste wie
// bisher alle 30 Sekunden ab und verbindet sich von selbst wieder.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  coalesce,
  EVENTS_URL,
  GRACE_MS,
  POLL_MS,
  REOPEN_MS,
  SILENT_MS,
  watchChanges,
  type ChangeSource,
  type LiveMode,
  type Timers,
} from "../src/live.ts";

class FakeSource implements ChangeSource {
  readyState = 0; // CONNECTING
  onopen: ChangeSource["onopen"] = null;
  onerror: ChangeSource["onerror"] = null;
  closed = false;
  listeners: { type: string; listener: () => void }[] = [];
  readonly url: string;
  constructor(url: string) {
    this.url = url;
  }
  addEventListener(type: "changed" | "ping", listener: () => void) {
    this.listeners.push({ type, listener });
  }
  close() {
    this.closed = true;
    this.readyState = 2;
  }
  open() {
    this.readyState = 1;
    this.onopen?.(new Event("open"));
  }
  emit(type: "changed" | "ping") {
    for (const l of this.listeners) if (l.type === type) l.listener();
  }
  changed() {
    this.emit("changed");
  }
  fail(readyState: 0 | 2) {
    this.readyState = readyState;
    this.onerror?.(new Event("error"));
  }
}

// Manuelle Uhr statt echter Zeitgeber.
function clock() {
  let now = 0;
  let next = 1;
  const jobs = new Map<number, { at: number; fn: () => void; every: number | null }>();
  const add = (fn: () => void, ms: number, every: number | null) => {
    jobs.set(next, { at: now + ms, fn, every });
    return next++ as unknown as ReturnType<typeof setTimeout>;
  };
  const drop = (id: ReturnType<typeof setTimeout>) => void jobs.delete(id as unknown as number);
  const timers: Timers = {
    setTimeout: (fn, ms) => add(fn, ms, null),
    setInterval: (fn, ms) => add(fn, ms, ms),
    clearTimeout: drop,
    clearInterval: drop,
  };
  const advance = (ms: number) => {
    const end = now + ms;
    for (;;) {
      const due = [...jobs.entries()].filter(([, j]) => j.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      const [id, job] = due;
      now = job.at;
      if (job.every === null) jobs.delete(id);
      else job.at += job.every;
      job.fn();
    }
    now = end;
  };
  return { timers, advance, pending: () => jobs.size };
}

function setup(withEventSource = true) {
  const c = clock();
  const sources: FakeSource[] = [];
  const modes: LiveMode[] = [];
  let changes = 0;
  const stop = watchChanges({
    onChange: () => changes++,
    onMode: (m) => modes.push(m),
    open: withEventSource
      ? (url) => {
          const s = new FakeSource(url);
          sources.push(s);
          return s;
        }
      : null,
    timers: c.timers,
  });
  const last = () => sources[sources.length - 1];
  // Zeit vergehen lassen, während der Server wie echt alle 15 s ein `ping` schickt.
  const pinging = (ms: number) => {
    for (let t = 0; t < ms; t += 15_000) {
      c.advance(15_000);
      last().emit("ping");
    }
  };
  return { ...c, sources, modes, stop, changes: () => changes, last, pinging };
}

test("ein Ereignis lädt sofort neu, ohne auf den Abgleich zu warten", () => {
  const w = setup();
  assert.equal(w.last().url, EVENTS_URL);
  w.last().open();
  assert.deepEqual(w.modes, ["live"]);
  w.last().changed(); // Version beim Verbindungsaufbau
  w.last().changed(); // neues Diktat vom iPad
  assert.equal(w.changes(), 2); // synchron, ohne dass Zeit vergeht
  w.pinging(POLL_MS * 3);
  assert.equal(w.changes(), 2); // solange der Strom steht, kein Abgleich
});

test("kurzes Neuverbinden des Browsers wechselt nicht in den Abgleich", () => {
  const w = setup();
  w.last().open();
  w.last().fail(0); // Browser verbindet sich selbst neu (retry 3 s)
  w.advance(3_000);
  w.last().open();
  w.advance(GRACE_MS * 2);
  assert.deepEqual(w.modes, ["live"]);
  assert.equal(w.sources.length, 1);
});

test("Strom weg: sofort ein Abgleich, dann alle 30 Sekunden, bis er wieder steht", () => {
  const w = setup();
  w.last().open();
  w.last().fail(0);
  w.advance(GRACE_MS);
  assert.deepEqual(w.modes, ["live", "polling"]);
  assert.equal(w.changes(), 1);
  w.advance(POLL_MS * 2);
  assert.equal(w.changes(), 3);
  w.last().open();
  assert.deepEqual(w.modes, ["live", "polling", "live"]);
  w.pinging(POLL_MS * 2);
  assert.equal(w.changes(), 3);
});

test("abgewiesener Strom (401, Server aus): Abgleich und später ein neuer Versuch", () => {
  const w = setup();
  w.last().fail(2);
  assert.equal(w.sources[0].closed, true);
  assert.deepEqual(w.modes, ["polling"]);
  assert.equal(w.changes(), 1); // Abgleich meldet 401 an die Seite weiter
  w.advance(REOPEN_MS);
  assert.equal(w.sources.length, 2);
  w.last().open();
  assert.deepEqual(w.modes, ["polling", "live"]);
});

test("stille Verbindung (Proxy hält sie offen, WLAN weg): Abgleich und neue Verbindung", () => {
  const w = setup();
  w.last().open();
  w.pinging(60_000); // Lebenszeichen halten die Verbindung
  assert.deepEqual(w.modes, ["live"]);
  w.advance(SILENT_MS);
  assert.equal(w.sources[0].closed, true);
  assert.deepEqual(w.modes, ["live", "polling"]);
  assert.equal(w.sources.length, 2);
  w.last().open();
  assert.deepEqual(w.modes, ["live", "polling", "live"]);
});

test("Browser ohne EventSource: nur der Abgleich wie bisher", () => {
  const w = setup(false);
  assert.deepEqual(w.modes, ["polling"]);
  w.advance(POLL_MS);
  assert.equal(w.changes(), 2);
});

test("Abmelden schließt den Strom und stoppt alle Zeitgeber", () => {
  const w = setup();
  w.last().open();
  w.last().fail(0);
  w.advance(GRACE_MS);
  w.stop();
  assert.equal(w.sources[0].closed, true);
  assert.equal(w.pending(), 0);
});

test("Abrufe überlappen nie; Ereignisse währenddessen führen zu genau einem weiteren", async () => {
  let runs = 0;
  let release: () => void = () => undefined;
  const refresh = coalesce(async () => {
    runs++;
    await new Promise<void>((r) => (release = r));
  });
  const first = refresh();
  void refresh();
  const third = refresh();
  assert.equal(runs, 1);
  release();
  await new Promise((r) => setImmediate(r));
  assert.equal(runs, 2);
  release();
  await Promise.all([first, third]);
  assert.equal(runs, 2);
});
