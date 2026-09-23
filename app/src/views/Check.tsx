// Gerätetest (/check): HTTPS, Mikrofon (mit Pegel), Server-Health und MediaRecorder-Formate.
// Oben ein Banner „Alles bereit“ bzw. „1 Problem“, darunter eine Kachel je Prüfung.
import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { Icon } from "../components/Icon";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { MIC_MESSAGES, MIME_CANDIDATES, requestMicrophone, startLevelMeter, stopStream } from "../hooks/recorder";

type Result = { ok: boolean | null; text: string };

const pending: Result = { ok: null, text: "prüfe …" };
const METER_SECONDS = 6; // so lange zeigt der Mikrofontest den Pegel

export function Check() {
  const [health, setHealth] = useState<Result>(pending);
  const [mic, setMic] = useState<Result>({ ok: null, text: "noch nicht getestet – „Mikrofon testen“ antippen" });
  const [level, setLevel] = useState<number | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) =>
        setHealth(
          h.whisper === "ok"
            ? { ok: true, text: "Server und Whisper erreichbar" }
            : { ok: false, text: "Server erreichbar, Whisper nicht bereit" },
        ),
      )
      .catch((e: unknown) => setHealth({ ok: false, text: e instanceof ApiError ? e.message : "Fehler" }));
  }, []);

  const testMic = async () => {
    setMic(pending);
    const r = await requestMicrophone();
    if (!r.ok) {
      setMic({ ok: false, text: MIC_MESSAGES[r.error] });
      return;
    }
    setMic({ ok: true, text: "Mikrofon freigegeben – bitte sprechen, der Balken zeigt den Pegel" });
    setLevel(0);
    const meter = startLevelMeter(r.stream, setLevel);
    window.setTimeout(() => {
      meter.stop();
      stopStream(r.stream);
      setLevel(null);
      setMic({ ok: true, text: "Mikrofon freigegeben" });
    }, METER_SECONDS * 1000);
  };

  const https = window.isSecureContext;
  const hasRecorder = typeof MediaRecorder !== "undefined";
  const mimes = hasRecorder ? MIME_CANDIDATES.filter((m) => MediaRecorder.isTypeSupported(m)) : [];

  const rows: Array<[string, Result]> = [
    ["Sichere Verbindung (HTTPS)", { ok: https, text: https ? `ja (${window.location.origin})` : "nein – Aufnahme wird nicht funktionieren" }],
    ["Audioaufnahme (MediaRecorder)", { ok: hasRecorder && mimes.length > 0, text: mimes.length ? mimes.join(", ") : hasRecorder ? "vorhanden, aber kein passendes Audioformat" : "fehlt" }],
    ["Mikrofon", mic],
    ["Praxis-Mac (Server-Health)", health],
  ];
  const problems = rows.filter(([, r]) => r.ok === false).length;
  const open = rows.filter(([, r]) => r.ok === null).length;
  const banner =
    problems > 0
      ? { cls: "banner-err", icon: "x" as const, text: problems === 1 ? "1 Problem" : `${problems} Probleme` }
      : open > 0
        ? { cls: "banner-open", icon: "info" as const, text: "Noch nicht alles geprüft" }
        : { cls: "banner-ok", icon: "check" as const, text: "Alles bereit" };

  return (
    <main className="page narrow">
      <header className="topbar">
        <h1>MedVox · Gerätetest</h1>
        <nav>
          <ThemeSwitch />
          <a className="btn" href="/">
            Diktat
          </a>
        </nav>
      </header>
      <p className={`banner ${banner.cls}`} role="status">
        <Icon name={banner.icon} />
        {banner.text}
      </p>
      <ul className="tiles">
        {rows.map(([name, r]) => (
          <li key={name} className={r.ok === true ? "tile tile-ok" : r.ok === false ? "tile tile-bad" : "tile"}>
            <Icon name={r.ok === true ? "check" : r.ok === false ? "x" : "info"} />
            <div>
              <h2>{name}</h2>
              <p>{r.text}</p>
              {name === "Mikrofon" && level !== null && (
                <div className="tile-level" aria-hidden="true">
                  <div style={{ width: `${Math.round(level * 100)}%` }} />
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
      <button type="button" className="btn btn-primary btn-block" onClick={testMic} disabled={level !== null}>
        Mikrofon testen
      </button>
    </main>
  );
}
