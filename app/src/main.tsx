import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/diktat.css";
import "./styles/status.css";
import "./styles/ergebnis.css";
import "./styles/ergebnis-extra.css";
import "./styles/rezeption.css";
import "./styles/patienten.css";
import "./styles/behandler.css";
import "./styles/korrektur.css";
import { applyTheme, loadTheme } from "./theme";

// Farbschema vor dem ersten Zeichnen setzen, damit nichts hell aufblitzt.
applyTheme(loadTheme());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Service Worker nur im Produktionsbuild: cached ausschließlich die App-Hülle.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* ohne SW läuft die App trotzdem */
    });
  });
}
