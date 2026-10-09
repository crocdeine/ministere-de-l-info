// Fiche commune (lot A3) : lecture des fichiers par département, lignes de l'historique
// électoral et ruptures de comparabilité. Logique pure, sans DOM, testée par vitest.
import type { Manifeste, Scrutin } from "./donnees";

/** Colonnes de `departements/<dep>/communes.json.gz` ou `bureaux.json.gz`. */
export type ColonnesDep = Record<string, (number | string | null)[]>;

export type Elu = {
  chambre: "AN" | "SENAT";
  circo: string | null;
  prenom: string;
  nom: string;
  groupe: string | null;
  groupe_nom: string | null;
  bloc: string | null;
};

export type InfoCommune = {
  nom: string;
  epci: string | null;
  circos: string[];
  population: [number, number | null][];
  /** Rang du scrutin (chaîne) -> codes des anciennes communes rattachées. */
  fusions: Record<string, string[]>;
  /** `null` : hors périmètre (Hauts-de-France seulement). */
  economie: Record<string, (number | null)[]> | null;
};

export type FichesDep = {
  departement: { code: string; nom: string | null; region: string | null };
  communes: Record<string, InfoCommune>;
  elus: Elu[];
};

const RE_COMMUNE = /^(\d{5}|2[AB]\d{3})$/;

/** Code commune du hachage `#/commune?code=80021` ; `null` si absent, `""` si invalide. */
export function codeDepuisHash(hash: string): string | null {
  const code = new URLSearchParams(hash.split("?")[1] ?? "").get("code");
  if (code === null) return null;
  return RE_COMMUNE.test(code) ? code : "";
}

/** Dossier du département : `97x` pour l'outre-mer, sinon deux caractères (2A, 2B compris). */
export function departementDe(code: string, m: Manifeste): string | null {
  for (const d of [code.slice(0, 3), code.slice(0, 2)])
    if (`departements/${d}/fiches.json.gz` in m.fichiers) return d;
  return null;
}

export type Raison = "type" | "tour" | "grille" | "decoupage" | "perimetre" | "nuancage";

export const LIBELLES_RAISONS: Record<Raison, string> = {
  type: "type de scrutin",
  tour: "tour de scrutin",
  grille: "grille de classement des blocs",
  decoupage: "découpage des circonscriptions (2010)",
  perimetre: "périmètre communal (communes rattachées)",
  nuancage: "seuil de nuançage (candidats ou listes sans nuance)",
};

export type Ligne = {
  rang: number;
  scrutin: Scrutin;
  inscrits: number | null;
  votants: number | null;
  exprimes: number | null;
  /** Votants / inscrits, en %. */
  participation: number | null;
  /** Part des exprimés par bloc (et `NC`, non classé), en % ; `null` = n.d. */
  parts: Record<string, number | null>;
  /** Somme des voix supérieure aux exprimés (scrutin plurinominal) : parts non calculées. */
  plurinominal: boolean;
  /** Toutes les voix sont non classées (aucune nuance attribuée). */
  nonClasseSeul: boolean;
  anciennes: string[];
  /** Ruptures avec la ligne précédente de la même série affichée. */
  raisons: Raison[];
};

const nombre = (v: number | string | null | undefined) => (typeof v === "number" ? v : null);

/** Ligne `i` d'un fichier par département (commune ou bureau de vote). */
function ligne(m: Manifeste, cols: ColonnesDep, i: number, anciennes: (rang: number) => string[]): Ligne | null {
  const rang = nombre(cols.scrutin?.[i]);
  const scrutin = rang === null ? undefined : m.scrutins[rang];
  if (rang === null || !scrutin) return null;
  const voix = [...m.blocs.map((b) => b.code), "NC"];
  const get = (c: string) => nombre(cols[c]?.[i]);
  const inscrits = get("inscrits");
  const votants = get("votants");
  const exprimes = get("exprimes");
  const v = voix.map(get);
  const total = v.every((x) => x === null) ? null : v.reduce<number>((a, x) => a + (x ?? 0), 0);
  const plurinominal = total !== null && exprimes !== null && total > exprimes;
  const calculable = total !== null && total > 0 && exprimes !== null && exprimes > 0 && !plurinominal;
  return {
    rang,
    scrutin,
    inscrits,
    votants,
    exprimes,
    participation: inscrits && votants !== null ? (100 * votants) / inscrits : null,
    parts: Object.fromEntries(
      voix.map((c, j) => [c, calculable && v[j] !== null ? (100 * (v[j] as number)) / (exprimes as number) : null]),
    ),
    plurinominal,
    nonClasseSeul: total !== null && total > 0 && get("NC") === total,
    anciennes: anciennes(rang),
    raisons: [],
  };
}

