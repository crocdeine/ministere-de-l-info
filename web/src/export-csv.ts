// Exports (lot A6) : Excel (.xlsx) et CSV brut, depuis un même tableau.
// Tableau dès la ligne 1 ; les notes (source, licence, dates, méthode, définitions) sont dans
// l'onglet « Notes » d'Excel, ou à la fin du CSV après une ligne vide, préfixées « # ».
// CSV : UTF-8 avec BOM, séparateur « ; », décimale « , », CRLF, absence = cellule vide (jamais 0).
import type { Bloc, Manifeste, Scrutin } from "./donnees";
import type { Ligne } from "./fiche";

export type Cellule = string | number | null | undefined;
export type Format = "csv" | "xlsx";

declare const __VERSION_APP__: string; // vite.config.ts : version de pyproject.toml

/** Méthode publique, à la version de l'application (le fichier quitte l'application). */
export const URL_METHODE = `https://github.com/crocdeine/ministere-de-l-info/blob/v${__VERSION_APP__}/docs/methodologie.md`;

export type Colonne = {
  titre: string;
  /** `texte` : codes INSEE et de bureau (zéros initiaux) ; `entier` ; `pct` (valeur en %, 2 décimales). */
  type: "texte" | "entier" | "pct";
  definition: string;
  /** Code du bloc (`NC` compris) pour les colonnes de voix et de parts. */
  bloc?: string;
  /** Colonne retirée si toutes ses valeurs sont absentes ou nulles (ex. non classés). */
  zeroVide?: boolean;
};

export type Export = {
  /** Nom de fichier : `ministere-info_{vue}_{id}_{date}`. */
  vue: string;
  id: string;
  titre: string;
  sources: string[];
  licence: Manifeste["licence_base"];
  donnees: string;
  filtre?: string;
  scrutins: Scrutin[];
  blocs: Bloc[];
  colonnes: Colonne[];
  lignes: Cellule[][];
};

const LIBELLE_NC = "Non classé";
const classement = (s: Scrutin) => (s.methode === "officielle" ? "Grille officielle" : "Reconstruction documentée");

/** Jour local `AAAA-MM-JJ`. */
export function jour(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** `ministere-info_{vue}_{identifiant}_{date}.{ext}`, caractères sûrs seulement. */
export function nomFichier(vue: string, identifiant: string, ext: Format, maintenant = new Date()): string {
  const sur = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9._-]+/g, "-");
  return `ministere-info_${sur(vue)}_${sur(identifiant)}_${jour(maintenant)}.${ext}`;
}

const vide = (v: Cellule) => v == null || v === "";

/** Retire les colonnes entièrement vides (et, si `zeroVide`, entièrement nulles). */
function sansColonnesVides(colonnes: Colonne[], lignes: Cellule[][]): { colonnes: Colonne[]; lignes: Cellule[][] } {
  const garde = colonnes.map((c, j) => lignes.some((l) => !vide(l[j]) && !(c.zeroVide && l[j] === 0)));
  return {
    colonnes: colonnes.filter((_, j) => garde[j]),
    lignes: lignes.map((l) => l.filter((_, j) => garde[j])),
  };
}

type Entree = Omit<Export, "colonnes" | "lignes" | "licence" | "donnees" | "blocs"> & { colonnes: Colonne[]; lignes: Cellule[][] };

/** Complète avec les mentions du manifeste et retire les colonnes sans objet. */
function exportDe(m: Manifeste, e: Entree): Export {
  return { ...e, ...sansColonnesVides(e.colonnes, e.lignes), licence: m.licence_base, donnees: m.date_export, blocs: m.blocs };
}

const sources = (m: Manifeste, cles: string[]) => cles.map((c) => m.sources[c]?.mention ?? c);

/** Colonnes de voix puis de parts, pour chaque bloc et `NC` (celui-ci seulement s'il y a des non classés). */
function colonnesBlocs(m: Manifeste, parts: boolean): Colonne[] {
  const codes = [...m.blocs.map((b) => ({ code: b.code, libelle: b.libelle })), { code: "NC", libelle: LIBELLE_NC }];
  const voix = codes.map(({ code, libelle }) => ({
    titre: `Voix ${code}`,
    type: "entier" as const,
    definition: `Nombre de voix des candidats ou listes classés dans le bloc « ${libelle} »`,
    bloc: code,
    zeroVide: code === "NC",
  }));
  const pct = codes.map(({ code, libelle }) => ({
    titre: `Part ${code} (% des exprimés)`,
    type: "pct" as const,
    definition: `Voix du bloc « ${libelle} » divisées par les suffrages exprimés, en %`,
    bloc: code,
    zeroVide: code === "NC",
  }));
  return parts ? [...voix, ...pct] : voix;
}

const identite: Colonne[] = [
  { titre: "Code INSEE", type: "texte", definition: "Code de la commune (5 caractères, zéros initiaux conservés)" },
  { titre: "Commune", type: "texte", definition: "Nom de la commune" },
];
const effectifs: Colonne[] = [
  { titre: "Inscrits", type: "entier", definition: "Électeurs inscrits sur les listes électorales" },
  { titre: "Votants", type: "entier", definition: "Électeurs ayant voté (blancs et nuls compris)" },
  { titre: "Exprimés", type: "entier", definition: "Suffrages exprimés (hors blancs et nuls)" },
  { titre: "Participation (% des inscrits)", type: "pct", definition: "Votants divisés par inscrits, en %" },
];

