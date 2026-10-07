// Types de meta.json (scripts/export_tuiles.py), chargement et formats français.

export type Bloc = { code: string; car: string; libelle: string; couleur: string };
export type ScrutinMeta = { id: string; libelle: string; legende: string };

export type Meta = {
  date_export: string;
  scrutins: ScrutinMeta[];
  blocs: Bloc[];
  codage: { egalite: string; non_classe: string; absent: string };
  couleur_nd: string;
  detail: { scrutin: string; colonnes: string[]; nul: number };
  sources: Record<"elections" | "ign", { mention: string; licence: string }>;
};

/** URL absolue d'un fichier de données (nécessaire au protocole pmtiles://). */
export function urlDonnees(fichier: string): string {
  return new URL(`${import.meta.env.BASE_URL}data/${fichier}`, location.href).href;
}

export async function chargerMeta(): Promise<Meta> {
  const r = await fetch(urlDonnees("meta.json"));
  if (!r.ok) throw new Error(`meta.json : ${r.status}`);
  return (await r.json()) as Meta;
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
  return n == null ? ND : `${fmtPct.format(n)} %`;
}
