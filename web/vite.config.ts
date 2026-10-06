import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Chemins relatifs : le build s'ouvre depuis n'importe quel dossier (Tauri, hébergement statique).
  base: "./",
  // tokens.css est importé tel quel depuis le skill du design system (hors de web/).
  server: { fs: { allow: [".."] } },
  // MapLibre (~0,8 Mo) et Plot/d3 dominent le bundle : acceptable pour une app locale (Tauri).
  build: { chunkSizeWarningLimit: 1600 },
  worker: { format: "es" },
});
