// Dev-Mock der MedVox-API für `npm run dev:mock` (VITE_MOCK_API=1), solange
// der Server (Login, Transcribe, Transfer) noch nicht gemerged ist.
// Nur Entwicklung, landet nie im Build. Passwort im Mock: "praxis".
import type { Plugin } from "vite";

// Bewusst ohne @types/node (keine neue Abhängigkeit): minimale Strukturtypen.
type IncomingMessage = {
  url?: string;
  method?: string;
  headers: { cookie?: string };
  on(event: "data", cb: (chunk: Uint8Array) => void): void;
  on(event: "end", cb: () => void): void;
};
type ServerResponse = {
  writeHead(status: number, headers: Record<string, string>): void;
  end(body?: string): void;
};

const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const TTL_MS = 15 * 60 * 1000;
const transfers = new Map<string, { transcript: string; codes: string[]; created_at: string; expires: number }>();

function send(res: ServerResponse, status: number, body?: unknown, headers: Record<string, string> = {}) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", ...headers });
  res.end(body === undefined ? "" : JSON.stringify(body));
}

function readBody(req: IncomingMessage): Promise<Uint8Array> {
  return new Promise((resolve) => {
    const chunks: Uint8Array[] = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const out = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
      let offset = 0;
      for (const c of chunks) {
        out.set(c, offset);
        offset += c.length;
      }
      resolve(out);
    });
  });
}

const text = (bytes: Uint8Array) => new TextDecoder().decode(bytes);

function loggedIn(req: IncomingMessage): boolean {
  return /(^|;\s*)medvox_session=dev/.test(req.headers.cookie ?? "");
}

function newCode(): string {
  let code = "";
  for (let i = 0; i < 6; i++) code += ALPHABET[Math.floor(Math.random() * ALPHABET.length)];
  return code;
}

async function handle(req: IncomingMessage, res: ServerResponse): Promise<boolean> {
  const url = new URL(req.url ?? "/", "http://localhost");
  const path = url.pathname;
  const method = req.method ?? "GET";

  if (path === "/api/v1/health") {
    send(res, 200, { status: "ok", whisper: "ok" });
  } else if (path === "/api/v1/login" && method === "POST") {
    const body = JSON.parse(text(await readBody(req)) || "{}") as { password?: string };
    if (body.password !== "praxis") return send(res, 401, { detail: "Passwort falsch." }), true;
    send(res, 204, undefined, { "Set-Cookie": "medvox_session=dev; Path=/; HttpOnly; SameSite=Strict" });
  } else if (path === "/api/v1/logout" && method === "POST") {
    send(res, 204, undefined, { "Set-Cookie": "medvox_session=; Path=/; Max-Age=0" });
  } else if (path === "/api/v1/session") {
    loggedIn(req) ? send(res, 200, { user: "praxis" }) : send(res, 401, { detail: "Nicht angemeldet." });
  } else if (path === "/api/v1/transcribe" && method === "POST") {
    if (!loggedIn(req)) return send(res, 401, { detail: "Nicht angemeldet." }), true;
    const raw = await readBody(req);
    if (raw.length > 10 * 1024 * 1024) return send(res, 413, { detail: "Aufnahme zu groß." }), true;
    await new Promise((r) => setTimeout(r, 800));
    send(res, 200, {
      transcript: `Mock-Transkript (${Math.round(raw.length / 1024)} kB Audio): Zahn drei sechs, Füllung okklusal.`,
      duration_s: 4.2,
      latency_s: 0.8,
      codes: [],
    });
  } else if (path === "/api/v1/transfer" && method === "POST") {
    if (!loggedIn(req)) return send(res, 401, { detail: "Nicht angemeldet." }), true;
    const body = JSON.parse(text(await readBody(req)) || "{}") as { transcript?: string; codes?: string[] };
    const now = Date.now();
    for (const [k, v] of transfers) if (v.expires < now) transfers.delete(k);
    const code = newCode();
    transfers.set(code, {
      transcript: body.transcript ?? "",
      codes: body.codes ?? [],
      created_at: new Date(now).toISOString(),
      expires: now + TTL_MS,
    });
    send(res, 200, { code, expires_at: new Date(now + TTL_MS).toISOString() });
  } else if (path.startsWith("/api/v1/transfer/") && method === "GET") {
    const entry = transfers.get(path.slice("/api/v1/transfer/".length).toUpperCase());
    if (!entry || entry.expires < Date.now()) return send(res, 404, { detail: "Kein Diktat unter diesem Code." }), true;
    send(res, 200, { transcript: entry.transcript, codes: entry.codes, created_at: entry.created_at });
  } else {
    return false;
  }
  return true;
}

export function mockApi(): Plugin {
  return {
    name: "medvox-mock-api",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const r = req as unknown as IncomingMessage;
        if (!r.url?.startsWith("/api/")) return next();
        handle(r, res as unknown as ServerResponse).then((done) => done || next(), next);
      });
    },
  };
}
