// Export CSV (lot A6) : sérialisation sans dépendance, pour un tableur français.
// UTF-8 avec BOM, séparateur « ; », décimale « , », fins de ligne CRLF, absence = cellule vide
// (jamais 0). En-tête de lignes « # … » : source, licence, dates, méthode, format.
import type { Manifeste, Scrutin } from "./donnees";
import type { Ligne } from "./fiche";

export type Cellule = string | number | null | undefined;

/** Méthode publique (le CSV quitte l'application : le panneau n'est plus accessible). */
export const URL_METHODE = "https://github.com/crocdeine/ministere-de-l-info/blob/main/docs/methodologie.md";

const BOM = "﻿";
const SEP = ";";

/** Décimale à virgule, au plus 2 décimales, sans séparateur de milliers (reste un nombre pour le tableur). */
function nombre(n: number): string {
  return Number.isFinite(n) ? String(Math.round(n * 100) / 100).replace(".", ",") : "";
}

/** Cellule : vide si absente ; guillemets si « ; », « " » ou saut de ligne ; texte neutralisé s'il pourrait être pris pour une formule. */
export function cellule(v: Cellule): string {
  if (v == null) return "";
  if (typeof v === "number") return nombre(v);
  const t = /^[=+\-@\t\r]/.test(v) ? `'${v}` : v;
  return /[;"\r\n]/.test(t) ? `"${t.replaceAll('"', '""')}"` : t;
}

const ligneCsv = (cellules: Cellule[]) => cellules.map(cellule).join(SEP);
// Ligne de commentaire : une seule cellule, donc ni « ; » ni saut de ligne dans le texte.
const commentaire = (t: string) => `# ${t.replace(/\s*[\r\n]+\s*/g, " ").replaceAll(";", ",")}`;

export type EnTete = {
  titre: string;
  /** Mentions des producteurs (une ligne chacune). */
  sources: string[];
  /** Mention de la licence de la base (ODbL) et rappel des licences des contenus. */
  licence: string;
  /** Date d'export des données (ISO). */
  donnees: string;
  /** Précisions de lecture : colonnes, classement, absences… */
  notes?: string[];
};

/** Fichier complet : BOM, lignes `#`, ligne de colonnes, lignes de données. */
export function csv(e: EnTete, colonnes: string[], lignes: Cellule[][], maintenant = new Date()): string {
  const haut = [
    `Titre : ${e.titre}`,
    ...e.sources.map((s) => `Source : ${s}`),
    `Licence : ${e.licence}`,
    `Données du : ${e.donnees.slice(0, 10)}`,
    `Export du : ${jour(maintenant)}`,
    `Méthode : ${URL_METHODE}`,
    "Format : UTF-8, séparateur « ; », décimale « , », en-tête de tableau = première ligne ne commençant pas par #. " +
      "Cellule vide = donnée absente (n.d.), jamais 0. Codes INSEE en texte : importer la colonne en texte pour conserver les zéros initiaux.",
    ...(e.notes ?? []),
  ].map(commentaire);
  return BOM + [...haut, ligneCsv(colonnes), ...lignes.map(ligneCsv)].join("\r\n") + "\r\n";
}

/** Jour local `AAAA-MM-JJ`. */
export function jour(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** `ministere-info_{vue}_{identifiant}_{date}.csv`, caractères sûrs seulement. */
export function nomFichier(vue: string, identifiant: string, maintenant = new Date()): string {
  const sur = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9._-]+/g, "-");
  return `ministere-info_${sur(vue)}_${sur(identifiant)}_${jour(maintenant)}.csv`;
}

/** En-tête commun : sources citées (clés du manifeste), licence de la base, date d'export. */
export function enTete(m: Manifeste, titre: string, cles: string[], notes: string[] = []): EnTete {
  return {
    titre,
    sources: cles.map((c) => m.sources[c]?.mention ?? c),
    licence: m.licence_base.mention,
    donnees: m.date_export,
    notes,
  };
}

