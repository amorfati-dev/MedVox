// Behandler am geteilten iPad: ein Tipp aus der Liste der aktiven Behandler, bleibt im Gerät (auch
// nach dem Neuladen), bis jemand wechselt – keine Anmeldung. Nach der Übergabe an die Rezeption
// (`release`) oder nach langer Pause ohne Bedienung (Einstellung des Servers, Voreinstellung 30 min)
// fragt das iPad vor dem nächsten Diktat, wer jetzt diktiert (`gate`), statt still beim letzten zu
// bleiben; nach der Pause öffnet sich die Auswahl sofort. Reine Regeln in dentists.ts.
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api";
import { DEFAULT_IDLE_S, dentistApi, idleExpired, mustAsk, restoreDevice, type Dentist, type DeviceDentist } from "../dentists";

const STORAGE_KEY = "medvox.dentist";
const CHECK_MS = 30_000;
const SAVE_MS = 15_000; // letzte Bedienung höchstens so oft speichern

export type DentistChoice = {
  roster: Dentist[] | null; // alle Behandler; null, solange nicht geladen
  active: Dentist[];
  current: Dentist | null; // am Gerät gewählt; null = keiner oder „ohne Behandler“ (leere Liste)
  unsure: boolean; // vor dem nächsten Diktat wird gefragt (nicht bestätigt oder nicht mehr aktiv)
  asking: boolean; // Auswahl ist offen
  error: string | null;
  open: () => void;
  close: () => void;
  choose: (id: number | null) => void; // null = ohne Behandler, nur bei leerer Liste (offerNone)
  release: () => void; // Diktat übergeben: vor dem nächsten neu fragen
  gate: (then: (id: number | null) => void) => void; // vor einem neuen Diktat: erst fragen, falls nötig
};

function store(device: DeviceDentist): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(device));
  } catch {
    /* nicht speicherbar (privates Surfen): gilt bis zum Neuladen */
  }
}

function stored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

// `busy`: Aufnahme oder Senden läuft – zählt als Bedienung, dann wird nie gefragt.
export function useDentist(busy: boolean, onUnauthorized: () => void): DentistChoice {
  // Die Pause prüft erst die Einstellung des Servers (unten nach dem Laden).
  const [device, setDevice] = useState<DeviceDentist>(() => restoreDevice(stored(), Date.now(), Infinity));
  const [roster, setRoster] = useState<Dentist[] | null>(null);
  const [idleS, setIdleS] = useState(DEFAULT_IDLE_S);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const deviceRef = useRef(device);
  deviceRef.current = device;
  const rosterRef = useRef(roster);
  rosterRef.current = roster;
  const last = useRef(device.lastActive);
  const pending = useRef<((id: number | null) => void) | null>(null);
  const busyRef = useRef(busy);
  busyRef.current = busy;
  const unauthorized = useRef(onUnauthorized);
  unauthorized.current = onUnauthorized;

  const active = (roster ?? []).filter((d) => d.active);

  const load = useCallback(async () => {
    try {
      const list = await dentistApi.list();
      setRoster(list.dentists);
      setIdleS(list.idle_s);
      setError(null);
      return list;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) unauthorized.current();
      else setError(e instanceof ApiError ? e.message : "Behandlerliste nicht erreichbar.");
      return null;
    }
  }, []);

  // Beim Start: Liste laden; nach langer Pause (auch über ein Neuladen) oder ohne Wahl gleich fragen.
  useEffect(() => {
    void load().then((list) => {
      if (!list) return;
      const d = deviceRef.current;
      const next = d.confirmed && idleExpired(d.lastActive, Date.now(), list.idle_s) ? { ...d, confirmed: false } : d;
      setDevice(next);
      if (mustAsk(next, list.dentists.filter((x) => x.active))) setAsking(true);
    });
  }, [load]);

  useEffect(() => store(device), [device]);

  // Lange Pause: nicht mehr bestätigt, Auswahl öffnen. Geprüft periodisch, beim Zurückkehren ins
  // Fenster und vor jeder Bedienung – der erste Tipp nach der Pause landet schon bei der Frage.
  const checkIdle = useCallback(() => {
    const now = Date.now();
    if (busyRef.current) last.current = now;
    const d = deviceRef.current;
    if (!d.confirmed || !idleExpired(last.current, now, idleS)) return false;
    setDevice({ ...d, confirmed: false, lastActive: last.current });
    if ((rosterRef.current ?? []).some((x) => x.active)) setAsking(true);
    return true;
  }, [idleS]);

  useEffect(() => {
    let savedAt = 0;
    const touch = () => {
      checkIdle();
      const now = Date.now();
      last.current = now;
      if (now - savedAt < SAVE_MS) return;
      savedAt = now;
      store({ ...deviceRef.current, lastActive: now });
    };
    const onVisible = () => document.visibilityState === "visible" && checkIdle();
    const timer = window.setInterval(checkIdle, CHECK_MS);
    document.addEventListener("pointerdown", touch, true);
    document.addEventListener("keydown", touch, true);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("pointerdown", touch, true);
      document.removeEventListener("keydown", touch, true);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [checkIdle]);

  const open = useCallback(() => {
    setAsking(true);
    void load(); // neue Kollegen ohne Neuladen
  }, [load]);

  const close = useCallback(() => {
    pending.current = null;
    setAsking(false);
  }, []);

  const choose = useCallback((id: number | null) => {
    const now = Date.now();
    last.current = now;
    setDevice({ id, confirmed: true, lastActive: now });
    setAsking(false);
    const then = pending.current;
    pending.current = null;
    then?.(id);
  }, []);

  const release = useCallback(() => setDevice((d) => ({ ...d, confirmed: false })), []);

  const gate = useCallback(
    (then: (id: number | null) => void) => {
      const list = rosterRef.current;
      const live = (list ?? []).filter((d) => d.active);
      const device = deviceRef.current;
      // Liste noch nicht geladen: nur eine bestätigte Wahl gilt, sonst fragen (lädt die Liste neu).
      if (list === null ? !device.confirmed : mustAsk(device, live)) {
        pending.current = then;
        open();
        return;
      }
      then(list === null || live.some((d) => d.id === device.id) ? device.id : null);
    },
    [open],
  );

  return {
    roster,
    active,
    current: roster?.find((d) => d.id === device.id) ?? null,
    unsure: !device.confirmed || mustAsk(device, active),
    asking,
    error,
    open,
    close,
    choose,
    release,
    gate,
  };
}
