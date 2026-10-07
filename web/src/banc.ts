// Banc de mesure du prototype A0 (actif seulement avec ?banc=… ou VITE_BANC au build).
// Résultats envoyés en POST à un écouteur local (`rapport=http://127.0.0.1:8765`).
import type { Map as CarteML } from "maplibre-gl";
import type { Meta } from "./donnees";
import { urlDonnees } from "./donnees";
import type { Reponse } from "./worker/details";

export const PARAMS = new URLSearchParams(location.search || import.meta.env.VITE_BANC || "");
export const BANC = PARAMS.has("banc");

// Build de mesure Tauri (paramètres figés au build) : chaque lancement prend la stratégie suivante.
const ROTATION = ["paint&fondu=0", "etat&fondu=0", "couches&fondu=0", "couches&fondu=1"];
if (PARAMS.has("rotation")) {
  const k = Number(localStorage.getItem("banc-k") ?? 0);
  localStorage.setItem("banc-k", String(k + 1));
  const [strategie, fondu] = (ROTATION[k % ROTATION.length] ?? "").split("&fondu=");
  PARAMS.set("strategie", strategie ?? "paint");
  PARAMS.set("fondu", fondu ?? "0");
  PARAMS.set("etiquette", `tauri-${strategie}-f${fondu}-${Math.floor(k / ROTATION.length) + 1}`);
}

function envoyer(objet: unknown): void {
  const url = PARAMS.get("rapport");
  const corps = JSON.stringify(objet);
  console.info(corps);
  if (url) void fetch(url, { method: "POST", body: corps, mode: "no-cors" });
}

const attendre = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Première carte colorée : tuiles des communes chargées et dessinées. */
export function surveillerOuverture(m: CarteML): void {
  envoyer({ mesure: "demarrage", depuisNavigation: performance.now(), etiquette: PARAMS.get("etiquette") });
  void fetch(urlDonnees("communes.pmtiles"), { headers: { Range: "bytes=0-99" } })
    .then(async (r) =>
      envoyer({
        mesure: "test-plage",
        url: r.url,
        statut: r.status,
        longueur: r.headers.get("content-length"),
        plage: r.headers.get("content-range"),
        octets: (await r.arrayBuffer()).byteLength,
      }),
    )
    .catch((e: unknown) => envoyer({ mesure: "test-plage", erreur: String(e) }));
  addEventListener("error", (e) => envoyer({ mesure: "erreur-js", message: String(e.message) }));
  addEventListener("unhandledrejection", (e) => envoyer({ mesure: "rejet", message: String(e.reason) }));
  for (const ev of ["style.load", "load", "idle"] as const)
    m.once(ev, () => envoyer({ mesure: `evt-${ev}`, t: performance.now() }));
  m.once("sourcedata", (e) => envoyer({ mesure: "evt-sourcedata", t: performance.now(), source: e.sourceId }));
  m.on("error", (e) => envoyer({ mesure: "erreur", message: String(e.error?.message ?? e.error) }));
  const fin = () => {
    if (!m.isSourceLoaded("communes")) return;
    m.off("sourcedata", fin);
    m.once("render", () =>
      envoyer({
        mesure: "ouverture",
        epoch: performance.timeOrigin + performance.now(),
        depuisNavigation: performance.now(),
        docFin: (performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined)
          ?.responseEnd,
        ressources: performance.getEntriesByType("resource").map((r) => {
          const e = r as PerformanceResourceTiming;
          return [e.name.split("/").pop(), Math.round(e.startTime), Math.round(e.responseEnd), e.transferSize];
        }),
      }),
    );
  };
  m.on("sourcedata", fin);
}

async function details(worker: Worker, meta: Meta): Promise<unknown[]> {
  const res: unknown[] = [];
  for (let k = 0; k < 6; k++) {
    const format = k % 2 ? "bin" : "json";
    const ext = format === "bin" ? "bin" : "json";
    const rep = await new Promise<Reponse>((ok) => {
      worker.onmessage = (e: MessageEvent<Reponse>) => ok(e.data);
      worker.postMessage({
        type: "charger",
        format,
        url: urlDonnees(`detail/${meta.detail.scrutin}.${ext}`),
        urlCodes: urlDonnees("detail/codes.json"),
        colonnes: meta.detail.colonnes,
        nul: meta.detail.nul,
      });
    });
    res.push(rep);
  }
  return res;
}

/** 50 changements de scrutin, chacun mesuré du « clic » à l'événement `idle` suivant. */
export async function lancerBanc(
  m: CarteML,
  changer: (i: number) => void,
  meta: Meta,
  worker: Worker,
): Promise<void> {
  await new Promise((r) => (m.loaded() ? r(null) : m.once("idle", r)));
  await attendre(500);
  const n = meta.scrutins.length;
  const durees: number[] = [];
  const premiereImage: number[] = [];
  let i = n - 1;
  for (let k = 0; k < 50; k++) {
    i = (i + 7) % n;
    const t0 = performance.now();
    const image = new Promise<number>((r) => m.once("render", () => r(performance.now() - t0)));
    const inactif = new Promise<number>((r) => m.once("idle", () => r(performance.now() - t0)));
    changer(i);
    premiereImage.push(await image);
    durees.push(await inactif);
    await attendre(50);
  }
  const memoire = (performance as unknown as { memory?: { usedJSHeapSize: number } }).memory;
  envoyer({
    mesure: "changements",
    params: Object.fromEntries(PARAMS),
    idle: durees,
    premiereImage,
    tasJsMo: memoire ? memoire.usedJSHeapSize / 1e6 : null,
    details: await details(worker, meta),
  });
  envoyer({ mesure: "fin" });
}
