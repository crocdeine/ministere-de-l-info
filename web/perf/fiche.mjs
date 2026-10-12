// Scénario e2e de la fiche commune (lot A3), WebKit puis Chromium, sans fenêtre, sur le build
// servi par `vite preview` : URL, carte et commune choisie -> fiche ; ruptures ; bureaux de vote ;
// clavier ; codes invalides ; aucune erreur de console.
// Usage : node perf/fiche.mjs   (données : export des départements 80 et 75 au moins)
import { spawn } from "node:child_process";
import { chromium, webkit } from "playwright-core";

const PORT = 4175;
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
    const page = await nav.newPage({ viewport: { width: 1280, height: 900 } });
    const erreurs = [];
    page.on("console", (m) => m.type() === "error" && erreurs.push(m.text()));
    page.on("pageerror", (e) => erreurs.push(String(e)));

    // 1. Lien direct : en-tête, chiffres-clés, tableau, sources, aucun « undefined »/« NaN ».
    await page.goto(`${BASE}#/commune?code=80021`);
    await page.locator("h1", { hasText: "Amiens" }).waitFor({ timeout: 15000 });
    const texte = (await page.locator("main").textContent()) ?? "";
    verifie(`${nom} valeurs brutes`, !/undefined|NaN|null/.test(texte));
    const lignes = await page.locator("table.tableau").first().locator("tbody tr").count();
    verifie(`${nom} tableau présidentielles`, lignes >= 5, String(lignes));
    verifie(`${nom} sources`, (await page.locator(".source").count()) >= 5);
    verifie(`${nom} deux circonscriptions`, texte.includes("1re circonscription") && texte.includes("2e circonscription"));
    verifie(`${nom} économie HdF`, texte.includes("Taux de pauvreté"));

    // 2. Tous les types : bandeau « Comparaison limitée ».
    await page.selectOption("#fiche-type", "");
    await page.getByText("Comparaison limitée").waitFor({ timeout: 5000 }).catch(() => echecs.push(`${nom} bandeau absent`));

    // 3. Tri au clavier (Tab jusqu'à l'en-tête, Entrée).
    const entete = page.locator("th button.tri", { hasText: "Participation" }).first();
    await entete.focus();
    await page.keyboard.press("Enter");
    const tri = await page.locator("th[aria-sort]").first().getAttribute("aria-sort");
    verifie(`${nom} tri clavier`, tri === "descending", String(tri));

    // 4. Bureaux de vote : chargés à l'ouverture seulement.
    await page.locator(".details-bv summary").focus();
    await page.keyboard.press("Enter");
    await page.locator(".details-bv table").waitFor({ timeout: 10000 });
    const bv = await page.locator(".details-bv tbody tr").count();
    verifie(`${nom} bureaux de vote`, bv > 50, String(bv));

    // 5. Paris (commune unique dans les résultats, 18 circonscriptions), hors HdF.
    await page.goto(`${BASE}#/commune?code=75056`);
    await page.locator("h1", { hasText: "Paris" }).waitFor({ timeout: 15000 });
    const paris = (await page.locator("main").textContent()) ?? "";
    verifie(`${nom} Paris économie hors périmètre`, paris.includes("Hauts-de-France uniquement"));
    verifie(`${nom} Paris circonscriptions`, paris.includes("18 circonscriptions"));

    // 5 bis. Commune fusionnée : nom de l'ancienne commune ; outre-mer : département nommé.
    await page.goto(`${BASE}#/commune?code=80155`);
    await page.locator("#fiche-type").waitFor({ timeout: 15000 });
    await page.selectOption("#fiche-type", "");
    await page.getByText("ancienne commune Yaucourt-Bussus (80830)").first().waitFor({ timeout: 5000 }).catch(() => echecs.push(`${nom} nom de l'ancienne commune`));
    await page.goto(`${BASE}#/commune?code=97502`);
    await page.locator("h1", { hasText: "Saint-Pierre" }).waitFor({ timeout: 15000 });
    verifie(`${nom} 975`, ((await page.locator("main").textContent()) ?? "").includes("Saint-Pierre-et-Miquelon (975)"));

    // 6. Codes invalide ou inconnu : message, jamais d'écran vide.
    await page.goto(`${BASE}#/commune?code=1001`);
    await page.getByText("Commune inconnue").waitFor({ timeout: 5000 }).catch(() => echecs.push(`${nom} code invalide`));
    await page.goto(`${BASE}#/commune?code=59350`);
    await page.getByText("Commune inconnue").waitFor({ timeout: 5000 }).catch(() => echecs.push(`${nom} département absent`));

    // 7. Commune choisie sur la page Élections -> lien vers la fiche.
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t1&commune=80021`);
    await page.getByRole("link", { name: "Ouvrir la fiche de la commune" }).click({ timeout: 15000 });
    await page.waitForFunction(() => location.hash === "#/commune?code=80021");
    await page.locator("h1", { hasText: "Amiens" }).waitFor({ timeout: 15000 });

    // 8. Clic sur la carte -> fiche de la commune cliquée (recherche d'un point couvert).
    await page.goto(`${BASE}#/elections?scrutin=2022_pres_t1`);
    const carte = page.locator(".carte-conteneur");
    await page.waitForFunction(() => document.querySelector(".carte-conteneur")?.getAttribute("aria-busy") === "false", null, { timeout: 30000 });
    await carte.scrollIntoViewIfNeeded();
    const b = await carte.boundingBox();
    let clique = false;
    for (let i = 1; b && i < b.width / 15 && !clique; i++)
      for (let j = 1; j < b.height / 15 && !clique; j++) {
        const x = b.x + 15 * i;
        const y = b.y + 15 * j;
        await page.mouse.move(x, y);
        if (await page.locator(".infobulle").count()) {
          await page.mouse.click(x, y);
          clique = true;
        }
      }
    verifie(`${nom} commune sous la souris`, clique);
    if (clique) await page.waitForFunction(() => /^#\/commune\?code=\w{5}$/.test(location.hash), null, { timeout: 5000 }).catch(() => echecs.push(`${nom} clic carte`));

    verifie(`${nom} console`, erreurs.length === 0, erreurs.slice(0, 3).join(" | "));
  } catch (e) {
    echecs.push(`${nom} exception ${e}`);
  } finally {
    await nav.close();
  }
}
serveur.kill();
console.log(echecs.length ? `ÉCHEC\n${echecs.join("\n")}` : "OK : fiche commune (WebKit, Chromium)");
process.exit(echecs.length ? 1 : 0);
