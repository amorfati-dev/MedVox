// Ein gespeichertes Diktat im Büro: Transkript, Evident-Zeilen je Zahn, Mehrkosten und dieselben
// Kopieraktionen wie am iPad (Text, Ziffern, Nur Ziffern) – Format unverändert (patients.ts).
import type { ReactNode } from "react";
import { evidentText, type StoredDictation } from "../api";
import { clock, dictationCopy } from "../patients";
import { CopayTable } from "./CopayTable";
import { CopyButton } from "./CopyButton";
import { EvidentLines } from "./EvidentLines";
import { PATIENT_LABEL } from "./PatientSwitch";

type Props = { d: StoredDictation; title: string; children?: ReactNode };

export function DictationCard({ d, title, children }: Props) {
  const copy = dictationCopy(d);
  return (
    <article className="dictation">
      <div className="section-head">
        <h3>
          {title} · {clock(d.created_at)} Uhr
        </h3>
        {d.patient_type && <span className={`badge badge-${d.patient_type}`}>{PATIENT_LABEL[d.patient_type]}</span>}
      </div>
      <p className="transcript">{d.transcript || <span className="muted">(leer)</span>}</p>
      <h2>Ziffern für Evident</h2>
      <EvidentLines lines={copy.evident} />
      <CopayTable positions={copy.positions} />
      <div className="actions">
        <CopyButton label="Text kopieren" text={d.transcript} primary />
        <CopyButton label="Ziffern kopieren" text={evidentText(copy.evident)} />
        <CopyButton label="Nur Ziffern" text={evidentText(copy.numbers)} />
        {children}
      </div>
    </article>
  );
}
