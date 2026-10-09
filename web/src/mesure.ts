// Mesures de performance (budget ADR-0015), actives seulement avec `?mesure=1` (ou la variable
// de compilation VITE_MESURE pour l'application Tauri, qui s'ouvre sans paramètre d'URL).
// Lues par web/perf/mesure.mjs (Playwright) via `window.__mesure`, ou envoyées à `rapport`.
import type { Rendu } from "./Carte";

const params = new URLSearchParams(location.search || (import.meta.env.VITE_MESURE ?? ""));
export const MESURE = params.has("mesure");

export type Journal = {
  premiere?: number;
  changements: Rendu[];
  choisir?: (i: number) => void;
  scrutins?: number;
};

export const journal: Journal = { changements: [] };
if (MESURE) (globalThis as unknown as { __mesure: Journal }).__mesure = journal;

export function noter(r: Rendu): void {
  if (!MESURE) return;
  if (r.type === "premiere") journal.premiere = r.ms;
  else journal.changements.push(r);
  const rapport = params.get("rapport");
  if (rapport) void fetch(rapport, { method: "POST", body: JSON.stringify(r) }).catch(() => {});
}
