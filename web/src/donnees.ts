// Contrat de données (manifest.json, export Python `ministere_de_l_info.export_web`),
// lecture des JSON gzip et formats français. Aucun accès au DOM : utilisable dans un worker.

/** Version de schéma comprise par cette interface (VERSION_SCHEMA côté Python). */
export const VERSION_SCHEMA = 2;

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
  codage: { egalite: string; non_classe: string; absent: string; aucun_scrutin: string };
  couleur_nd: string;
  colonnes_scrutin: string[];
  /** `sha256` : fichier tel qu'écrit ; `sha256_brut` : JSON décompressé (fichiers .json.gz). */
  fichiers: Record<string, { octets: number; sha256: string; brut?: number; sha256_brut?: string }>;
};

/** Colonnes d'un fichier `scrutins/<id>.json.gz`, alignées sur `communes.json.gz`. */
export type ColonnesScrutin = Record<string, (number | string | null)[]>;

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

/** Compare l'empreinte SHA256 d'un fichier lu à celle du manifeste (absente : erreur). */
export async function verifierEmpreinte(
  octets: ArrayBuffer | Uint8Array<ArrayBuffer>,
  attendu: string | undefined,
  nom: string,
): Promise<void> {
  const calcul = new Uint8Array(await crypto.subtle.digest("SHA-256", octets));
  const hex = Array.from(calcul, (o) => o.toString(16).padStart(2, "0")).join("");
  if (hex !== attendu)
    throw new ErreurDonnees(
      `Fichier altéré ou incomplet : ${nom} (empreinte SHA256 différente du manifeste). ` +
        "Réexporter les données.",
    );
}

/**
 * JSON compressé (gzip) : décompressé ici (ou déjà décompressé par le serveur, `Content-Encoding`),
 * puis vérifié contre l'empreinte du JSON brut (`sha256_brut` du manifeste) avant décodage.
 */
export async function lireJsonGz<T>(url: string, sha256Brut: string | undefined, nom: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new ErreurDonnees(`${nom} : ${r.status}`);
  const brut = await decompresser(new Uint8Array(await r.arrayBuffer()));
  await verifierEmpreinte(brut, sha256Brut, nom);
  return JSON.parse(new TextDecoder().decode(brut)) as T;
}

async function decompresser(octets: Uint8Array<ArrayBuffer>): Promise<Uint8Array<ArrayBuffer>> {
  if (octets[0] !== 0x1f || octets[1] !== 0x8b) return octets;
  const flux = new Blob([octets]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Uint8Array(await new Response(flux).arrayBuffer());
}

export async function decoderJsonGz<T>(octets: Uint8Array<ArrayBuffer>): Promise<T> {
  return JSON.parse(new TextDecoder().decode(await decompresser(octets))) as T;
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
