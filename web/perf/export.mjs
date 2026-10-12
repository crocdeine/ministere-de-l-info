// Scénario e2e des exports (lot A6), WebKit puis Chromium, sans fenêtre, sur `vite preview` :
// téléchargement réel de chaque export (Excel et CSV), relecture du fichier (BOM, tableau dès la
// ligne 1, notes, codes en texte, n.d. vide, cellules numériques d'Excel).
// Usage : node perf/export.mjs   (données : export des départements 80 et 75 au moins)
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { unzipSync, strFromU8 } from "fflate";
import { chromium, webkit } from "playwright-core";

const PORT = 4196;
const BASE = `http://127.0.0.1:${PORT}/`;
const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], { stdio: "ignore" });
for (let i = 0; i < 100; i++) {
  if (await fetch(BASE).then((r) => r.ok, () => false)) break;
  await new Promise((r) => setTimeout(r, 100));
}

const echecs = [];
const verifie = (nom, ok, detail = "") => !ok && echecs.push(`${nom} ${detail}`);

/** Relecteur RFC 4180 (« ; »). */
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
  return lignes;
}

/** Cellules d'une feuille xlsx : { ref -> { t: texte|nombre, v } }, lignes dans l'ordre. */
function feuille(xml) {
  const cellules = {};
  for (const [, ref, attrs, corps] of xml.matchAll(/<c r="([A-Z]+\d+)"([^>]*)>(.*?)<\/c>/g)) {
    const texte = /t="inlineStr"/.test(attrs);
    const v = texte ? (/<t[^>]*>(.*?)<\/t>/.exec(corps)?.[1] ?? "") : Number(/<v>(.*?)<\/v>/.exec(corps)?.[1]);
    cellules[ref] = { texte, v: texte ? v.replaceAll("&amp;", "&").replaceAll("&lt;", "<").replaceAll("&gt;", ">") : v };
  }
  return cellules;
}

async function telecharge(page, nom, declencheur) {
  const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 20000 }), declencheur()]);
  const brut = await readFile(await dl.path());
  return { brut, fichier: dl.suggestedFilename() };
}

/** CSV : BOM, tableau dès la ligne 1, ligne vide, notes « # ». */
function verifieCsv(nom, { brut, fichier }) {
  verifie(`${nom} nom`, /^ministere-info_[\w.-]+_\d{4}-\d{2}-\d{2}\.csv$/.test(fichier), fichier);
  verifie(`${nom} BOM`, brut[0] === 0xef && brut[1] === 0xbb && brut[2] === 0xbf);
  const texte = brut.toString("utf8").replace(/^﻿/, "");
  verifie(`${nom} pas de valeur brute`, !/undefined|NaN|null| , /.test(texte));
  const lignes = lire(texte);
  const vide = lignes.findIndex((l) => l.length === 1 && l[0] === "");
  verifie(`${nom} ligne vide avant les notes`, vide > 1, String(vide));
  const table = lignes.slice(0, vide);
  const fin = lignes.slice(vide + 1).filter((l) => l.length > 1);
  verifie(`${nom} tableau dès la ligne 1`, table[0][0] === "Code INSEE", table[0][0]);
  verifie(`${nom} largeur constante`, table.every((r) => r.length === table[0].length));
  verifie(`${nom} notes #`, fin.length > 8 && fin.every((r) => r[0].startsWith("# ")));
  const cles = fin.map((r) => r[0]);
  for (const k of ["# Titre", "# Source", "# Licence de la base", "# Données du", "# Export du", "# Méthode"])
    verifie(`${nom} note ${k}`, cles.includes(k));
  verifie(`${nom} ODbL`, fin.some((r) => r[1].includes("ODbL")));
  verifie(`${nom} classement`, cles.some((k) => k.startsWith("# Classement des blocs — ")));
  return table;
}

/** Excel : onglets Données et Notes, en-têtes ligne 1 figés, codes en texte, nombres numériques. */
function verifieXlsx(nom, { brut, fichier }) {
  verifie(`${nom} nom`, /^ministere-info_[\w.-]+_\d{4}-\d{2}-\d{2}\.xlsx$/.test(fichier), fichier);
  const z = unzipSync(new Uint8Array(brut));
  const d = strFromU8(z["xl/worksheets/sheet1.xml"]);
  verifie(`${nom} figé`, d.includes('state="frozen"'));
  verifie(`${nom} onglets`, /name="Données".*name="Notes"/.test(strFromU8(z["xl/workbook.xml"])));
  const c = feuille(d);
  verifie(`${nom} A1`, c.A1?.v === "Code INSEE", JSON.stringify(c.A1));
  verifie(`${nom} code en texte`, c.A2?.texte === true && /^(\d{5}|2[AB]\d{3})$/.test(c.A2.v), JSON.stringify(c.A2));
  const nombres = Object.entries(c).filter(([r, x]) => !x.texte && !r.endsWith("1"));
  verifie(`${nom} cellules numériques`, nombres.length > 5 && nombres.every(([, x]) => Number.isFinite(x.v)));
  const n = strFromU8(z["xl/worksheets/sheet2.xml"]);
  for (const mot of ["Licence de la base", "ODbL", "Méthode", "Classement des blocs — ", "Colonne — "])
    verifie(`${nom} notes ${mot}`, n.includes(mot));
  verifie(`${nom} pas d'artefact`, !/ , |undefined|NaN/.test(d + n));
  return c;
}

