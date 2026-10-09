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
const location_ok = (h) => h.startsWith("#/elections?scrutin=") && !h.includes("commune");
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

    // 3. Valeurs invalides : jamais d'écran vide ; la vue affichée = scrutin par défaut = URL canonique.
    const avis = page.locator(".avis p");
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t2`);
    await page.waitForFunction(() => document.querySelector("input[name=tour]:checked")?.value === "2");
    verifie(`${nom} avis vide`, (await avis.count()) === 0 && (await page.locator(".avis[role=status]").count()) === 1);
    await page.goto(`${BASE}#/elections?scrutin=1999_xxx_t9&commune=1001`);
    await page.waitForFunction(() => !location.hash.includes("1999"));
    const v4 = await vue();
    verifie(`${nom} scrutin par défaut affiché`, v4.tour === "1" && location_ok(await page.evaluate(() => location.hash)), JSON.stringify(v4));
    await avis.first().waitFor();
    verifie(`${nom} avis`, (await avis.count()) === 2 && (await page.locator(".carte").count()) === 1);
    // L'avis disparaît dès que l'URL est valide.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t2`);
    await page.waitForFunction(() => document.querySelectorAll(".avis p").length === 0);

    // 5. Code de 5 chiffres inconnu : avis « inconnue », pas de « Chargement… » infini.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t1&commune=99999`);
    await page.getByText("inconnue dans les données").waitFor({ timeout: 10000 }).catch(() => echecs.push(`${nom} commune inconnue sans avis`));
    verifie(`${nom} pas de chargement infini`, !((await page.locator(".commune-choisie").textContent()) ?? "").includes("Chargement"));

    // 6. Page inconnue : hachage canonique.
    await page.goto(`${BASE}#/nimporte`);
    await page.waitForFunction(() => location.hash.startsWith("#/elections"));

    // Copie impossible (presse-papiers absent) : message et adresse visible.
    const p2 = await nav.newPage();
    await p2.addInitScript(() => Object.defineProperty(navigator, "clipboard", { value: undefined }));
    await p2.goto(`${BASE}#/elections?scrutin=2022_pres_t1`);
    await p2.getByRole("button", { name: /Copier le lien/ }).click();
    await p2.getByText("Copie impossible").waitFor({ timeout: 5000 }).catch(() => echecs.push(`${nom} copie impossible sans message`));
  } catch (e) {
    echecs.push(`${nom} exception ${e}`);
  } finally {
    await nav.close();
  }
}
serveur.kill();
console.log(echecs.length ? `ÉCHEC\n${echecs.join("\n")}` : "OK : état dans l'URL (WebKit, Chromium)");
process.exit(echecs.length ? 1 : 0);