/** Lignes d'une commune, dans l'ordre des scrutins (chronologique) ; `raisons` vides ici. */
export function lignesCommune(m: Manifeste, cols: ColonnesDep, code: string, info?: InfoCommune): Ligne[] {
  const lignes: Ligne[] = [];
  const codes = cols.code_commune ?? [];
  for (let i = 0; i < codes.length; i++) {
    if (codes[i] !== code) continue;
    const l = ligne(m, cols, i, (rang) => info?.fusions[String(rang)] ?? []);
    if (l) lignes.push(l);
  }
  return lignes.sort((a, b) => a.rang - b.rang);
}

/** Bureaux de vote d'une commune pour un scrutin (`bureaux.json.gz`), par code de bureau. */
export function lignesBureaux(m: Manifeste, cols: ColonnesDep, code: string, rang: number): (Ligne & { bv: string })[] {
  const r: (Ligne & { bv: string })[] = [];
  const codes = cols.code_commune ?? [];
  for (let i = 0; i < codes.length; i++) {
    if (codes[i] !== code || cols.scrutin?.[i] !== rang) continue;
    const l = ligne(m, cols, i, () => []);
    if (l) r.push({ ...l, bv: String(cols.code_bv?.[i] ?? "") });
  }
  return r;
}

/** Ruptures entre lignes consécutives d'une série (comparaison entre scrutins). */
export function avecRuptures(lignes: Ligne[]): Ligne[] {
  return lignes.map((l, i) => {
    const p = lignes[i - 1];
    if (!p) return { ...l, raisons: [] };
    const a = p.scrutin;
    const b = l.scrutin;
    const r: Raison[] = [];
    if (a.type !== b.type) r.push("type");
    if (a.tour !== b.tour) r.push("tour");
    if (a.legende !== b.legende) r.push("grille");
    if (a.type === "legi" && b.type === "legi" && a.ancien_decoupage !== b.ancien_decoupage) r.push("decoupage");
    if (p.anciennes.join() !== l.anciennes.join()) r.push("perimetre");
    if (p.nonClasseSeul !== l.nonClasseSeul) r.push("nuancage");
    return { ...l, raisons: r };
  });
}

/** Raisons distinctes d'une série (bandeau « Comparaison limitée »), dans l'ordre des libellés. */
export function raisonsSerie(lignes: Ligne[]): Raison[] {
  const toutes = new Set(lignes.flatMap((l) => l.raisons));
  return (Object.keys(LIBELLES_RAISONS) as Raison[]).filter((r) => toutes.has(r));
}

/** Filtre de la série : type (`""` = tous) et tour (`0` = tous). */
export function filtrer(lignes: Ligne[], type: string, tour: number): Ligne[] {
  return lignes.filter((l) => (!type || l.scrutin.type === type) && (!tour || l.scrutin.tour === tour));
}

/** Bloc seul en tête d'une ligne (`null` : n.d. ; `"="` : égalité). `NC` possible. */
export function blocEnTete(l: Ligne): string | null {
  const parts = Object.entries(l.parts).filter((e): e is [string, number] => e[1] !== null);
  if (parts.length === 0) return null;
  const max = Math.max(...parts.map((e) => e[1]));
  if (max <= 0) return null;
  const tete = parts.filter((e) => e[1] === max);
  return tete.length > 1 ? "=" : (tete[0]?.[0] ?? null);
}

/** Mention des communes rattachées (garde-fou : commune fusionnée signalée). */
export function mentionFusion(anciennes: string[]): string | null {
  if (anciennes.length === 0) return null;
  return anciennes.length === 1
    ? `Inclut les résultats de l'ancienne commune ${anciennes[0]} (code INSEE)`
    : `Inclut les résultats des anciennes communes ${anciennes.join(", ")} (codes INSEE)`;
}

/** Dernière valeur renseignée d'un indicateur économique : [année, valeur] ou `null`. */
export function derniereValeur(eco: Record<string, (number | null)[]>, cle: string): [number, number] | null {
  const annees = eco.annee ?? [];
  const valeurs = eco[cle] ?? [];
  for (let i = annees.length - 1; i >= 0; i--) {
    const a = annees[i];
    const v = valeurs[i];
    if (a != null && v != null) return [a, v];
  }
  return null;
}
