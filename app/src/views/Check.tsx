// Gerätetest (/check): HTTPS, Mikrofon, Server-Health und MediaRecorder-Formate.
import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { MIC_MESSAGES, MIME_CANDIDATES, requestMicrophone, stopStream } from "../hooks/recorder";

type Result = { ok: boolean | null; text: string };

const pending: Result = { ok: null, text: "prüfe …" };

export function Check() {
  const [health, setHealth] = useState<Result>(pending);
  const [mic, setMic] = useState<Result>({ ok: null, text: "noch nicht getestet" });

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
    if (r.ok) {
      stopStream(r.stream);
      setMic({ ok: true, text: "Mikrofon freigegeben" });
    } else {
      setMic({ ok: false, text: MIC_MESSAGES[r.error] });
    }
  };

  const https = window.isSecureContext;
  const hasRecorder = typeof MediaRecorder !== "undefined";
  const mimes = hasRecorder ? MIME_CANDIDATES.filter((m) => MediaRecorder.isTypeSupported(m)) : [];

  const rows: Array<[string, Result]> = [
    ["HTTPS / sicherer Kontext", { ok: https, text: https ? `ja (${window.location.origin})` : "nein – Aufnahme wird nicht funktionieren" }],
    ["MediaRecorder", { ok: hasRecorder && mimes.length > 0, text: mimes.length ? mimes.join(", ") : hasRecorder ? "vorhanden, aber kein passendes Audioformat" : "fehlt" }],
    ["Mikrofon", mic],
    ["Server-Health", health],
  ];

  return (
    <main className="page narrow">
      <header className="topbar">
        <h1>MedVox · Gerätetest</h1>
        <nav>
          <ThemeSwitch />
          <a href="/">Diktat</a>
        </nav>
      </header>
      <section className="card">
        <table className="checks">
          <tbody>
            {rows.map(([name, r]) => (
              <tr key={name}>
                <th scope="row">{name}</th>
                <td className={r.ok === true ? "ok" : r.ok === false ? "bad" : ""}>
                  {r.ok === true ? "✓ " : r.ok === false ? "✗ " : "· "}
                  {r.text}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" className="btn btn-primary" onClick={testMic}>
          Mikrofon testen
        </button>
      </section>
    </main>
  );
}
