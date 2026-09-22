import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Entwicklung: /api geht per Proxy an den lokalen MedVox-Server (server/: `make dev`).
// Im Betrieb liegen App und API hinter Caddy auf derselben Origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
