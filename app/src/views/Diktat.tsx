// Diktat-Ansicht: links die Steuerung (wer diktiert, aktiver Patient, Schalter Kasse/Privat, Statusfeld,
// Aufnahmeknopf), rechts das Ergebnis (ResultPane: Kopfzeile, Transkript, Liste nach Zahn, Geplantes,
// Hinweise) mit der Leiste Text · Ziffern · An Rezeption. Im Querformat (≥ 900 px) zwei Spalten, im Hochformat
// untereinander (styles/diktat.css). Die Aufnahme- und Warteschlangenlogik liegt in useDictation.
// Jedes Diktat wird beim aktiven Patienten (Evident-Nummer) auf dem Praxis-Mac gespeichert
// (useDictationSave), ohne Nummer als „ohne Patient“; im Büro unter /patienten übertragen. Eine
// später gewählte Nummer ordnet es erst nach Nachfrage zu (AssignDialog). Jedes Diktat trägt den
// Behandler, der beim Start der Aufnahme am iPad gewählt war (useDentist); ein späterer Wechsel am
// Gerät ändert es nicht.
import { useEffect, useMemo, useState } from "react";
import { api, ApiError, type DictationBody } from "../api";
import { AssignDialog } from "../components/AssignDialog";
import { Controls } from "../components/Controls";
import { DentistBar } from "../components/DentistBar";
import { DentistPicker } from "../components/DentistPicker";
import { MoreMenu } from "../components/MoreMenu";
import { PatientBar } from "../components/PatientBar";
import { PatientPicker } from "../components/PatientPicker";
import { PatientSwitch } from "../components/PatientSwitch";
import { ResultPane } from "../components/ResultPane";
import { StatusPanel } from "../components/StatusPanel";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { useDentist } from "../hooks/useDentist";
import { useDictation } from "../hooks/useDictation";
import { useDictationSave } from "../hooks/useDictationSave";
import { usePatientType } from "../hooks/usePatientType";
import { useSelection } from "../hooks/useSelection";
import { useTransfer } from "../hooks/useTransfer";
import { pickAction } from "../patients";
import { countGroups, positionsOf, uniquePlanned } from "../result";
import { formatSeconds, plural, uiState } from "../status";
import { Login } from "./Login";

type Props = { onLogout: () => void };

const UNSUPPORTED = "Dieser Browser kann nicht aufnehmen – bitte Safari auf dem iPad verwenden.";

