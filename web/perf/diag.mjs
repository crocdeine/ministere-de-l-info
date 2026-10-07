// Diagnostic jetable : captures d'écran (WebKit sans fenêtre).
import { spawn } from "node:child_process";
import { webkit } from "playwright-core";

const sortie = process.argv[2];
const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", "4174", "--strictPort"], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 1500));
const nav = await webkit.launch({ headless: true });
for (const [nom, largeur, hauteur] of [["bureau", 1280, 1400], ["mobile", 390, 1400]]) {
  const page = await nav.newPage({ viewport: { width: largeur, height: hauteur } });
  await page.goto("http://127.0.0.1:4174/?mesure=1#/elections");
  await page.waitForFunction(() => window.__mesure?.premiere !== undefined, null, { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 1500));
  if (nom === "bureau") {
    const carte = await page.locator(".carte-conteneur").boundingBox();
    await page.mouse.move(carte.x + carte.width * 0.55, carte.y + carte.height * 0.3);
    await new Promise((r) => setTimeout(r, 1500));
  }
  await page.screenshot({ path: `${sortie}/${nom}.png`, fullPage: true });
  if (nom === "bureau") {
    await page.selectOption("#type", "muni");
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: `${sortie}/muni.png`, fullPage: true });
    await page.goto("http://127.0.0.1:4174/#/economie");
    await new Promise((r) => setTimeout(r, 800));
    await page.screenshot({ path: `${sortie}/economie.png` });
  }
}
await nav.close();
serveur.kill();
