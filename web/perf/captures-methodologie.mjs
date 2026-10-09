// Captures du panneau Méthodologie (WebKit sans fenêtre). Usage : node perf/captures-methodologie.mjs DOSSIER
// Vérifie aussi : ouverture depuis l'étiquette, ancre atteinte, tables chargées, fermeture (Échap).
import { spawn } from "node:child_process";
import { webkit } from "playwright-core";

const sortie = process.argv[2];
const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", "4175", "--strictPort"], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 1500));
const nav = await webkit.launch({ headless: true });
const erreurs = [];
try {
  for (const [nom, largeur] of [["bureau", 1280], ["mobile", 390]]) {
    const page = await nav.newPage({ viewport: { width: largeur, height: 900 } });
    page.on("pageerror", (e) => erreurs.push(String(e)));
    page.on("console", (m) => m.type() === "error" && erreurs.push(m.text()));
    await page.goto("http://127.0.0.1:4175/#/elections");
    await page.locator("button.etiquette-methode").click();
    await page.locator("dialog[open] #methode").waitFor({ timeout: 15000 });
    await page.locator("dialog[open] .meth-table td").first().waitFor({ timeout: 15000 });
    await new Promise((r) => setTimeout(r, 500));
    await page.screenshot({ path: `${sortie}/methodologie-${nom}.png` });
    if (nom === "bureau") {
      const lignes = await page.locator("dialog[open] .meth-compte").textContent();
      console.log("correspondances affichées :", lignes);
      await page.selectOption("#meth-annee", "toutes");
      console.log("toutes années :", await page.locator("dialog[open] .meth-compte").textContent());
      await page.locator("dialog[open] #correspondances").scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${sortie}/methodologie-correspondances.png` });
      await page.keyboard.press("Escape");
      if (await page.locator("dialog[open]").count()) throw new Error("panneau non refermé par Échap");
      await page.locator(".lien-methode").first().click();
      await page.locator("dialog[open] #blocs").waitFor({ timeout: 15000 });
      console.log("lien « Méthode » : panneau ouvert sur #blocs ; hash :", await page.evaluate(() => location.hash));
      const n = await page.locator("dialog").count();
      if (n !== 1) throw new Error(`${n} fenêtres <dialog> (attendu : 1)`);
      await page.mouse.click(20, 450); // fond, hors du panneau
      if (await page.locator("dialog[open]").count()) throw new Error("panneau non refermé par un clic sur le fond");
      console.log("une seule fenêtre ; fermeture par clic sur le fond : ok");
    }
  }
} finally {
  await nav.close();
  serveur.kill();
}
console.log(erreurs.length ? `Erreurs : ${erreurs.join(" | ")}` : "Aucune erreur de console.");
