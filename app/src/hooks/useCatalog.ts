// Katalog je Patiententyp (GET /api/v1/catalog), einmal geladen und für die Sitzung gemerkt; ein Fehler
// wird nicht gemerkt, der nächste Aufruf versucht es neu. Für das Katalog-Blatt und den Ziffernvergleich.
import { useEffect, useState } from "react";
import { api, ApiError, type PatientType } from "../api";
import type { CatalogEntry } from "../catalog";

const cache = new Map<PatientType, Promise<CatalogEntry[]>>();

export function loadCatalog(type: PatientType): Promise<CatalogEntry[]> {
  let found = cache.get(type);
  if (!found) {
    found = api.catalog(type).then((list) => list.entries);
    found.catch(() => cache.delete(type));
    cache.set(type, found);
  }
  return found;
}

export type CatalogState = { entries: CatalogEntry[] | null; error: string | null };

// `type` null oder `wanted` false: nichts laden.
export function useCatalog(type: PatientType | null, wanted = true): CatalogState {
  const [state, setState] = useState<CatalogState & { type: PatientType | null }>({ entries: null, error: null, type: null });
  useEffect(() => {
    if (!type || !wanted) return;
    let alive = true;
    loadCatalog(type)
      .then((entries) => alive && setState({ entries, error: null, type }))
      .catch((e: unknown) => {
        if (alive) setState({ entries: null, error: e instanceof ApiError ? e.message : "Katalog nicht erreichbar.", type });
      });
    return () => {
      alive = false;
    };
  }, [type, wanted]);
  return state.type === type ? { entries: state.entries, error: state.error } : { entries: null, error: null };
}
