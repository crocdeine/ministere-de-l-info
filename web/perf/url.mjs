// Scénario e2e de l'état dans l'URL (lot A2), WebKit puis Chromium, sans fenêtre, sur le build
// servi par `vite preview` : lien -> même vue au rechargement ; retour arrière ; valeurs invalides.
// Usage : node perf/url.mjs   (données : échantillon contenant Amiens, 80021)
import { spawn } from "node:child_process";
import { chromium, webkit } from "playwright-core";

const PORT = 4174;
const BASE = `http://127.0.0.1:${PORT}/`;
const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], { stdio: "ignore" });
for (let i = 0; i < 100; i++) {
  if (await fetch(BASE).then((r) => r.ok, () => false)) break;
  await new Promise((r) => setTimeout(r, 100));
}

const echecs = [];
const verifie = (nom, ok, detail = "") => !ok && echecs.push(`${nom} ${detail}`);

for (const [nom, type] of [["webkit", webkit], ["chromium", chromium]]) {
  const nav = await type.launch({ headless: true });
  try {
    const page = await nav.newPage();
    const vue = async () => ({
      annee: await page.locator("#annee").inputValue(),
      tour: await page.locator("input[name=tour]:checked").inputValue(),
      commune: ((await page.locator(".commune-choisie").textContent()) ?? "").includes("80021"),
    });
    const pret = () => page.locator("#annee").waitFor();

    // 1. Lien -> vue, puis rechargement.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t2&commune=80021`);
    await pret();
    const v1 = await vue();
    verifie(`${nom} lien`, v1.annee === "2022" && v1.tour === "2" && v1.commune, JSON.stringify(v1));
    await page.reload();
    await pret();
    const v2 = await vue();
    verifie(`${nom} rechargement`, JSON.stringify(v2) === JSON.stringify(v1), JSON.stringify(v2));

    // 2. Choix d'une commune -> URL (pushState) ; retour arrière -> commune retirée, scrutin conservé.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t1`);
    await page.reload();
    await pret();
    await page.fill("#commune", "Amiens");
    await page.locator(".liste-communes button").first().click();
    await page.waitForFunction(() => location.hash.includes("commune=80021"));
    await page.goBack();
    await page.waitForFunction(() => !location.hash.includes("commune="));
    const v3 = await vue();
    verifie(`${nom} retour arrière`, v3.tour === "1" && !v3.commune && (await page.locator(".commune-choisie strong").count()) === 0, JSON.stringify(v3));
    await page.goForward();
    await page.waitForFunction(() => location.hash.includes("commune=80021"));
    verifie(`${nom} avancer`, (await vue()).commune);

    // 3. Valeurs invalides : jamais d'écran vide, messages discrets.
    await page.goto(`${BASE}#/elections?scrutin=1999_xxx_t9&commune=1001`);
    await pret();
    await page.waitForTimeout(300);
    verifie(`${nom} invalides`, (await page.locator("p.aide[role=status]").count()) === 2 && (await page.locator(".carte").count()) === 1);
  } catch (e) {
    echecs.push(`${nom} exception ${e}`);
  } finally {
    await nav.close();
  }
}
serveur.kill();
console.log(echecs.length ? `ÉCHEC\n${echecs.join("\n")}` : "OK : état dans l'URL (WebKit, Chromium)");
process.exit(echecs.length ? 1 : 0);
