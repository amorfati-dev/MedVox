// Büro (/patienten): nach der Runde durch die Behandlungsräume die Diktate je Patient nach Evident
// übertragen. Links die Liste (ohne Patient, dann Patienten, jüngstes zuerst), rechts der gewählte
// Patient mit seinen Diktaten und denselben Kopieraktionen wie am iPad; „Als übertragen markieren“
// löscht den Inhalt sofort. Kurzcode und /transfer bleiben für die sofortige Übergabe.
import { useState } from "react";
import { api, ApiError, type StoredDictation } from "../api";
import { DictationCard } from "../components/DictationCard";
import { PatientListCard, type Selection } from "../components/PatientListCard";
import { PatientPicker } from "../components/PatientPicker";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { usePatientList } from "../hooks/usePatientList";
import { patientState, STATE_LABEL } from "../patients";

type Props = { onLogout: () => void };

export function Patienten({ onLogout }: Props) {
  const [selected, setSelected] = useState<Selection>(null);
  const data = usePatientList(selected?.kind === "patient" ? selected.id : null, onLogout);
  const [assigning, setAssigning] = useState<StoredDictation | null>(null);
  const [confirm, setConfirm] = useState<string | null>(null); // Schlüssel der Aktion, die bestätigt werden muss
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const select = (s: Selection) => {
    setSelected(s);
    setConfirm(null);
    setMessage(null);
    setError(null);
  };

  // Eine Aktion ausführen, danach Liste und Patient neu laden; 401 führt zur Anmeldung.
  const act = async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setConfirm(null);
    try {
      await work();
      await data.refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) onLogout();
      else setError(e instanceof ApiError ? e.message : "Aktion fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const markTransferred = () =>
    act(async () => {
      const detail = data.detail;
      if (!detail) return;
      const after = await api.markTransferred(detail.id, detail.items);
      data.setDetail(after);
      setMessage(
        after.items.length === 0
          ? `Patient ${after.number} als übertragen markiert – Text und Ziffern sind auf dem Praxis-Mac gelöscht.`
          : `${after.items.length === 1 ? "Ein Diktat ist" : `${after.items.length} Diktate sind`} inzwischen neu oder geändert – bitte prüfen und erneut markieren.`,
      );
    });

  const assign = (d: StoredDictation, number: string | null) => {
    setAssigning(null);
    if (number === null || number === d.patient) return;
    void act(async () => {
      const patient = await api.createPatient(number);
      await api.appendDictation(patient.id, d.id);
      setSelected({ kind: "patient", id: patient.id });
      setMessage(`Diktat Patient ${number} zugeordnet.`);
    });
  };

  // Zweistufig statt Browser-Dialog: erster Tipp fragt nach, zweiter führt aus.
  const twoStep = (key: string, label: string, work: () => Promise<void>) =>
    confirm === key ? (
      <button type="button" className="btn btn-warn" disabled={busy} onClick={() => void act(work)}>
        Wirklich {label}?
      </button>
    ) : (
      <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => setConfirm(key)}>
        {label[0].toUpperCase() + label.slice(1)}
      </button>
    );

  const assignButton = (d: StoredDictation, label: string, primary = false) => (
    <button type="button" className={primary ? "btn btn-primary" : "btn"} disabled={busy} onClick={() => setAssigning(d)}>
      {label}
    </button>
  );

  const loose = selected?.kind === "ohne" ? data.list?.unassigned.find((d) => d.id === selected.id) ?? null : null;
  const detail = selected?.kind === "patient" ? data.detail : null;

  let content;
  if (loose) {
    content = (
      <section className="card">
        <div className="section-head">
          <h2>Ohne Patient</h2>
          <span className="state-chip state-ohne">zuordnen</span>
        </div>
        <p className="muted small">Vor dem Übertragen die Evident-Nummer zuordnen.</p>
        <DictationCard d={loose} title="Diktat">
          {assignButton(loose, "Patient zuordnen", true)}
          {twoStep(`weg-${loose.id}`, "verwerfen", async () => {
            await api.deleteDictation(loose.id);
            setSelected(null);
          })}
        </DictationCard>
      </section>
    );
  } else if (detail) {
    const state = patientState(detail);
    content = (
      <section className="card">
        <div className="section-head">
          <h2 className="patient-head">
            Patient <span className="mono">{detail.number}</span>
          </h2>
          <span className={`state-chip state-${state === "übertragen" ? "done" : state}`}>{STATE_LABEL[state]}</span>
        </div>
        {detail.items.length === 0 && (
          <p className="muted">
            {state === "übertragen"
              ? "Alle Diktate sind übertragen, der Inhalt ist gelöscht."
              : "Noch kein Diktat – am iPad diese Nummer wählen und diktieren."}
          </p>
        )}
        {detail.items.map((d, i) => (
          <DictationCard key={d.id} d={d} title={detail.items.length > 1 ? `Diktat ${i + 1} von ${detail.items.length}` : "Diktat"}>
            {assignButton(d, "Anderem Patienten zuordnen")}
          </DictationCard>
        ))}
        <div className="actions patient-actions">
          {detail.items.length > 0 && (
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void markTransferred()}>
              Als übertragen markieren
            </button>
          )}
          {twoStep(`pat-${detail.id}`, "löschen", async () => {
            await api.deletePatient(detail.id);
            setSelected(null);
          })}
        </div>
        <p className="muted small">
          „Als übertragen markieren“ löscht Text und Ziffern dieses Patienten sofort auf dem Praxis-Mac; nur Nummer und
          Uhrzeit bleiben bis zum Ablauf der 24 Stunden in der Liste.
        </p>
      </section>
    );
  } else {
    content = (
      <section className="card placeholder">
        <p className="muted">
          {!selected
            ? "Links einen Patienten wählen."
            : selected.kind === "patient" && data.list?.patients.some((p) => p.id === selected.id)
              ? "Lade …"
              : "Nicht mehr vorhanden – übertragen, gelöscht oder älter als 24 Stunden."}
        </p>
      </section>
    );
  }

  return (
    <main className="page wide rezeption patienten">
      <header className="topbar">
        <h1>MedVox · Patienten</h1>
        <nav>
          <ThemeSwitch />
          <button type="button" className="btn" onClick={() => void data.refresh()}>
            Aktualisieren
          </button>
          <a className="btn" href="/transfer">
            Kurzcode
          </a>
          <a className="btn" href="/">
            Diktat
          </a>
        </nav>
      </header>
      {(error ?? data.error) && (
        <p role="alert" className="error">
          {error ?? data.error}
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      <div className="rezeption-grid">
        <PatientListCard list={data.list} selected={selected} onSelect={select} />
        {content}
      </div>
      {assigning && (
        <PatientPicker
          title="Patient zuordnen"
          current={assigning.patient}
          onChoose={(number) => assign(assigning, number)}
          onClose={() => setAssigning(null)}
        />
      )}
    </main>
  );
}
