import "@fontsource/hanken-grotesk/latin-400.css";
import "@fontsource/hanken-grotesk/latin-500.css";
import "@fontsource/hanken-grotesk/latin-600.css";
import "@fontsource/hanken-grotesk/latin-800.css";
import "@fontsource/hanken-grotesk/latin-900.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
// Tokens du design system, importés tels quels depuis le skill (source unique des valeurs).
import "../../.claude/skills/design-system-mi/tokens.css";
import "./styles.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

const racine = document.getElementById("root");
if (racine)
  createRoot(racine).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
