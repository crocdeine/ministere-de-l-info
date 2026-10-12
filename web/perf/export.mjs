// Scénario e2e des exports CSV (lot A6), WebKit puis Chromium, sans fenêtre, sur `vite preview` :
// téléchargement réel de chaque CSV, relecture du fichier (BOM, en-tête, codes en texte, n.d. vide).
// Usage : node perf/export.mjs   (données : export des départements 80 et 75 au moins)
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { chromium, webkit } from "playwright-core";

const PORT = 4176;
const BASE = `http://127.0.0.1:${PORT}/`;
const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], { stdio: "ignore" });
for (let i = 0; i < 100; i++) {
  if (await fetch(BASE).then((r) => r.ok, () => false)) break;
  await new Promise((r) => setTimeout(r, 100));
}

const echecs = [];
const verifie = (nom, ok, detail = "") => !ok && echecs.push(`${nom} ${detail}`);

/** Relecteur RFC 4180 (« ; »), lignes `#` à part. */
function lire(texte) {
  const lignes = [];
  let l = [], c = "", q = false;
  for (let i = 0; i < texte.length; i++) {
    const x = texte[i];
    if (q) {
      if (x === '"' && texte[i + 1] === '"') (c += '"', i++);
      else if (x === '"') q = false;
      else c += x;
    } else if (x === '"') q = true;
    else if (x === ";") (l.push(c), (c = ""));
    else if (x === "\r") continue;
    else if (x === "\n") (l.push(c), lignes.push(l), (l = []), (c = ""));
    else c += x;
  }
  return { commentaires: lignes.filter((r) => r[0].startsWith("#")).map((r) => r[0]), table: lignes.filter((r) => !r[0].startsWith("#")) };
}

async function telecharge(page, nom, declencheur) {
  const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 20000 }), declencheur()]);
  const chemin = await dl.path();
  const brut = await readFile(chemin);
  const texte = brut.toString("utf8");
  verifie(`${nom} BOM`, brut[0] === 0xef && brut[1] === 0xbb && brut[2] === 0xbf);
  verifie(`${nom} nom`, /^ministere-info_[\w.-]+_\d{4}-\d{2}-\d{2}\.csv$/.test(dl.suggestedFilename()), dl.suggestedFilename());
  const { commentaires, table } = lire(texte.replace(/^﻿/, ""));
  const tout = commentaires.join("\n");
  for (const mot of ["# Source :", "# Licence :", "ODbL", "# Données du :", "# Export du :", "# Méthode :", "Classement des blocs"])
    verifie(`${nom} en-tête ${mot}`, tout.includes(mot));
  verifie(`${nom} pas de valeur brute`, !/undefined|NaN|null/.test(texte));
  const largeur = table[0].length;
  verifie(`${nom} lignes de même largeur`, table.every((r) => r.length === largeur));
  return { table, dl };
}

for (const [nom, type] of [["webkit", webkit], ["chromium", chromium]]) {
  const nav = await type.launch({ headless: true });
  try {
    const ctx = await nav.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    const erreurs = [];
    page.on("console", (m) => m.type() === "error" && erreurs.push(m.text()));
    page.on("pageerror", (e) => erreurs.push(String(e)));

    // 1. Fiche : historique (tous types pour avoir des n.d.) et bureaux de vote.
    await page.goto(`${BASE}#/commune?code=80021`);
    await page.locator("h1", { hasText: "Amiens" }).waitFor({ timeout: 15000 });
    await page.selectOption("#fiche-type", "");
    await page.selectOption("#fiche-tour", "0");
    const h = await telecharge(page, `${nom} historique`, () => page.getByRole("button", { name: "Télécharger (CSV)" }).first().click());
    verifie(`${nom} historique colonnes`, h.table[0].slice(0, 4).join("|") === "Code INSEE|Commune|Scrutin|Méthode", h.table[0].join("|"));
    verifie(`${nom} historique lignes`, h.table.length > 10, String(h.table.length));
    verifie(`${nom} historique code`, h.table.slice(1).every((r) => r[0] === "80021" && r[1] === "Amiens"));
    verifie(`${nom} historique nom`, h.dl.suggestedFilename().includes("_historique_80021_"), h.dl.suggestedFilename());

    await page.locator(".details-bv summary").click();
    await page.locator(".details-bv table").waitFor({ timeout: 10000 });
    const b = await telecharge(page, `${nom} bureaux`, () => page.locator(".details-bv").getByRole("button", { name: "Télécharger (CSV)" }).click());
    verifie(`${nom} bureaux lignes`, b.table.length > 50, String(b.table.length));
    verifie(`${nom} bureaux colonnes`, b.table[0][3] === "Bureau", b.table[0].join("|"));

    // 2. Élections : une ligne par commune, codes en texte (zéros conservés, 2A/2B), absences vides.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t1`);
    await page.getByRole("button", { name: "Télécharger (CSV)" }).waitFor({ timeout: 15000 });
    const e = await telecharge(page, `${nom} scrutin`, () => page.getByRole("button", { name: "Télécharger (CSV)" }).click());
    verifie(`${nom} scrutin lignes`, e.table.length > 100, String(e.table.length));
    verifie(`${nom} scrutin Amiens`, e.table.some((r) => r[0] === "80021" && r[1] === "Amiens" && /^\d+,\d$|^\d+,\d\d$|^\d+$/.test(r[3])));
    verifie(`${nom} scrutin codes`, e.table.slice(1).every((r) => /^(\d{5}|2[AB]\d{3})$/.test(r[0])));
    verifie(`${nom} scrutin absences`, e.table.slice(1).every((r) => r[2] !== "n.d." || (r[3] === "" && r[4] === "")), "n.d. avec valeur");

    verifie(`${nom} console`, erreurs.length === 0, erreurs.slice(0, 3).join(" | "));
  } catch (err) {
    echecs.push(`${nom} exception ${err}`);
  } finally {
    await nav.close();
  }
}
serveur.kill();
console.log(echecs.length ? `ÉCHEC\n${echecs.join("\n")}` : "OK : exports CSV (WebKit, Chromium)");
process.exit(echecs.length ? 1 : 0);
