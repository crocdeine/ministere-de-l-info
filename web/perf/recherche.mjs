// Scénario e2e de la recherche globale (lot A4), WebKit puis Chromium, sans fenêtre, sur le build
// servi par `vite preview` : raccourcis, saisie, flèches, Entrée, Échap, code postal, élu,
// aucun résultat, aucune erreur de console.
// Usage : node perf/recherche.mjs   (données : export complet avec recherche.json.gz)
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { chromium, webkit } from "playwright-core";

const PORT = 4176;
const BASE = `http://127.0.0.1:${PORT}/`;
const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], { stdio: "ignore" });
for (let i = 0; i < 100; i++) {
  if (await fetch(BASE).then((r) => r.ok, () => false)) break;
  await new Promise((r) => setTimeout(r, 100));
}

const index = JSON.parse(gunzipSync(readFileSync("dist/data/recherche.json.gz")));
const elu = index.lignes.find((l) => l[0] === "u");
const echecs = [];
const verifie = (nom, ok, detail = "") => !ok && echecs.push(`${nom} ${detail}`);

for (const [nom, type] of [["webkit", webkit], ["chromium", chromium]]) {
  const nav = await type.launch({ headless: true });
  try {
    const page = await nav.newPage({ viewport: { width: 1280, height: 900 } });
    const erreurs = [];
    page.on("console", (m) => m.type() === "error" && erreurs.push(m.text()));
    page.on("pageerror", (e) => erreurs.push(String(e)));
    const champ = page.locator('input[role="combobox"]');
    const options = page.getByRole("option");

    await page.goto(`${BASE}#/elections`);
    await champ.waitFor({ timeout: 15000 });
    await page.locator(".page h1").first().waitFor({ timeout: 15000 });

    // 1. Raccourcis : ⌘K / Ctrl+K, puis « / » hors d'un champ.
    await page.keyboard.press("ControlOrMeta+k");
    verifie(`${nom} raccourci K`, await champ.evaluate((e) => e === document.activeElement));
    await page.keyboard.press("Escape");
    await champ.evaluate((e) => e.blur());
    await page.keyboard.press("/");
    verifie(`${nom} raccourci /`, await champ.evaluate((e) => e === document.activeElement));

    // 2. Saisie tolérante (« St-Etienne »), liste, homonymes départagés par le département.
    await champ.fill("St-Etienne");
    await options.first().waitFor({ timeout: 10000 });
    verifie(`${nom} expanded`, (await champ.getAttribute("aria-expanded")) === "true");
    const premier = (await options.first().textContent()) ?? "";
    verifie(`${nom} saint-etienne`, premier.startsWith("Saint-Étienne") && /\(\d{2}\)/.test(premier), premier);

    // 3. Flèches puis Entrée : la fiche s'ouvre (URL).
    await page.keyboard.press("ArrowDown");
    const actif = await champ.getAttribute("aria-activedescendant");
    verifie(`${nom} activedescendant`, !!actif && (await page.locator(`#${actif}`).getAttribute("aria-selected")) === "true");
    await page.keyboard.press("Enter");
    await page.locator("h1", { hasText: "Saint-Étienne" }).waitFor({ timeout: 15000 }).catch(() => echecs.push(`${nom} fiche Saint-Étienne`));
    verifie(`${nom} URL`, page.url().includes("#/commune?code=42218"), page.url());

    // 4. Code postal : Amiens (80000), ouverture avec Entrée sans flèche.
    await page.keyboard.press("ControlOrMeta+k");
    await champ.fill("80000");
    await options.first().waitFor({ timeout: 5000 });
    verifie(`${nom} code postal`, ((await options.first().textContent()) ?? "").includes("code postal 80000"));
    await page.keyboard.press("Enter");
    await page.locator("h1", { hasText: "Amiens" }).waitFor({ timeout: 15000 }).catch(() => echecs.push(`${nom} fiche Amiens`));

    // 5. Échap : ferme la liste en gardant le texte, puis efface au second appui.
    await page.keyboard.press("ControlOrMeta+k");
    await champ.fill("Somme");
    await options.first().waitFor({ timeout: 5000 });
    verifie(`${nom} département`, ((await options.first().textContent()) ?? "").startsWith("Somme"));
    await page.keyboard.press("Escape");
    verifie(`${nom} échap ferme`, (await champ.getAttribute("aria-expanded")) === "false" && (await champ.inputValue()) === "Somme");
    await page.keyboard.press("Escape");
    verifie(`${nom} échap efface`, (await champ.inputValue()) === "");

    // 6. Élu : renvoi vers la fiche d'une commune, sans date de naissance ni libellé politique.
    await champ.fill(elu[2]);
    await options.first().waitFor({ timeout: 5000 });
    const texteElu = (await page.getByRole("listbox").textContent()) ?? "";
    verifie(`${nom} élu`, texteElu.includes(elu[2]) && /Député|Sénateur/.test(texteElu), texteElu.slice(0, 120));
    await page.keyboard.press("Enter");
    await page.waitForURL(new RegExp(`#/commune\\?code=${elu[6]}`), { timeout: 5000 }).catch(() => echecs.push(`${nom} URL élu ${elu[6]}`));

    // 7. Aucun résultat : message, jamais de liste vide silencieuse.
    await page.keyboard.press("ControlOrMeta+k");
    await champ.fill("zzzzqx");
    await page.getByText("Aucun résultat pour").waitFor({ timeout: 5000 }).catch(() => echecs.push(`${nom} aucun résultat`));

    verifie(`${nom} console`, erreurs.length === 0, erreurs.join(" | ").slice(0, 300));
  } finally {
    await nav.close();
  }
}
serveur.kill();
if (echecs.length) {
  console.log("ÉCHEC\n" + echecs.join("\n"));
  process.exit(1);
}
console.log("OK : recherche globale (WebKit, Chromium)");
