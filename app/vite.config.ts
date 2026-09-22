import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Im Entwicklungsbetrieb leitet Vite alle /api-Aufrufe an den lokalen
// MedVox-Server weiter (server/: `make dev`).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
