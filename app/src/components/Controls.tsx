// Steuerung unter dem Statusfeld: Aufnahmeknopf und die Aktionen des jeweiligen Zustands.
// Nur Anzeige – alle Aktionen sind die von useDictation (stop, next, resume, retry, dropSegment)
// bzw. „neues Diktat“, „nächster Patient“ und „verwerfen“ aus der Diktat-Ansicht.
import type { Dictation } from "../hooks/useDictation";
import type { UiState } from "../status";
import { Icon } from "./Icon";
import { RecordButton } from "./RecordButton";

type Props = {
  state: UiState;
  d: Dictation;
  onNew: () => void; // neues Diktat aufnehmen (das bisherige bleibt beim Patienten gespeichert)
  onNext: () => void; // Bildschirm leeren und die nächste Patientennummer abfragen
  onDiscard: () => void; // Diktat verwerfen (auch das gespeicherte)
  handedOver: boolean; // Kurzcode erzeugt: „Nächster Patient“ wird Hauptaktion
};

export function Controls({ state, d, onNew, onNext, onDiscard, handedOver }: Props) {
  switch (state) {
    case "aufnahme":
      return (
        <div className="controls">
          <RecordButton variant="stopp" onClick={d.stop} />
          <button type="button" className="btn btn-block" onClick={d.next}>
            <Icon name="plus" />
            <span className="btn-text">
              Abschnitt anhängen
              <small>Bisheriges senden, Aufnahme läuft weiter</small>
            </span>
          </button>
        </div>
      );
    case "senden":
      return (
        <div className="controls">
          <RecordButton variant="warten" onClick={() => undefined} />
        </div>
      );
    case "fertig":
      return (
        <div className="controls">
          <RecordButton variant="neu" onClick={onNew} />
          <button type="button" className={handedOver ? "btn btn-primary btn-block" : "btn btn-block"} onClick={onNext}>
            <Icon name="user" />
            Nächster Patient
          </button>
        </div>
      );
    case "fortsetzbar":
      return (
        <div className="controls">
          {d.retryable ? (
            <>
              <RecordButton variant="erneut" onClick={d.retry} />
              <button type="button" className="btn btn-block" onClick={() => void d.resume()}>
                <Icon name="mic" />
                Weiter aufnehmen
              </button>
            </>
          ) : (
            <RecordButton
              variant="aufnehmen"
              label="Weiter aufnehmen"
              aria="Diktat fortsetzen – nächsten Abschnitt anhängen"
              onClick={() => void d.resume()}
            />
          )}
          <button type="button" className="btn btn-quiet btn-block" onClick={onDiscard}>
            Verwerfen
          </button>
        </div>
      );
    case "fehler":
      if (d.discardable) {
        return (
          <div className="controls">
            <RecordButton variant="aufnehmen" onClick={onNew} disabled />
            <button type="button" className="btn btn-warn btn-block" onClick={d.dropSegment}>
              Diesen Abschnitt verwerfen
            </button>
            <button type="button" className="btn btn-quiet btn-block" onClick={onDiscard}>
              Ganzes Diktat verwerfen
            </button>
          </div>
        );
      }
      return (
        <div className="controls">
          <RecordButton variant="aufnehmen" onClick={onNew} disabled={!d.supported} />
        </div>
      );
    default:
      return (
        <div className="controls">
          <RecordButton variant="aufnehmen" onClick={onNew} />
        </div>
      );
  }
}
