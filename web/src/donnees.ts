// Contrat de données (manifest.json, export Python `ministere_de_l_info.export_web`),
// lecture des JSON gzip et formats français. Aucun accès au DOM : utilisable dans un worker.

/** Version de schéma comprise par cette interface (VERSION_SCHEMA côté Python). */
export const VERSION_SCHEMA = 1;

export type Bloc = { code: string; car: string; libelle: string; couleur: string };

export type Scrutin = {
  id: string;
  type: string;
  annee: number;
  tour: number;
  libelle: string;
  methode: "officielle" | "reconstruit";
  legende: string;
};

export type Source = { mention: string; producteur: string; licence: string; url: string };

/** Type unique de manifest.json. */
export type Manifeste = {
  schema: number;
  date_export: string;
  licence_base: { nom: string; url: string; mention: string };
  sources: Record<"elections" | "ign", Source>;
  perimetre: { departements: string[] | null; communes: number; communes_sans_contour: number };
  types: Record<string, string>;
  scrutins: Scrutin[];
  scrutins_sans_resultats: { id: string; libelle: string }[];
  blocs: Bloc[];
  codage: { egalite: string; non_classe: string; absent: string; hors_perimetre: string };
  couleur_nd: string;
  colonnes_scrutin: string[];
  fichiers: Record<string, { octets: number; sha256: string; brut?: number }>;
};

/** Colonnes d'un fichier `scrutins/<id>.json.gz`, alignées sur `communes.json.gz`. */
export type ColonnesScrutin = Record<string, (number | null)[]>;

/** URL absolue d'un fichier de données (nécessaire au protocole pmtiles://). */
export function urlDonnees(fichier: string): string {
  return new URL(`${import.meta.env.BASE_URL}data/${fichier}`, location.href).href;
}

export class ErreurDonnees extends Error {}

/** Vérifie la version de schéma : une version inconnue est refusée avec un message clair. */
export function verifierManifeste(m: unknown): Manifeste {
  const schema = (m as { schema?: unknown } | null)?.schema;
  if (schema !== VERSION_SCHEMA)
    throw new ErreurDonnees(
      `Version des données non prise en charge (${String(schema)} ; attendue : ${VERSION_SCHEMA}). ` +
        "Réexporter les données ou mettre à jour l'application.",
    );
  return m as Manifeste;
}

export async function chargerManifeste(url = urlDonnees("manifest.json")): Promise<Manifeste> {
  const r = await fetch(url);
  if (!r.ok) throw new ErreurDonnees(`manifest.json introuvable (${r.status}).`);
  return verifierManifeste(await r.json());
}

/** JSON compressé (gzip), décompressé ici ; accepte aussi un JSON déjà décodé par le serveur. */
export async function lireJsonGz<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new ErreurDonnees(`${url} : ${r.status}`);
  return decoderJsonGz<T>(new Uint8Array(await r.arrayBuffer()));
}

export async function decoderJsonGz<T>(octets: Uint8Array<ArrayBuffer>): Promise<T> {
  const gzip = octets[0] === 0x1f && octets[1] === 0x8b;
  const texte = gzip
    ? await new Response(
        new Blob([octets]).stream().pipeThrough(new DecompressionStream("gzip")),
      ).text()
    : new TextDecoder().decode(octets);
  return JSON.parse(texte) as T;
}

const fmtEntier = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const fmtPct = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const fmtDate = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

export const ND = "n.d.";

export function entier(n: number | null | undefined): string {
  return n == null ? ND : fmtEntier.format(n);
}

export function pct(n: number | null | undefined): string {
  return n == null ? ND : `${fmtPct.format(n)} %`; // espace insécable avant %
}

export function date(iso: string): string {
  return fmtDate.format(new Date(iso));
}
