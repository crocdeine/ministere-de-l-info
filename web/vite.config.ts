import { copyFileSync, mkdirSync, readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

// MapLibre servi depuis ses fichiers ESM d'origine (voir src/maplibre.ts) : copiés dans
// public/vendor/ (non commité) au démarrage de `vite` et de `vite build`.
const FICHIERS_MAPLIBRE = ["maplibre-gl.mjs", "maplibre-gl-shared.mjs", "maplibre-gl-worker.mjs"];
const vendorMapLibre: Plugin = {
  name: "vendor-maplibre",
  buildStart() {
    const dossier = new URL("./public/vendor/", import.meta.url);
    mkdirSync(dossier, { recursive: true });
    for (const f of FICHIERS_MAPLIBRE)
      copyFileSync(new URL(`./node_modules/maplibre-gl/dist/${f}`, import.meta.url), new URL(f, dossier));
  },
};

// CSP de l'application Tauri appliquée aussi par `vite preview` : le test de fumée WebKit
// (perf/mesure.mjs) vérifie ainsi qu'aucune ressource n'est bloquée par la politique de l'app.
const csp = Object.entries(
  JSON.parse(readFileSync(new URL("./src-tauri/tauri.conf.json", import.meta.url), "utf8")).app.security
    .csp as Record<string, string>,
)
  .map(([k, v]) => `${k} ${v}`)
  .join("; ");

export default defineConfig({
  plugins: [react(), vendorMapLibre],
  // Chemins relatifs : le build s'ouvre depuis n'importe quel dossier (Tauri, hébergement statique).
  base: "./",
  // tokens.css est importé tel quel depuis le skill du design system (hors de web/).
  server: { fs: { allow: [".."] } },
  worker: { format: "es" },
  preview: { headers: { "Content-Security-Policy": csp } },
});
