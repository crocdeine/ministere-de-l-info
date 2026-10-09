// Sous-ensemble de Markdown de docs/methodologie.md (titres avec ancre `{#id}`, paragraphes,
// listes, tableaux, ligne « Source(s) : », insertions `{{nom}}`). Logique pure, sans DOM.
// ponytail: pas de bibliothèque Markdown ; étendre ici si le texte utilise d'autres syntaxes.

/** Sections du panneau Méthodologie ouvertes depuis l'interface (vérifiées par les tests). */
export const ANCRES = ["methode", "blocs", "ruptures", "bloc-en-tete", "valeurs-absentes", "sources"] as const;
export type Ancre = (typeof ANCRES)[number];

export type Bloc =
  | { t: "titre"; niveau: number; texte: string; id?: string }
  | { t: "p" | "source"; texte: string }
  | { t: "ul" | "ol"; items: string[] }
  | { t: "table"; entete: string[]; lignes: string[][] }
  | { t: "insertion"; nom: string };

const cellules = (l: string) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function analyser(md: string): Bloc[] {
  const blocs: Bloc[] = [];
  const lignes = md.split("\n");
  for (let i = 0; i < lignes.length; ) {
    const l = lignes[i] as string;
    const titre = /^(#{1,3}) (.*?)(?: \{#([\w-]+)\})?$/.exec(l);
    const insertion = /^\{\{(\w+)\}\}$/.exec(l.trim());
    if (!l.trim()) i++;
    else if (titre) {
      blocs.push({ t: "titre", niveau: (titre[1] as string).length, texte: titre[2] as string, id: titre[3] });
      i++;
    } else if (insertion) {
      blocs.push({ t: "insertion", nom: insertion[1] as string });
      i++;
    } else if (l.startsWith("|")) {
      const tab: string[] = [];
      while (lignes[i]?.startsWith("|")) tab.push(lignes[i++] as string);
      blocs.push({ t: "table", entete: cellules(tab[0] as string), lignes: tab.slice(2).map(cellules) });
    } else if (/^(- |\d+\. )/.test(l)) {
      const ordonnee = !l.startsWith("- ");
      const items: string[] = [];
      while (/^(- |\d+\. )/.test(lignes[i] ?? "")) items.push((lignes[i++] as string).replace(/^(- |\d+\. )/, ""));
      blocs.push({ t: ordonnee ? "ol" : "ul", items });
    } else {
      const par: string[] = [];
      while (lignes[i]?.trim() && !/^(#|\||- |\d+\. |\{\{)/.test(lignes[i] as string)) par.push(lignes[i++] as string);
      const texte = par.join(" ");
      blocs.push({ t: /^Sources? ?:/.test(texte) ? "source" : "p", texte });
    }
  }
  return blocs;
}

/** Ancres définies par les titres. */
export function ancres(blocs: Bloc[]): string[] {
  return blocs.flatMap((b) => (b.t === "titre" && b.id ? [b.id] : []));
}

/** Morceaux d'une ligne : texte, **gras**, `code`, [lien](cible). */
export type Morceau =
  | { t: "texte"; v: string }
  | { t: "gras"; v: string }
  | { t: "code"; v: string }
  | { t: "lien"; v: string; cible: string };

/** Seules les ancres internes et les adresses http(s) deviennent des liens. */
export function lienSur(cible: string): boolean {
  if (cible.startsWith("#")) return true;
  try {
    return ["https:", "http:"].includes(new URL(cible).protocol);
  } catch {
    return false;
  }
}

export function morceaux(texte: string): Morceau[] {
  const res: Morceau[] = [];
  const motif = /\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)/g;
  let debut = 0;
  for (const m of texte.matchAll(motif)) {
    if (m.index > debut) res.push({ t: "texte", v: texte.slice(debut, m.index) });
    if (m[1] !== undefined) res.push({ t: "gras", v: m[1] });
    else if (m[2] !== undefined) res.push({ t: "code", v: m[2] });
    else if (lienSur(m[4] as string)) res.push({ t: "lien", v: m[3] as string, cible: m[4] as string });
    else res.push({ t: "texte", v: m[3] as string }); // schéma refusé (javascript:, data:…) : texte simple
    debut = m.index + m[0].length;
  }
  if (debut < texte.length) res.push({ t: "texte", v: texte.slice(debut) });
  return res;
}
