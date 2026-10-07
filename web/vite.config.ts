import { copyFileSync, mkdirSync } from "node:fs";
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

export default defineConfig({
  plugins: [react(), vendorMapLibre],
  // Chemins relatifs : le build s'ouvre depuis n'importe quel dossier (Tauri, hébergement statique).
  base: "./",
  // tokens.css est importé tel quel depuis le skill du design system (hors de web/).
  server: { fs: { allow: [".."] } },
  worker: { format: "es" },
});