export function Diktat({ onLogout }: Props) {
  const [patientType, setPatientType] = usePatientType();
  const d = useDictation(patientType);
  const sel = useSelection(d.codes, d.suggestions);
  const plans = useMemo(() => uniquePlanned(d.planned), [d.planned]);
  const counts = useMemo(() => countGroups(sel.groups, plans), [sel.groups, plans]);
  const details = useMemo(
    () => (d.resultType ? { patient_type: d.resultType, positions: positionsOf(sel.groups) } : null),
    [d.resultType, sel.groups],
  );
  const transfer = useTransfer(d.transcript, sel.evident, details, d.sessionExpired);
  const recording = d.phase === "aufnahme";
  const sending = d.phase === "sende";
  const resumable = d.phase === "fortsetzbar";
  const running = recording || sending || resumable;
  const dentist = useDentist(running, d.sessionExpired);
  const [dictDentist, setDictDentist] = useState<number | null>(null); // beim Start der Aufnahme festgehalten
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [patient, setPatient] = useState<string | null>(null); // Evident-Nummer, null = ohne Patient
  const [picking, setPicking] = useState(false);
  const [asking, setAsking] = useState<string | null>(null); // Nummer, für die die Zuordnung erfragt wird
  const hasResult = d.transcript !== "" || d.suggestions.length > 0 || d.planned.length > 0;
  const body = useMemo<DictationBody | null>(
    () =>
      hasResult
        ? {
            ...(patient ? { patient } : {}),
            dentist_id: dictDentist,
            transcript: d.transcript,
            patient_type: d.resultType,
            codes: d.codes,
            suggestions: d.suggestions,
            planned: d.planned,
            notes: d.notes,
            deselected: sel.deselected,
            adopted: sel.adopted,
          }
        : null,
    [hasResult, patient, dictDentist, d.transcript, d.resultType, d.codes, d.suggestions, d.planned, d.notes, sel.deselected, sel.adopted],
  );
  const save = useDictationSave(body, d.sessionExpired);
  const closed = save.state === "übertragen";

  const logout = async () => {
    setLogoutError(null);
    try {
      await api.logout();
      onLogout();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onLogout();
        return;
      }
      setLogoutError(e instanceof ApiError ? e.message : "Abmelden fehlgeschlagen.");
    }
  };

  // Übergeben: vor dem nächsten Diktat fragen, wer diktiert (das iPad wandert zum Kollegen).
  const { release } = dentist;
  useEffect(() => {
    if (transfer.result) release();
  }, [transfer.result, release]);

  // Neues Diktat für denselben Patienten; das bisherige bleibt gespeichert. Erst fragen, wer diktiert,
  // falls nötig; der gewählte Behandler gilt für dieses Diktat bis zum Schluss.
  const startNew = () =>
    dentist.gate((id) => {
      save.detach();
      sel.clear();
      d.reset(); // Bildschirm leer, bevor der neue Behandler gilt – nie ein altes Ergebnis unter neuem Namen
      setDictDentist(id);
      void d.start();
    });

  const clear = () => {
    save.detach();
    d.reset();
    sel.clear();
  };

  // Verwerfen löscht das Diktat auch auf dem Praxis-Mac.
  const discard = () => {
    save.discard();
    d.reset();
    sel.clear();
  };

  // Anderer Behandler am Gerät: ein Ergebnis auf dem Bildschirm bleibt beim bisherigen gespeichert,
  // der Bildschirm wird frei.
  const chooseDentist = (id: number | null) => {
    if (hasResult && !running && id !== dictDentist) clear();
    dentist.choose(id);
  };

  // Nächster Patient: Bildschirm leeren und gleich die Nummer abfragen.
  const nextPatient = () => {
    clear();
    setPatient(null);
    setPicking(true);
  };

  // Gehört das Diktat schon einem Patienten, bleibt es dort gespeichert und der Bildschirm wird frei;
  // ein Diktat „ohne Patient“ bekommt die Nummer nur nach Nachfrage.
  const choosePatient = (number: string | null) => {
    setPicking(false);
    const action = pickAction(patient, number, !hasResult ? "keins" : closed ? "übertragen" : "offen");
    if (action === "bleiben") return;
    if (action === "fragen" && number !== null) return setAsking(number);
    if (action === "neu") clear();
    setPatient(number);
  };

  // Antwort auf die Nachfrage: zuordnen oder das Diktat „ohne Patient“ lassen und neu beginnen.
  const answer = (assign: boolean) => {
    if (asking === null) return;
    if (!assign) clear();
    setPatient(asking);
    setAsking(null);
  };

  // Sitzung abgelaufen: Anmeldung anzeigen, Diktat und offene Abschnitte bleiben im Speicher.
  if (d.sessionLost) {
    return (
      <Login
        notice="Sitzung abgelaufen – bitte erneut anmelden. Das aktuelle Diktat bleibt erhalten."
        onLogin={d.relogin}
      />
    );
  }

  const error = d.supported ? d.error : UNSUPPORTED;
  const state = uiState({ ...d, error });
  const summary = [
    d.lastLatency !== null ? formatSeconds(d.lastLatency) : "",
    plural(counts.positions, "Ziffer", "Ziffern"),
    counts.planned > 0 ? `${counts.planned} geplant` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="diktat ipad">
      <aside className="control" aria-label="Aufnahme">
        <header className="control-head">
          <h1>MedVox</h1>
          <ThemeSwitch />
          <MoreMenu onLogout={logout} />
        </header>
        <DentistBar choice={dentist} onOpen={dentist.open} locked={running} />
        <PatientBar number={patient} onOpen={() => setPicking(true)} locked={running && (patient !== null || hasResult)} save={save} />
        <PatientSwitch value={patientType} onChange={setPatientType} disabled={running} />
        {running && (
          <p className="switch-hint">Der Patiententyp gilt für das ganze laufende Diktat.</p>
        )}
        <div className="control-main">
          <StatusPanel
            state={state}
            seconds={d.seconds}
            level={d.level}
            waiting={d.waiting}
            uploading={d.uploading}
            error={error}
            rejected={d.discardable}
            summary={summary}
          />
          <Controls
            state={state}
            d={d}
            onNew={startNew}
            onNext={nextPatient}
            onDiscard={discard}
            handedOver={transfer.result !== null}
          />
        </div>
        {logoutError && (
          <p role="alert" className="error">
            {logoutError}
          </p>
        )}
      </aside>

      <ResultPane
        d={d}
        sel={sel}
        plans={plans}
        counts={counts}
        state={state}
        patientType={patientType}
        running={running}
        hasResult={hasResult}
        closed={closed}
        transfer={transfer}
        onClear={clear}
        onHandover={() => void transfer.send(save.handover(), dictDentist)}
      />
      {picking && (
        <PatientPicker
          title="Patient wählen"
          current={patient}
          onChoose={choosePatient}
          onClose={() => setPicking(false)}
          allowNone
        />
      )}
      {dentist.asking && (
        <DentistPicker
          active={dentist.active}
          current={dentist.current?.id ?? null}
          error={dentist.error}
          onChoose={chooseDentist}
          onClose={dentist.close}
        />
      )}
      {asking !== null && (
        <AssignDialog number={asking} onAssign={() => answer(true)} onNew={() => answer(false)} onCancel={() => setAsking(null)} />
      )}
    </div>
  );
}
