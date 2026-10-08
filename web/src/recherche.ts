// Recherche simple d'une commune par nom ou code INSEE (en attendant la recherche du lot A4).

/** Minuscules, sans accents ni ponctuation : « Saint-Étienne » → « saint etienne ». */
export function normaliser(texte: string): string {
  return texte
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
