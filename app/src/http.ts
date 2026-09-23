// HTTP-Grundlage der MedVox-API: Fehler werden als ApiError mit deutscher Meldung geworfen,
// damit die Ansichten sie direkt anzeigen können.

export class ApiError extends Error {
  readonly status: number; // 0 = Netzwerk/Server nicht erreichbar

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const MESSAGES: Record<number, string> = {
  401: "Nicht angemeldet.",
  404: "Nicht gefunden.",
  410: "Dieses Diktat wurde bereits übertragen.",
  413: "Aufnahme zu lang (maximal 60 Sekunden).",
  415: "Audioformat wird vom Server nicht unterstützt.",
  429: "Zu viele Abfragen – bitte kurz warten.",
  502: "Praxis-Mac antwortet nicht – MedVox-Dienst auf dem Praxis-Mac prüfen.",
  503: "Whisper nicht bereit – Transkriptionsdienst auf dem Praxis-Mac prüfen.",
  504: "Praxis-Mac antwortet zu langsam – bitte erneut versuchen.",
};

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Server nicht erreichbar – WLAN und Praxis-Mac prüfen.");
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* Body ohne JSON */
    }
    throw new ApiError(res.status, detail || MESSAGES[res.status] || `Serverfehler (HTTP ${res.status}).`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function json(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