type LigneBloc = Ligne & { bv?: string };

/** Historique électoral d'une commune : une ligne par scrutin affiché, dans l'ordre de l'écran. */
export function exportHistorique(
  m: Manifeste,
  commune: { code: string; nom: string },
  lignes: Ligne[],
  remarques: (l: Ligne) => (string | null)[],
  filtre?: string,
): Export {
  const codes = [...m.blocs.map((b) => b.code), "NC"];
  return exportDe(m, {
    vue: "historique",
    id: commune.code,
    titre: `Historique électoral — ${commune.nom} (${commune.code})`,
    sources: sources(m, ["elections"]),
    filtre,
    scrutins: lignes.map((l) => l.scrutin),
    colonnes: [
      ...identite,
      { titre: "Scrutin", type: "texte", definition: "Type de scrutin, année et tour" },
      { titre: "Classement des blocs", type: "texte", definition: "Grille officielle du ministère de l'Intérieur ou reconstruction documentée par le projet (voir les lignes de classement)" },
      ...effectifs,
      ...colonnesBlocs(m, true),
      { titre: "Remarques", type: "texte", definition: "Ruptures de comparabilité avec la ligne précédente, communes rattachées, scrutin plurinominal" },
    ],
    lignes: lignes.map((l) => [
      commune.code,
      commune.nom,
      l.scrutin.libelle,
      classement(l.scrutin),
      l.inscrits,
      l.votants,
      l.exprimes,
      l.participation,
      ...codes.map((c) => l.voix[c]),
      ...codes.map((c) => l.parts[c]),
      remarques(l).filter(Boolean).join(". "),
    ]),
  });
}

/** Bureaux de vote d'une commune pour un scrutin (les numéros changent d'un scrutin à l'autre). */
export function exportBureaux(m: Manifeste, commune: { code: string; nom: string }, lignes: (Ligne & { bv: string })[]): Export {
  const codes = [...m.blocs.map((b) => b.code), "NC"];
  const s = lignes[0]?.scrutin;
  return exportDe(m, {
    vue: "bureaux-de-vote",
    id: `${commune.code}_${s?.id ?? ""}`,
    titre: `Bureaux de vote — ${commune.nom} (${commune.code}) — ${s?.libelle ?? ""}`,
    sources: sources(m, ["elections"]),
    filtre: undefined,
    scrutins: s ? [s] : [],
    colonnes: [
      ...identite,
      { titre: "Scrutin", type: "texte", definition: "Type de scrutin, année et tour" },
      { titre: "Bureau de vote", type: "texte", definition: "Code du bureau (texte). Les bureaux et leurs numéros changent d'un scrutin à l'autre : pas de comparaison entre scrutins" },
      ...effectifs,
      ...colonnesBlocs(m, true),
    ],
    lignes: lignes.map((l: LigneBloc) => [
      commune.code,
      commune.nom,
      l.scrutin.libelle,
      l.bv,
      l.inscrits,
      l.votants,
      l.exprimes,
      l.participation,
      ...codes.map((c) => l.voix[c]),
      ...codes.map((c) => l.parts[c]),
    ]),
  });
}

/** Une ligne par commune pour un scrutin : bloc en tête (libellé de la légende), sa part, participation, voix. */
export function exportScrutin(
  m: Manifeste,
  s: Scrutin,
  codes: string[],
  noms: string[],
  col: Record<string, (number | string | null)[]>,
  libelleEtat: (car: string) => string,
): Export {
  const num = (v: number | string | null | undefined) => (typeof v === "number" ? v : null);
  const blocs = [...m.blocs.map((b) => b.code), "NC"];
  return exportDe(m, {
    vue: "scrutin",
    id: s.id,
    titre: `Bloc arrivé en tête par commune — ${s.libelle}`,
    sources: sources(m, ["elections"]),
    scrutins: [s],
    colonnes: [
      ...identite,
      { titre: "Bloc en tête", type: "texte", definition: "Bloc qui totalise le plus de voix dans la commune (somme des voix de ses candidats ou listes), et non le bloc de la liste arrivée en tête. En cas d'égalité, aucun bloc n'est favorisé. n.d. : résultats absents ou sans voix exploitables" },
      { titre: "Part du bloc en tête (% des exprimés)", type: "pct", definition: "Voix du bloc en tête divisées par les suffrages exprimés, en %" },
      ...effectifs,
      ...colonnesBlocs(m, false),
    ],
    lignes: codes.map((code, i) => [
      code,
      noms[i],
      libelleEtat(String(col.etat?.[i] ?? m.codage.absent)),
      num(col.part_tete?.[i]),
      num(col.inscrits?.[i]),
      num(col.votants?.[i]),
      num(col.exprimes?.[i]),
      num(col.participation?.[i]),
      ...blocs.map((c) => num(col[c]?.[i])),
    ]),
  });
}

