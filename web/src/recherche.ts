// Recherche : choix simple d'une commune (page Élections), puis recherche globale (lot A4).

/** Minuscules, sans accents ni ponctuation : « Saint-Étienne » → « saint etienne ». */
export function normaliser(texte: string): string {
  return texte
    .replace(/œ/gi, "oe")
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/** Au plus `max` communes : code exact ou préfixe de code, puis nom commençant par le texte,
 * puis nom le contenant ; ordre alphabétique dans chaque groupe. */
export function rechercherCommunes(
  codes: string[],
  noms: string[],
  texte: string,
  max = 10,
): { code: string; nom: string }[] {
  const t = normaliser(texte);
  if (t.length < 2) return [];
  const groupes: [number, string, string][] = [];
  codes.forEach((code, i) => {
    const nom = noms[i] ?? code;
    const n = normaliser(nom);
    const rang = code.toLowerCase().startsWith(t) ? 0 : n.startsWith(t) ? 1 : n.includes(t) ? 2 : -1;
    if (rang >= 0) groupes.push([rang, nom, code]);
  });
  groupes.sort((a, b) => a[0] - b[0] || a[1].localeCompare(b[1], "fr"));
  return groupes.slice(0, max).map(([, nom, code]) => ({ code, nom }));
}

// ---- Recherche globale (lot A4) : index `recherche.json.gz`, filtrage linéaire sans bibliothèque.

export type TypeEntree = "c" | "d" | "e" | "u";
/** Ligne de l'index : commune, département, circonscription, élu. */
export type Entree = {
  type: TypeEntree;
  code: string;
  libelle: string;
  norm: string;
  dep: string;
  /** Commune : codes postaux séparés par une espace ; élu : « Député » ou « Sénateur ». */
  extra: string;
  /** Commune dont la fiche s'ouvre (null pour une commune : elle-même). */
  ref: string | null;
};
export type BrutIndex = {
  colonnes: string[];
  lignes: (string | null)[][];
  departements: Record<string, string>;
  codes_postaux: boolean;
};
export type Index = {
  entrees: Entree[];
  departements: Record<string, string>;
  codesPostaux: boolean;
  /** Nom d'une commune d'après son code (libellé des renvois). */
  communes: Map<string, string>;
};
export type Resultat = { entree: Entree; cible: string; codePostal?: string };

/** Décode le JSON de l'export (colonnes dans l'ordre de `colonnes`). */
export function decoderIndex(brut: BrutIndex): Index {
  const i = (nom: string) => brut.colonnes.indexOf(nom);
  const [t, c, l, n, d, x, r] = [i("type"), i("code"), i("libelle"), i("norm"), i("dep"), i("extra"), i("ref")] as [
    number, number, number, number, number, number, number,
  ];
  const entrees = brut.lignes.map(
    (v) =>
      ({ type: v[t], code: v[c], libelle: v[l], norm: v[n], dep: v[d], extra: v[x] ?? "", ref: v[r] ?? null }) as Entree,
  );
  const communes = new Map(entrees.filter((e) => e.type === "c").map((e) => [e.code, e.libelle]));
  return { entrees, departements: brut.departements, codesPostaux: brut.codes_postaux, communes };
}

/** Même règle que l'index : « St-Étienne » → « saint etienne ». */
export function normaliserRequete(texte: string): string {
  return normaliser(texte)
    .split(" ")
    .map((m) => (m === "st" ? "saint" : m === "ste" ? "sainte" : m))
    .join(" ");
}

const ORDRE_TYPE: Record<TypeEntree, number> = { c: 0, d: 1, e: 2, u: 3 };

/**
 * Au plus `max` résultats. Rang 0 : code, code postal ou libellé exact ; 1 : préfixe ; 2 : tous les
 * mots saisis contenus dans le libellé. Ordre lexical (libellé, type, code) : aucun résultat mis
 * en avant. Moins de deux caractères : aucun résultat.
 */
export function chercher(index: Index, texte: string, max = 10): Resultat[] {
  const t = normaliserRequete(texte);
  if (t.length < 2) return [];
  const mots = t.split(" ");
  const chiffres = /^\d+$/.test(t);
  const trouves: { rang: number; r: Resultat }[] = [];
  for (const e of index.entrees) {
    let rang = e.norm === t ? 0 : e.norm.startsWith(t) ? 1 : mots.every((m) => e.norm.includes(m)) ? 2 : -1;
    // Circonscription saisie par son code (« 80-01 » → « 80 01 »), en fin de libellé normalisé.
    if (e.type === "e" && mots.length > 1 && e.norm.endsWith(` ${t}`)) rang = 0;
    let codePostal: string | undefined;
    if (e.type === "c" || e.type === "d") {
      const code = e.code.toLowerCase();
      const rc = code === t ? 0 : code.startsWith(t) ? 1 : -1;
      if (rc >= 0 && (rang < 0 || rc < rang)) rang = rc;
    }
    if (chiffres && e.type === "c" && e.extra) {
      for (const cp of e.extra.split(" ")) {
        const rc = cp === t ? 0 : cp.startsWith(t) ? 1 : -1;
        if (rc >= 0 && (rang < 0 || rc < rang)) {
          rang = rc;
          codePostal = cp;
        }
      }
    }
    if (rang >= 0) trouves.push({ rang, r: { entree: e, cible: e.ref ?? e.code, codePostal } });
  }
  trouves.sort(
    (a, b) =>
      a.rang - b.rang ||
      a.r.entree.libelle.localeCompare(b.r.entree.libelle, "fr") ||
      ORDRE_TYPE[a.r.entree.type] - ORDRE_TYPE[b.r.entree.type] ||
      a.r.entree.code.localeCompare(b.r.entree.code),
  );
  return trouves.slice(0, max).map((x) => x.r);
}
