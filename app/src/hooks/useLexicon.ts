// Daten der Wörterbuch-Seite: Einträge, Füllstand des Prompts, Vorschläge aus Korrekturen. Jede Aktion
// lädt danach beides neu; 401 führt zur Anmeldung, Schutzregeln kommen als Meldung des Servers zurück.
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api";
import { lexiconApi, type Lexicon, type SuggestionList } from "../lexicon";

export type LexiconState = {
  lexicon: Lexicon | null;
  suggestions: SuggestionList | null;
  busy: boolean;
  error: string | null;
  message: string | null;
  // Führt `work` aus, lädt neu und zeigt die zurückgegebene Meldung; true bei Erfolg.
  act: (work: () => Promise<string | null>) => Promise<boolean>;
};

export function useLexicon(onLogout: () => void): LexiconState {
  const [lexicon, setLexicon] = useState<Lexicon | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionList | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const logout = useRef(onLogout); // App reicht jedes Mal eine neue Funktion; act bleibt trotzdem gleich
  logout.current = onLogout;

  const act = useCallback(
    async (work: () => Promise<string | null>) => {
      setBusy(true);
      setError(null);
      setMessage(null);
      try {
        const done = await work();
        const [list, found] = await Promise.all([lexiconApi.list(), lexiconApi.suggestions()]);
        setLexicon(list);
        setSuggestions(found);
        setMessage(done);
        return true;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) logout.current();
        else setError(e instanceof ApiError ? e.message : "Aktion fehlgeschlagen.");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  useEffect(() => {
    void act(async () => null);
  }, [act]);

  return { lexicon, suggestions, busy, error, message, act };
}
