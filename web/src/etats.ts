// États d'une commune sur la carte (caractère de la propriété `s` des tuiles) et sélection
// du scrutin (type, année, tour). Logique pure, testée par vitest.
import type { ExpressionSpecification } from "maplibre-gl";
import type { Manifeste, Scrutin } from "./donnees";

const TRANSPARENT = "rgba(0, 0, 0, 0)";

export type Etat = {
  car: string;
  libelle: string;
  /** Couleur de remplissage ; `null` = aucun remplissage (hors périmètre). */
  couleur: string | null;
};

/** `token` lit une variable CSS (couleurs d'interface : jamais de valeur en dur). */
export function etats(m: Manifeste, token: (nom: string) => string): Etat[] {
  return [
    ...m.blocs.map((b) => ({ car: b.car, libelle: b.libelle, couleur: b.couleur })),
    { car: m.codage.egalite, libelle: "Égalité entre blocs en tête", couleur: token("--paper") },
    {
      car: m.codage.non_classe,
      libelle: "Non classé (candidats ou listes sans bloc en tête)",
      couleur: token("--grey-300"),
    },
    { car: m.codage.absent, libelle: "n.d. (donnée non disponible)", couleur: m.couleur_nd },
    {
      car: m.codage.hors_perimetre,
      libelle: "Hors périmètre (aucun résultat pour la commune à ce tour)",
      couleur: null,
    },
  ];
}

export function libelleEtat(liste: Etat[], car: string | undefined): string {
  return liste.find((e) => e.car === car)?.libelle ?? "n.d. (donnée non disponible)";
}

const parAnnee = (a: Scrutin, b: Scrutin) => a.annee - b.annee || a.tour - b.tour;

export function annees(m: Manifeste, type: string): number[] {
  return [...new Set(m.scrutins.filter((s) => s.type === type).map((s) => s.annee))].sort(
    (a, b) => b - a,
  );
}

export function tours(m: Manifeste, type: string, annee: number): number[] {
  return m.scrutins
    .filter((s) => s.type === type && s.annee === annee)
    .map((s) => s.tour)
    .sort();
}

/**
 * Indice du scrutin (type, année, tour) dans `manifest.scrutins`. Année absente : la plus
 * récente du type ; tour absent : le premier tour disponible.
 */
export function choisir(m: Manifeste, type: string, annee?: number, tour?: number): number {
  const candidats = m.scrutins.filter((s) => s.type === type).sort(parAnnee);
  if (candidats.length === 0) return m.scrutins.length - 1;
  const a = candidats.some((s) => s.annee === annee) ? annee : candidats.at(-1)?.annee;
  const memeAnnee = candidats.filter((s) => s.annee === a);
  const s = memeAnnee.find((x) => x.tour === tour) ?? memeAnnee[0];
  return m.scrutins.findIndex((x) => x.id === s?.id);
}

/** Scrutin affiché au démarrage : présidentielle la plus récente, 1er tour. */
export function scrutinInitial(m: Manifeste): number {
  return choisir(m, m.scrutins.some((s) => s.type === "pres") ? "pres" : (m.scrutins.at(-1)?.type ?? ""), undefined, 1);
}

/** Durée du fondu (jeton --duration-map-fade, ramené à 0 par prefers-reduced-motion). */
export function dureeFondu(valeur: string): number {
  const n = Number.parseFloat(valeur);
  if (!Number.isFinite(n)) return 0;
  return valeur.endsWith("ms") ? n : n * 1000;
}

/** Couleur d'un scrutin : i-ème caractère de la propriété `s`, un seul setPaintProperty. */
export function couleurScrutin(etats: Etat[], nd: string, i: number): ExpressionSpecification {
  const paires = etats.flatMap((e) => [e.car, e.couleur ?? TRANSPARENT]);
  return ["match", ["slice", ["get", "s"], i, i + 1], ...paires, nd] as unknown as ExpressionSpecification;
}