const bouton = (page, intitule, format) => page.getByRole("button", { name: `Télécharger ${intitule} (${format})` });

for (const [nom, type] of [["webkit", webkit], ["chromium", chromium]]) {
  const nav = await type.launch({ headless: true });
  try {
    const ctx = await nav.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    const erreurs = [];
    page.on("console", (m) => m.type() === "error" && erreurs.push(m.text()));
    page.on("pageerror", (e) => erreurs.push(String(e)));

    // 1. Fiche : historique (tous types, deux tours) en CSV puis Excel.
    await page.goto(`${BASE}#/commune?code=80021`);
    await page.locator("h1", { hasText: "Amiens" }).waitFor({ timeout: 15000 });
    await page.selectOption("#fiche-type", "");
    await page.selectOption("#fiche-tour", "0");
    const h = verifieCsv(`${nom} historique csv`, await telecharge(page, nom, () => bouton(page, "l'historique", "CSV").click()));
    verifie(`${nom} historique colonnes`, h[0].slice(0, 4).join("|") === "Code INSEE|Commune|Scrutin|Classement des blocs", h[0].join("|"));
    verifie(`${nom} historique lignes`, h.length > 10, String(h.length));
    verifie(`${nom} historique voix`, h[0].some((t) => t.startsWith("Voix ")) && h[0].includes("Votants") && h[0].includes("Exprimés"));
    verifie(`${nom} historique code`, h.slice(1).every((r) => r[0] === "80021" && r[1] === "Amiens"));
    verifie(`${nom} historique classement`, h.slice(1).every((r) => ["Grille officielle", "Reconstruction documentée"].includes(r[3])));
    const hx = verifieXlsx(`${nom} historique xlsx`, await telecharge(page, nom, () => bouton(page, "l'historique", "Excel").click()));
    verifie(`${nom} historique xlsx lignes`, Object.keys(hx).filter((r) => /^A\d+$/.test(r)).length === h.length, "");

    // 2. Bureaux de vote.
    await page.locator(".details-bv summary").click();
    await page.locator(".details-bv table").waitFor({ timeout: 10000 });
    const b = verifieCsv(`${nom} bureaux csv`, await telecharge(page, nom, () => bouton(page, "les bureaux de vote", "CSV").click()));
    verifie(`${nom} bureaux lignes`, b.length > 50, String(b.length));
    verifie(`${nom} bureaux colonnes`, b[0][3] === "Bureau de vote", b[0].join("|"));
    verifieXlsx(`${nom} bureaux xlsx`, await telecharge(page, nom, () => bouton(page, "les bureaux de vote", "Excel").click()));

    // 3. Élections : une ligne par commune, codes en texte (zéros, 2A/2B), absences vides.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t1`);
    await bouton(page, "le scrutin affiché", "CSV").waitFor({ timeout: 15000 });
    const e = verifieCsv(`${nom} scrutin csv`, await telecharge(page, nom, () => bouton(page, "le scrutin affiché", "CSV").click()));
    verifie(`${nom} scrutin lignes`, e.length > 100, String(e.length));
    verifie(`${nom} scrutin Amiens`, e.some((r) => r[0] === "80021" && r[1] === "Amiens" && /^\d+(,\d\d?)?$/.test(r[3])));
    verifie(`${nom} scrutin codes`, e.slice(1).every((r) => /^(\d{5}|2[AB]\d{3})$/.test(r[0])));
    verifie(`${nom} scrutin absences`, e.slice(1).every((r) => r[2] !== "n.d." || (r[3] === "" && r[4] === "")), "n.d. avec valeur");
    verifieXlsx(`${nom} scrutin xlsx`, await telecharge(page, nom, () => bouton(page, "le scrutin affiché", "Excel").click()));

    verifie(`${nom} console`, erreurs.length === 0, erreurs.slice(0, 3).join(" | "));
  } catch (err) {
    echecs.push(`${nom} exception ${err}`);
  } finally {
    await nav.close();
  }
}
serveur.kill();
console.log(echecs.length ? `ÉCHEC\n${echecs.join("\n")}` : "OK : exports Excel et CSV (WebKit, Chromium)");
process.exit(echecs.length ? 1 : 0);
