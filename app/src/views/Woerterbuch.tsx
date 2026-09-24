// Wörterbuch pflegen (/woerterbuch), gedacht vor allem für den Büro-PC: Ersetzungen „falsch gehört →
// richtig“, Fachbegriffe für den Whisper-Prompt und Vorschläge aus den Korrekturen. Was hier gespeichert
// wird, gilt ab dem nächsten Diktat für alle iPads, ohne Neustart (Entscheidung F5); abgeschaltet wird
// statt gelöscht. Gebaut wie /behandler: Karten, 64-px-Felder; ab 900 px zwei Spalten.
import { useState } from "react";
import { LexiconReplacements } from "../components/LexiconReplacements";
import { LexiconSuggestions } from "../components/LexiconSuggestions";
import { LexiconTerms } from "../components/LexiconTerms";
import type { Prefill } from "../components/ReplacementForm";
import { ThemeSwitch } from "../components/ThemeSwitch";
import { useLexicon } from "../hooks/useLexicon";
import type { LexiconSuggestion } from "../lexicon";

type Props = { onLogout: () => void };

export function Woerterbuch({ onLogout }: Props) {
  const { lexicon, suggestions, busy, error, message, act } = useLexicon(onLogout);
  const [prefill, setPrefill] = useState<{ nonce: number; value: Prefill } | null>(null);

  const take = (s: LexiconSuggestion) => {
    setPrefill((p) => ({ nonce: (p?.nonce ?? 0) + 1, value: { wrong: s.before, right: s.after, sentence: "", source: "korrektur" } }));
    document.getElementById("lex-form-top")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <main className="page wide rezeption behandler woerterbuch">
      <header className="topbar">
        <h1>MedVox · Wörterbuch</h1>
        <nav>
          <ThemeSwitch />
          <a className="btn" href="/patienten">
            Patienten
          </a>
          <a className="btn" href="/">
            Diktat
          </a>
        </nav>
      </header>
      <p className="muted">
        Was hier steht, gilt ab dem nächsten Diktat für alle iPads. Ein Eintrag lässt sich jederzeit abschalten. Zahlen und
        Ziffern werden nie ersetzt.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      {lexicon === null ? (
        !error && <p className="muted">Lade …</p>
      ) : (
        <div className="lex-grid">
          <div id="lex-form-top">
            <LexiconReplacements lexicon={lexicon} busy={busy} act={act} prefill={prefill} />
          </div>
          <div>
            <LexiconTerms lexicon={lexicon} busy={busy} act={act} />
            {suggestions && <LexiconSuggestions found={suggestions} busy={busy} act={act} onTake={take} />}
          </div>
        </div>
      )}
    </main>
  );
}
