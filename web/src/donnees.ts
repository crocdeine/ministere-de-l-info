import type { FeatureCollection, Geometry } from "geojson";

// Types des fichiers produits par scripts/export_web.py, chargement et formats français.

export type Bloc = { code: string; libelle: string; couleur: string; couleur_trait: string };

export type Source = {
  donnees: string;
  producteur: string;
  licence: string;
  url: string;
  mention: string;
};

export type Meta = {
  date_export: string;
  sources: { elections: Source; ign: Source };
  legendes_classement: Record<string, string>;
  annees: number[];
  tours: number[];
  blocs: Bloc[];
  couleur_nd: string;
  echelle_score_max: number;
  bornes: [[number, number], [number, number]] | null;
  fond_carte: { url: string; attribution: string; opacite: number };
};

type Colonne = (number | null)[];

export type Scrutin = {
  annee: number;
  tour: number;
  inscrits: Colonne;
  votants: Colonne;
  exprimes: Colonne;
  voix: Record<string, Colonne>;
  chiffres: {
    communes: number | null;
    inscrits: number | null;
    participation: number | null;
    bloc_majoritaire: string | null;
  };
};

export type Resultats = { codes: string[]; scrutins: Record<string, Scrutin> };

export type PointEvolution = { annee: number; tour: number; bloc: string; pct: number | null };

export type Communes = FeatureCollection<Geometry, { code: string; nom: string }>;

export type Donnees = {
  meta: Meta;
  resultats: Resultats;
  evolution: PointEvolution[];
  communes: Communes;
};

async function lire<T>(fichier: string): Promise<T> {
  const r = await fetch(`${import.meta.env.BASE_URL}data/${fichier}`);
  if (!r.ok) throw new Error(`${fichier} : ${r.status}`);
  return (await r.json()) as T;
}

export async function chargerDonnees(): Promise<Donnees> {
  const [meta, resultats, evolution, communes] = await Promise.all([
    lire<Meta>("meta.json"),
    lire<Resultats>("resultats.json"),
    lire<PointEvolution[]>("evolution.json"),
    lire<Communes>("communes.geojson"),
  ]);
  return { meta, resultats, evolution, communes };
}

/** Bloc arrivé en tête dans une commune ; égalité signalée ; null si pas de résultat. */
export function blocDominant(
  s: Scrutin,
  i: number,
  blocs: Bloc[],
): { code: string; egalite: boolean } | null {
  let meilleur: string | null = null;
  let max = -1;
  let egalite = false;
  for (const b of blocs) {
    const v = s.voix[b.code]?.[i];
    if (v == null) continue;
    if (v > max) {
      max = v;
      meilleur = b.code;
      egalite = false;
    } else if (v === max) {
      egalite = true;
    }
  }
  return meilleur && max > 0 ? { code: meilleur, egalite } : null;
}

/** Part des exprimés (%) d'un bloc dans une commune ; null si non calculable. */
export function scoreBloc(s: Scrutin, i: number, bloc: string): number | null {
  const v = s.voix[bloc]?.[i];
  const e = s.exprimes[i];
  return v == null || e == null || e <= 0 ? null : (100 * v) / e;
}

export function participation(s: Scrutin, i: number): number | null {
  const ins = s.inscrits[i];
  const vot = s.votants[i];
  return ins == null || vot == null || ins <= 0 ? null : (100 * vot) / ins;
}

const fmtEntier = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const fmtPct = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const ND = "n.d.";

export function entier(n: number | null | undefined): string {
  return n == null ? ND : fmtEntier.format(n);
}

export function pct(n: number | null | undefined): string {
  return n == null ? ND : `${fmtPct.format(n)} %`;
}

export function libelleTour(t: number): string {
  return t === 1 ? "1er tour" : "2e tour";
}
