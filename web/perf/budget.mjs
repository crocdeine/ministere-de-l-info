// Budget de taille du JS initial (ADR-0015) : JS chargé avant la première carte, compressé gzip.
// = point d'entrée (index-*.js) + MapLibre (vendor/*.mjs) + worker de détail. Échec si > cible.
// Usage : node perf/budget.mjs [dossier dist]   (après `npm run build`)
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const CIBLE_KO = 450;
const SEUIL_KO = 550;
const dist = process.argv[2] ?? "dist";
const ko = (f) => gzipSync(readFileSync(f), { level: 9 }).length / 1024;

const html = readFileSync(join(dist, "index.html"), "utf8");
const entree = [...html.matchAll(/src="\.\/(assets\/[^"]+\.js)"/g)].map((m) => m[1]);
const js = [
  ...entree,
  ...readdirSync(join(dist, "vendor")).map((f) => `vendor/${f}`),
  ...readdirSync(join(dist, "assets"))
    .filter((f) => f.endsWith(".js") && !entree.includes(`assets/${f}`))
    .map((f) => `assets/${f}`),
];
let total = 0;
for (const f of js) {
  const t = ko(join(dist, f));
  total += t;
  console.log(`${t.toFixed(1).padStart(7)} Ko  ${f}`);
}
const verdict = total <= CIBLE_KO ? "tenu" : total <= SEUIL_KO ? "cible dépassée" : "ÉCHEC";
console.log(`${total.toFixed(1).padStart(7)} Ko  JS initial gzip (cible ${CIBLE_KO}, seuil ${SEUIL_KO}) : ${verdict}`);
if (total > CIBLE_KO) process.exit(1);
