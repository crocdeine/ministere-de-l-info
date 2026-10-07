// Mesures de performance dans WebKit (Playwright, sans fenêtre) sur le build (`npm run build`),
// servi par `vite preview`. Budget ADR-0015 : ouverture < 1 s, changement de scrutin < 100 ms,
// données avant la 1re carte < 1,5 Mo (gzip). Sert aussi de test de fumée (carte colorée,
// légende, aucune erreur de console).
// Usage : node perf/mesure.mjs [--strict] [--changements 30] [--mouvement-reduit]
//   --strict : échec si un seuil d'échec est dépassé (sinon seules la fumée et le budget de
//   données font échouer ; les temps d'un exécuteur CI ne sont pas ceux d'un Mac).
import { execSync, spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { webkit } from "playwright-core";

const args = process.argv.slice(2);
const STRICT = args.includes("--strict");
const N = Number(args[args.indexOf("--changements") + 1]) || 30;
const REDUIT = args.includes("--mouvement-reduit"); // prefers-reduced-motion : aucun fondu attendu
const PORT = 4173;
const BUDGET = { ouvertureMs: [1000, 1500], changementMs: [100, 150], donneesKo: [1536, 3072] };

const serveur = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"], {
  stdio: "ignore",
});
const attendre = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 100; i++) {
  if (await fetch(`http://127.0.0.1:${PORT}/`).then((r) => r.ok, () => false)) break;
  await attendre(100);
}

const erreurs = [];
const reponses = [];
const nav = await webkit.launch({ headless: true });
let resultat;
try {
  const page = await nav.newPage({ viewport: { width: 1280, height: 860 }, reducedMotion: REDUIT ? "reduce" : "no-preference" });
  page.on("pageerror", (e) => erreurs.push(String(e)));
  page.on("console", (m) => m.type() === "error" && !m.text().includes("data.geopf.fr") && erreurs.push(m.text()));
  page.on("requestfinished", async (req) => {
    const debut = req.timing().startTime; // horloge murale (ms), comme performance.timeOrigin
    const url = req.url();
    if (!url.includes("/data/") && !/\.(m?js)$/.test(url)) return;
    const corps = await (await req.response())?.body().catch(() => null);
    if (corps) reponses.push({ url, debut, brut: corps.length, gzip: Math.min(corps.length, gzipSync(corps).length) });
  });
  await page.goto(`http://127.0.0.1:${PORT}/?mesure=1${process.env.MESURE_PARAMS ?? ""}#/elections`);
  await page.waitForFunction(() => window.__mesure?.premiere !== undefined, null, { timeout: 30000 });
  const { premiere, origine, n } = await page.evaluate(() => ({
    premiere: window.__mesure.premiere,
    origine: performance.timeOrigin,
    n: window.__mesure.scrutins,
  }));
  await attendre(200); // derniers événements requestfinished
  const avant = reponses.filter((r) => r.debut <= origine + premiere);
  const somme = (l, f) => l.reduce((s, r) => s + r[f], 0) / 1024;
  const donnees = avant.filter((r) => r.url.includes("/data/"));
  const js = avant.filter((r) => !r.url.includes("/data/"));

  // Fumée : légende et étiquette de méthode présentes.
  const legende = await page.locator(".legende li").count();
  const etiquette = await page.locator(".etiquette-methode").textContent();
  if (legende < 10) erreurs.push(`légende incomplète (${legende} entrées)`);

  const changements = [];
  for (let k = 1; k <= N; k++) {
    const i = (k * 7) % n;
    const avantN = await page.evaluate(() => window.__mesure.changements.length);
    await page.evaluate((x) => window.__mesure.choisir(x), i);
    await page.waitForFunction((a) => window.__mesure.changements.length > a, avantN, { timeout: 10000 }).catch(() => null);
    const c = await page.evaluate(() => window.__mesure.changements.at(-1));
    if (c) changements.push(c);
    await attendre(300); // fondu (220 ms) terminé avant le changement suivant
  }
  const ms = changements.map((c) => c.ms).sort((a, b) => a - b);
  const q = (p) => ms[Math.min(ms.length - 1, Math.floor(p * ms.length))] ?? null;

  let memoireMo = null;
  if (process.platform === "darwin") {
    const pids = execSync("ps -axo pid=,command=").toString().split("\n").filter((l) => l.includes("playwright-navigateurs") || l.includes("ms-playwright")).map((l) => l.trim().split(/\s+/)[0]);
    memoireMo = 0;
    for (const pid of pids) {
      const m = /Footprint:\s*([\d.]+)\s*(KB|MB|GB)/.exec(execSync(`footprint ${pid} 2>/dev/null || true`).toString());
      if (m) memoireMo += Number(m[1]) * { KB: 1 / 1024, MB: 1, GB: 1024 }[m[2]];
    }
    memoireMo = Math.round(memoireMo);
  }

  resultat = {
    navigateur: `WebKit ${nav.version()} (Playwright, sans fenêtre)`,
    scrutins: n,
    ouvertureMs: Math.round(premiere),
    donneesAvantCarteKo: { gzip: Math.round(somme(donnees, "gzip")), brut: Math.round(somme(donnees, "brut")), requetes: donnees.length },
    // Le module partagé de MapLibre est redemandé par chaque worker (plusieurs) : `uniques`
    // compte chaque fichier une fois (ce que mesure perf/budget.mjs), `transferes` chaque requête.
    jsAvantCarteKo: {
      uniques: Math.round(somme([...new Map(js.map((r) => [r.url, r])).values()], "gzip")),
      transferes: Math.round(somme(js, "gzip")),
      requetes: js.map((r) => r.url.replace(/^.*\//, "")),
    },
    changementMs: { mediane: q(0.5), p90: q(0.9), max: ms.at(-1) ?? null, n: ms.length, avecFondu: changements.filter((c) => c.fondu).length },
    memoireMo,
    legende,
    etiquette,
    erreurs,
  };
} finally {
  await nav.close();
  serveur.kill();
}

console.log(JSON.stringify(resultat, null, 2));
mkdirSync("test-results", { recursive: true });
writeFileSync("test-results/mesure.json", JSON.stringify(resultat, null, 2));

const echecs = [...resultat.erreurs];
if (resultat.changementMs.n < N) echecs.push(`${N - resultat.changementMs.n} changements sans rendu`);
if (REDUIT && resultat.changementMs.avecFondu > 0) echecs.push("fondu malgré prefers-reduced-motion");
if (resultat.donneesAvantCarteKo.gzip > BUDGET.donneesKo[0]) echecs.push("données avant la 1re carte > 1,5 Mo");
if (STRICT) {
  if (resultat.ouvertureMs > BUDGET.ouvertureMs[1]) echecs.push("ouverture > 1,5 s");
  if (resultat.changementMs.mediane > BUDGET.changementMs[1]) echecs.push("changement de scrutin > 150 ms");
}
if (echecs.length) {
  console.error(`ÉCHEC : ${echecs.join(" ; ")}`);
  process.exit(1);
}
