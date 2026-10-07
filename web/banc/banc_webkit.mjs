// Banc WebKit (Playwright, sans fenêtre) : 3 lancements à froid par stratégie.
import { execSync } from "node:child_process";
import { appendFileSync, readFileSync } from "node:fs";
import { webkit } from "playwright";

const MESURES = process.env.BANC_MESURES ?? "mesures.jsonl";
const CAS = (process.argv[2] ?? "paint:0,etat:0,couches:0,couches:1").split(",");
const N = Number(process.argv[3] ?? 3);
const lignes = () => readFileSync(MESURES, "utf8").split("\n").filter(Boolean);

for (let k = 1; k <= N; k++) {
  for (const cas of CAS) {
    const [strategie, fondu] = cas.split(":");
    const etiquette = `webkit-${strategie}-f${fondu}-${k}`;
    const n0 = lignes().length;
    const t0 = Date.now();
    const nav = await webkit.launch({ headless: true });
    const page = await nav.newPage({ viewport: { width: 1280, height: 860 } });
    await page.goto(
      `http://127.0.0.1:4173/?banc=1&strategie=${strategie}&fondu=${fondu}&etiquette=${etiquette}&rapport=http://127.0.0.1:8765/`,
    );
    let fini = false;
    for (let i = 0; i < 400 && !fini; i++) {
      await new Promise((r) => setTimeout(r, 500));
      fini = lignes().slice(n0).some((l) => l.includes('"fin"'));
    }
    // Mémoire : RSS cumulée des processus WebKit de Playwright (Mo).
    const ps = execSync("ps -axo rss=,command=").toString().split("\n");
    const rss = ps.filter((l) => l.includes("playwright-navigateurs")).reduce((s, l) => s + Number(l.trim().split(/\s+/)[0]), 0) / 1024;
    // Empreinte physique (footprint), comparable à la mesure Tauri du POC précédent.
    const pids = execSync("ps -axo pid=,command=").toString().split("\n")
      .filter((l) => l.includes("playwright-navigateurs")).map((l) => l.trim().split(/\s+/)[0]);
    let empreinte = 0;
    for (const pid of pids) {
      const m = /Footprint:\s*([\d.]+)\s*(KB|MB|GB)/.exec(execSync(`footprint ${pid} 2>/dev/null || true`).toString());
      if (m) empreinte += Number(m[1]) * { KB: 1 / 1024, MB: 1, GB: 1024 }[m[2]];
    }
    console.log(`  empreinte ${empreinte.toFixed(0)} Mo (${pids.length} processus)`);
    await nav.close();
    appendFileSync(
      MESURES,
      JSON.stringify({ corps: { mesure: "lancement", etiquette, t0, rssMo: rss, termine: fini } }) + "\n",
    );
    console.log(etiquette, fini ? "terminé" : "DÉLAI DÉPASSÉ", `RSS ${rss.toFixed(0)} Mo`);
  }
}
