import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { ANCRES, analyser, ancres, lienSur, morceaux } from "./markdown";

const texte = readFileSync(new URL("../../docs/methodologie.md", import.meta.url), "utf8");
const blocs = analyser(texte);
const definies = ancres(blocs);

describe("Méthodologie (docs/methodologie.md)", () => {
  it("définit chaque ancre ouverte par l'interface", () => {
    for (const a of ANCRES) expect(definies).toContain(a);
    // Ancres citées dans les composants (ancre="…") : toutes dans ANCRES, donc définies.
    const legende = readFileSync(new URL("./Legende.tsx", import.meta.url), "utf8");
    for (const [, a] of legende.matchAll(/ancre="([\w-]+)"/g)) expect(definies).toContain(a);
  });

  it("a des ancres uniques et des liens internes valides", () => {
    expect(new Set(definies).size).toBe(definies.length);
    for (const m of morceaux(texte)) if (m.t === "lien" && m.cible.startsWith("#")) expect(definies).toContain(m.cible.slice(1));
  });

  it("contient les deux insertions générées et cite une source par section", () => {
    const insertions = blocs.flatMap((b) => (b.t === "insertion" ? [b.nom] : []));
    expect(insertions).toEqual(["sources", "correspondances"]);
    // Chaque section de niveau 2 ou 3 (hors préambule) a au moins une ligne « Source(s) : ».
    let section: string | undefined;
    const avecSource = new Map<string, boolean>();
    for (const b of blocs) {
      if (b.t === "titre" && b.niveau >= 2 && b.id) avecSource.set((section = b.id), false);
      if (b.t === "source" && section) avecSource.set(section, true);
    }
    const sansSource = [...avecSource].filter(([id, ok]) => !ok && !["blocs", "calculs"].includes(id)).map(([id]) => id);
    expect(sansSource).toEqual([]);
  });

  it("n'utilise aucun mot proscrit (garde-fou 6) hors de l'énoncé de la règle", () => {
    const hors = blocs.filter((b) => !(b.t === "ol" && b.items.some((x) => x.includes("Vocabulaire neutre"))));
    const corps = JSON.stringify(hors).toLowerCase();
    for (const mot of ["bastion", "protestataire", "populiste"]) expect(corps).not.toContain(mot);
  });

  it("n'oriente pas vers les fichiers du dépôt (docs/adr/)", () => {
    expect(texte).not.toContain("docs/adr");
  });
});

describe("analyseur Markdown", () => {
  it("ne produit de lien que pour #, http: et https:", () => {
    expect(morceaux("[x](javascript:alert(1))")).toEqual([{ t: "texte", v: "x" }, { t: "texte", v: ")" }]);
    expect(morceaux("[x](data:text/html,a)")).toEqual([{ t: "texte", v: "x" }]);
    expect(lienSur("javascript:alert(1)")).toBe(false);
    expect(lienSur("pas une url")).toBe(false);
    expect(lienSur("https://www.insee.fr/")).toBe(true);
    expect(lienSur("http://exemple.fr/")).toBe(true);
    expect(lienSur("#blocs")).toBe(true);
  });

  it("reconnaît titres, listes, tableaux, sources et morceaux en ligne", () => {
    const b = analyser("## Titre {#t}\n\nUn **gras** et `code`.\n\n- a\n- b\n\n| X | Y |\n|---|---|\n| 1 | 2 |\n\nSource : ADR.\n");
    expect(b.map((x) => x.t)).toEqual(["titre", "p", "ul", "table", "source"]);
    expect(b[0]).toMatchObject({ niveau: 2, texte: "Titre", id: "t" });
    expect(b[3]).toMatchObject({ entete: ["X", "Y"], lignes: [["1", "2"]] });
    expect(morceaux("a **b** [c](#d)")).toEqual([
      { t: "texte", v: "a " },
      { t: "gras", v: "b" },
      { t: "texte", v: " " },
      { t: "lien", v: "c", cible: "#d" },
    ]);
  });
});