/** Notes lisibles (clé, valeur) : identiques dans l'onglet « Notes » et à la fin du CSV. */
export function notes(e: Export, maintenant = new Date()): [string, string][] {
  const retire = (t: string) => t.replace(/^Classement des blocs\s*:\s*/i, "");
  const maj = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
  const affiches = new Set(e.colonnes.flatMap((c) => (c.bloc ? [c.bloc] : [])));
  const libelles: Record<string, string> = { ...Object.fromEntries(e.blocs.map((b) => [b.code, b.libelle])), NC: LIBELLE_NC };
  return [
    ["Titre", e.titre],
    ...e.sources.map((s): [string, string] => ["Source", s]),
    ["Licence de la base", `${e.licence.nom} — ${e.licence.url}`],
    ["Licence des contenus", e.licence.mention],
    ["Données du", e.donnees.slice(0, 10)],
    ["Export du", jour(maintenant)],
    ...(e.filtre ? [["Filtre actif", e.filtre] as [string, string]] : []),
    ["Valeurs absentes", "Cellule vide = donnée absente (n.d.), jamais 0."],
    ...[...affiches].map((c): [string, string] => [`Bloc ${c}`, libelles[c] ?? c]),
    ...e.scrutins.map((s): [string, string] => [`Classement des blocs — ${s.libelle}`, `${classement(s)}. ${maj(retire(s.legende))}`]),
    ["Méthode", URL_METHODE],
    ...e.colonnes.map((c): [string, string] => [`Colonne — ${c.titre}`, c.definition]),
  ];
}

/** Cellule CSV : vide si absente ; guillemets si « ; », « " » ou saut de ligne ; texte neutralisé s'il pourrait être pris pour une formule. */
export function cellule(v: Cellule): string {
  if (v == null) return "";
  if (typeof v === "number") return Number.isFinite(v) ? String(Math.round(v * 100) / 100).replace(".", ",") : "";
  const t = /^[=+\-@\t\r\n]/.test(v) ? `'${v}` : v;
  return /[;"\r\n]/.test(t) ? `"${t.replaceAll('"', '""')}"` : t;
}

const ligneCsv = (cellules: Cellule[]) => cellules.map(cellule).join(";");

/** CSV brut : BOM, tableau dès la ligne 1, ligne vide, notes préfixées « # ». */
export function csv(e: Export, maintenant = new Date()): string {
  const fin: [string, string][] = [
    ...notes(e, maintenant),
    ["Format du fichier", "UTF-8 avec BOM, séparateur point-virgule (;), décimale virgule (,). Importer les colonnes de codes en texte pour conserver les zéros initiaux."],
  ];
  const lignes = [
    ligneCsv(e.colonnes.map((c) => c.titre)),
    ...e.lignes.map(ligneCsv),
    "",
    ...fin.map(([k, v]) => ligneCsv([`# ${k}`, v])),
  ];
  return "﻿" + lignes.join("\r\n") + "\r\n";
}

export type Fichier = { nom: string; octets: Uint8Array; mime: string };

/** Fichier prêt à enregistrer ; la bibliothèque Excel n'est chargée qu'à la demande. */
export async function fichierExport(e: Export, format: Format, maintenant = new Date()): Promise<Fichier> {
  const nom = nomFichier(e.vue, e.id, format, maintenant);
  if (format === "csv") return { nom, octets: new TextEncoder().encode(csv(e, maintenant)), mime: "text/csv;charset=utf-8" };
  const { xlsx } = await import("./export-xlsx");
  return { nom, octets: xlsx(e, notes(e, maintenant)), mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" };
}

type Tauri = { invoke: (cmd: string, args: Uint8Array, options: { headers: Record<string, string> }) => Promise<unknown> };

/**
 * Enregistre le fichier. Application Mac : commande Rust `enregistrer_export` (boîte « Enregistrer sous »,
 * octets bruts ; le WebKit embarqué ignore les liens `download` sur `blob:`). Navigateur : lien `download`.
 * Retourne un message d'erreur, ou `null` (succès ou annulation par l'utilisateur).
 */
export async function telecharger(f: Fichier): Promise<string | null> {
  const tauri = (globalThis as { __TAURI_INTERNALS__?: Tauri }).__TAURI_INTERNALS__;
  if (tauri) {
    try {
      await tauri.invoke("enregistrer_export", f.octets, { headers: { nom: f.nom } });
      return null;
    } catch (e) {
      return `Enregistrement impossible : ${e instanceof Error ? e.message : String(e)}`;
    }
  }
  const url = URL.createObjectURL(new Blob([f.octets as Uint8Array<ArrayBuffer>], { type: f.mime }));
  const a = Object.assign(document.createElement("a"), { href: url, download: f.nom });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  return null;
}

/** Construit puis enregistre ; message d'erreur ou `null`. */
export async function enregistrerExport(e: Export, format: Format): Promise<string | null> {
  try {
    return await telecharger(await fichierExport(e, format));
  } catch (err) {
    return `Export impossible : ${err instanceof Error ? err.message : String(err)}`;
  }
}
