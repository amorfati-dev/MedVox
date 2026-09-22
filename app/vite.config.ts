import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { mockApi } from "./dev/mockApi";

// Entwicklung: /api geht per Proxy an den lokalen MedVox-Server (server/: `make dev`).
// Mit VITE_MOCK_API=1 (`npm run dev:mock`) beantwortet ein Mock die API selbst.
// Build: VITE_API_BASE (z. B. https://medvox.local) lässt die App gegen eine
// andere Origin laufen; leer = gleiche Origin (Caddy vor Server und App).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react(), ...(env.VITE_MOCK_API === "1" ? [mockApi()] : [])],
    server: {
      proxy: {
        "/api": "http://127.0.0.1:8000",
      },
    },
  };
});