/** Déclenche l'enregistrement (lien `download` sur un blob) ; l'application Mac demande un traitement propre. */
export function telecharger(nom: string, contenu: string): void {
  const url = URL.createObjectURL(new Blob([contenu], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: nom });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

const methode = (s: Scrutin) => (s.methode === "officielle" ? "Grille officielle" : "Reconstruit");

/** Légendes de classement distinctes des scrutins exportés, une note chacune (garde-fou de neutralité). */
function notesClassement(scrutins: Scrutin[]): string[] {
  const par = new Map<string, string[]>();
  for (const s of scrutins) par.set(s.legende, [...(par.get(s.legende) ?? []), s.libelle]);
  return [...par].map(([legende, libelles]) => `Classement des blocs (${libelles.join(" ; ")}) : ${legende}`);
}

const notesBlocs = (m: Manifeste) =>
  `Blocs : ${m.blocs.map((b) => `${b.code} = ${b.libelle}`).join(" ; ")} ; NC = Non classé. Parts en % des suffrages exprimés.`;

type Colonne = { code: string };

/** Historique électoral d'une commune : mêmes colonnes et libellés que le tableau affiché. */
export function csvHistorique(
  m: Manifeste,
  commune: { code: string; nom: string },
  lignes: Ligne[],
  colonnes: Colonne[],
  remarques: (l: Ligne) => (string | null)[],
  maintenant?: Date,
): string {
  return csv(
    enTete(m, `Historique électoral — ${commune.nom} (${commune.code})`, ["elections"], [
      notesBlocs(m),
      ...notesClassement(lignes.map((l) => l.scrutin)),
    ]),
    ["Code INSEE", "Commune", "Scrutin", "Méthode", "Inscrits", "Participation (%)", ...colonnes.map((c) => `Part ${c.code} (%)`), "Remarques"],
    lignes.map((l) => [
      commune.code,
      commune.nom,
      l.scrutin.libelle,
      methode(l.scrutin),
      l.inscrits,
      l.participation,
      ...colonnes.map((c) => l.parts[c.code]),
      remarques(l).filter(Boolean).join(". "),
    ]),
    maintenant,
  );
}

/** Bureaux de vote d'une commune pour un scrutin (les numéros changent d'un scrutin à l'autre). */
export function csvBureaux(
  m: Manifeste,
  commune: { code: string; nom: string },
  lignes: (Ligne & { bv: string })[],
  colonnes: Colonne[],
  maintenant?: Date,
): string {
  const s = lignes[0]?.scrutin;
  return csv(
    enTete(m, `Bureaux de vote — ${commune.nom} (${commune.code}) — ${s?.libelle ?? ""}`, ["elections"], [
      notesBlocs(m),
      "Les bureaux de vote et leurs numéros changent d'un scrutin à l'autre : pas de comparaison entre scrutins à ce niveau. Code du bureau en texte.",
      ...(s ? notesClassement([s]) : []),
    ]),
    ["Code INSEE", "Commune", "Scrutin", "Bureau", "Inscrits", "Participation (%)", ...colonnes.map((c) => `Part ${c.code} (%)`)],
    lignes.map((l) => [commune.code, commune.nom, l.scrutin.libelle, l.bv, l.inscrits, l.participation, ...colonnes.map((c) => l.parts[c.code])]),
    maintenant,
  );
}

/** Une ligne par commune pour un scrutin : bloc en tête (libellé de la légende), sa part, participation. */
export function csvScrutin(
  m: Manifeste,
  s: Scrutin,
  codes: string[],
  noms: string[],
  col: Record<string, (number | string | null)[]>,
  libelleEtat: (car: string) => string,
  maintenant?: Date,
): string {
  const num = (v: number | string | null | undefined) => (typeof v === "number" ? v : null);
  return csv(
    enTete(m, `Bloc arrivé en tête par commune — ${s.libelle}`, ["elections"], [
      "Bloc en tête : bloc qui totalise le plus de voix dans la commune (somme des voix de ses candidats ou listes), et non le bloc de la liste arrivée en tête. En cas d'égalité, aucun bloc n'est favorisé.",
      "Part du bloc en tête et participation en %. « n.d. » dans la colonne Bloc en tête : résultats absents ou sans voix exploitables.",
      ...notesClassement([s]),
    ]),
    ["Code INSEE", "Commune", "Bloc en tête", "Part du bloc en tête (%)", "Participation (%)", "Inscrits", "Votants", "Exprimés"],
    codes.map((code, i) => [
      code,
      noms[i],
      libelleEtat(String(col.etat?.[i] ?? m.codage.absent)),
      num(col.part_tete?.[i]),
      num(col.participation?.[i]),
      num(col.inscrits?.[i]),
      num(col.votants?.[i]),
      num(col.exprimes?.[i]),
    ]),
    maintenant,
  );
}
