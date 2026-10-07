/// <reference lib="webworker" />
// Résultats détaillés (infobulle) : JSON gzip décompressés et décodés hors du thread principal.
import { type ColonnesScrutin, lireJsonGz } from "../donnees";

export type Demande =
  | { type: "precharger"; urlCommunes: string; scrutin: string; url: string }
  | { type: "commune"; urlCommunes: string; scrutin: string; url: string; code: string };

export type Reponse = {
  code: string;
  scrutin: string;
  nom: string | null;
  valeurs: Record<string, number | null> | null;
};

type Communes = { index: Map<string, number>; noms: string[] };

let communes: Promise<Communes> | null = null;
const scrutins = new Map<string, Promise<ColonnesScrutin>>();
const GARDES = 4; // scrutins gardés en mémoire (≈ 1-2 Mo décodés chacun)

function lireCommunes(url: string): Promise<Communes> {
  communes ??= lireJsonGz<{ codes: string[]; noms: string[] }>(url).then((c) => ({
    index: new Map(c.codes.map((code, i) => [code, i])),
    noms: c.noms,
  }));
  return communes;
}

function lireScrutin(id: string, url: string): Promise<ColonnesScrutin> {
  let p = scrutins.get(id);
  if (!p) {
    p = lireJsonGz<ColonnesScrutin>(url);
    scrutins.set(id, p);
    for (const ancien of scrutins.keys()) {
      if (scrutins.size <= GARDES) break;
      scrutins.delete(ancien); // ordre d'insertion : le plus ancien d'abord
    }
  }
  return p;
}

self.onmessage = async (e: MessageEvent<Demande>) => {
  const d = e.data;
  let c: Communes, s: ColonnesScrutin;
  try {
    [c, s] = await Promise.all([lireCommunes(d.urlCommunes), lireScrutin(d.scrutin, d.url)]);
  } catch {
    // Fichier absent ou illisible : l'infobulle affiche « n.d. » ; nouvel essai au prochain survol.
    communes = null;
    scrutins.delete(d.scrutin);
    if (d.type === "commune") self.postMessage({ code: d.code, scrutin: d.scrutin, nom: null, valeurs: null });
    return;
  }
  if (d.type !== "commune") return;
  const i = c.index.get(d.code);
  const rep: Reponse = {
    code: d.code,
    scrutin: d.scrutin,
    nom: i === undefined ? null : (c.noms[i] ?? null),
    valeurs:
      i === undefined ? null : Object.fromEntries(Object.entries(s).map(([k, v]) => [k, v[i] ?? null])),
  };
  self.postMessage(rep);
};
