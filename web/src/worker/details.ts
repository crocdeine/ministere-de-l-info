/// <reference lib="webworker" />
// Résultats détaillés d'un scrutin (infobulle), décodés hors du thread principal.
// Deux formats comparés (tâche 4 du prototype A0) : JSON en colonnes, ou colonnes Int32 brutes.

export type Demande =
  | { type: "charger"; format: "json" | "bin"; url: string; urlCodes: string; colonnes: string[]; nul: number }
  | { type: "commune"; code: string };

export type Reponse =
  | { type: "pret"; format: string; octets: number; msLecture: number; msDecodage: number }
  | { type: "commune"; code: string; nom: string | null; valeurs: Record<string, number | null> | null };

let index = new Map<string, number>();
let noms: string[] = [];
let colonnes: string[] = [];
let valeur: (c: number, i: number) => number | null = () => null;

async function charger(d: Extract<Demande, { type: "charger" }>): Promise<Reponse> {
  if (index.size === 0) {
    const c = (await (await fetch(d.urlCodes)).json()) as { codes: string[]; noms: string[] };
    index = new Map(c.codes.map((code, i) => [code, i]));
    noms = c.noms;
  }
  const t0 = performance.now();
  const r = await fetch(d.url);
  const brut = await r.arrayBuffer();
  const t1 = performance.now();
  colonnes = d.colonnes;
  if (d.format === "bin") {
    const v = new Int32Array(brut);
    const n = index.size;
    valeur = (c, i) => {
      const x = v[c * n + i];
      return x === undefined || x === d.nul ? null : x;
    };
  } else {
    const o = JSON.parse(new TextDecoder().decode(brut)) as Record<string, (number | null)[]>;
    const cols = colonnes.map((c) => o[c]);
    valeur = (c, i) => cols[c]?.[i] ?? null;
  }
  return {
    type: "pret",
    format: d.format,
    octets: brut.byteLength,
    msLecture: t1 - t0,
    msDecodage: performance.now() - t1,
  };
}

self.onmessage = async (e: MessageEvent<Demande>) => {
  const d = e.data;
  if (d.type === "charger") {
    self.postMessage(await charger(d));
    return;
  }
  const i = index.get(d.code);
  const rep: Reponse =
    i === undefined
      ? { type: "commune", code: d.code, nom: null, valeurs: null }
      : {
          type: "commune",
          code: d.code,
          nom: noms[i] ?? null,
          valeurs: Object.fromEntries(colonnes.map((c, k) => [c, valeur(k, i)])),
        };
  self.postMessage(rep);
};
