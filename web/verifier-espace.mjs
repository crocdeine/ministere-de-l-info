// Garde d'espace disque avant `tauri build` (seuil : MINISTERE_ESPACE_MIN_GO, défaut 10 Go).
import { statfsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const minGo = Number(process.env.MINISTERE_ESPACE_MIN_GO ?? 10);
const racine = dirname(fileURLToPath(import.meta.url));
const cibles = [racine, resolve(process.env.CARGO_TARGET_DIR ?? racine)];
let ok = true;
for (const d of cibles) {
  const s = statfsSync(d);
  const libreGo = (s.bavail * s.bsize) / 1e9;
  if (libreGo < minGo) {
    console.error(
      `Espace disque insuffisant sur ${d} : ${libreGo.toFixed(2)} Go libres, seuil ${minGo} Go (MINISTERE_ESPACE_MIN_GO)`,
    );
    ok = false;
  }
}
process.exit(ok ? 0 : 1);
