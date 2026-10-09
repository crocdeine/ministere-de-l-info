/// <reference lib="webworker" />
// Résultats détaillés et recherche de commune, hors du thread principal : JSON gzip vérifiés
// (SHA256 du manifeste), décompressés et décodés ici.
import { type ColonnesScrutin, lireJsonGz } from "../donnees";
import { rechercherCommunes } from "../recherche";

/** Fichier à lire : URL, empreinte attendue, nom affiché en cas d'erreur. */
export type Fichier = { url: string; sha256: string | undefined; nom: string };

export type Demande =
  | { type: "precharger"; communes: Fichier; scrutin: string; fichier: Fichier }
  | { type: "commune"; communes: Fichier; scrutin: string; fichier: Fichier; code: string }
  | { type: "rechercher"; communes: Fichier; texte: string };

export type Valeurs = Record<string, number | string | null>;

export type Reponse =
  | { type: "commune"; code: string; scrutin: string; nom: string | null; valeurs: Valeurs | null; erreur?: string }
  | { type: "resultats"; texte: string; communes: { code: string; nom: string }[]; erreur?: string };

type Communes = { index: Map<string, number>; codes: string[]; noms: string[] };

let communes: Promise<Communes> | null = null;
const scrutins = new Map<string, Promise<ColonnesScrutin>>();
const GARDES = 4; // tours gardés en mémoire (≈ 1-2 Mo décodés chacun)

function lireCommunes(f: Fichier): Promise<Communes> {
  communes ??= lireJsonGz<{ codes: string[]; noms: string[] }>(f.url, f.sha256, f.nom).then((c) => ({
    index: new Map(c.codes.map((code, i) => [code, i])),
    codes: c.codes,
    noms: c.noms,
  }));
  return communes;
}

function lireScrutin(id: string, f: Fichier): Promise<ColonnesScrutin> {
  let p = scrutins.get(id);
  if (!p) {
    p = lireJsonGz<ColonnesScrutin>(f.url, f.sha256, f.nom);
    scrutins.set(id, p);
    for (const ancien of scrutins.keys()) {
      if (scrutins.size <= GARDES) break;
      scrutins.delete(ancien); // ordre d'insertion : le plus ancien d'abord
    }
  }
  return p;
}

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

self.onmessage = async (e: MessageEvent<Demande>) => {
  const d = e.data;
  if (d.type === "rechercher") {
    try {
      const c = await lireCommunes(d.communes);
      const rep: Reponse = { type: "resultats", texte: d.texte, communes: rechercherCommunes(c.codes, c.noms, d.texte) };
      self.postMessage(rep);
    } catch (err) {
      communes = null; // nouvel essai à la prochaine demande
      self.postMessage({ type: "resultats", texte: d.texte, communes: [], erreur: message(err) } satisfies Reponse);
    }
    return;
  }
  let c: Communes, s: ColonnesScrutin;
  try {
    [c, s] = await Promise.all([lireCommunes(d.communes), lireScrutin(d.scrutin, d.fichier)]);
  } catch (err) {
    // Fichier absent, altéré ou illisible : « n.d. » et message ; nouvel essai à la prochaine demande.
    communes = null;
    scrutins.delete(d.scrutin);
    if (d.type === "commune")
      self.postMessage({ type: "commune", code: d.code, scrutin: d.scrutin, nom: null, valeurs: null, erreur: message(err) } satisfies Reponse);
    return;
  }
  if (d.type !== "commune") return;
  const i = c.index.get(d.code);
  const rep: Reponse = {
    type: "commune",
    code: d.code,
    scrutin: d.scrutin,
    nom: i === undefined ? null : (c.noms[i] ?? null),
    valeurs: i === undefined ? null : Object.fromEntries(Object.entries(s).map(([k, v]) => [k, v[i] ?? null])),
  };
  self.postMessage(rep);
};
