// État de la vue dans l'URL (hachage `#/elections?scrutin=2022_pres_t1&commune=01001`).
// Identifiants techniques uniquement (aucun libellé politique). Logique pure, sans DOM.

export type EtatUrl = { page: string; scrutin?: string; commune?: string; avertissements: string[] };

const RE_SCRUTIN = /^\d{4}_[a-z]+_t\d$/;
const RE_COMMUNE = /^(\d{5}|2[AB]\d{3})$/; // code INSEE en chaîne (« 01001 », jamais 1001)

/** Lit un hachage ; `pages` et `ids` (scrutins du manifeste) servent à rejeter les valeurs inconnues. */
export function lireUrl(hash: string, pages: readonly string[], ids: readonly string[], defaut: string): EtatUrl {
  const [chemin = "", requete = ""] = hash.replace(/^#\/?/, "").split("?");
  const p = new URLSearchParams(requete);
  const avertissements: string[] = [];
  const r: EtatUrl = { page: pages.includes(chemin) ? chemin : defaut, avertissements };
  const scrutin = p.get("scrutin");
  const commune = p.get("commune");
  if (scrutin !== null) {
    if (RE_SCRUTIN.test(scrutin) && ids.includes(scrutin)) r.scrutin = scrutin;
    else avertissements.push(`Scrutin « ${scrutin} » absent des données : scrutin par défaut affiché.`);
  }
  if (commune !== null) {
    if (RE_COMMUNE.test(commune)) r.commune = commune;
    else avertissements.push(`Code commune « ${commune} » invalide (cinq caractères, ex. 01001) : ignoré.`);
  }
  return r;
}

/** Écrit un hachage ; les valeurs vides sont omises. */
export function ecrireUrl(e: { page: string; scrutin?: string; commune?: string }): string {
  const p = new URLSearchParams();
  if (e.scrutin) p.set("scrutin", e.scrutin);
  if (e.commune) p.set("commune", e.commune);
  const q = p.toString();
  return `#/${e.page}${q ? `?${q}` : ""}`;
}
