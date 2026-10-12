import { strFromU8, unzipSync } from "fflate";
import { describe, expect, it } from "vitest";
import type { Manifeste, Scrutin } from "./donnees";
import { cellule, csv, exportBureaux, exportHistorique, exportScrutin, fichierExport, nomFichier, notes } from "./export-csv";
import type { Ligne } from "./fiche";

/** Relecteur RFC 4180 (séparateur « ; », BOM retiré) : toutes les lignes, vides comprises. */
function lireCsv(texte: string): string[][] {
  const lignes: string[][] = [];
  let l: string[] = [];
  let c = "";
  let q = false;
  const t = texte.replace(/^﻿/, "");
  for (let i = 0; i < t.length; i++) {
    const x = t[i];
    if (q) {
      if (x === '"' && t[i + 1] === '"') (c += '"'), i++;
      else if (x === '"') q = false;
      else c += x;
    } else if (x === '"') q = true;
    else if (x === ";") (l.push(c), (c = ""));
    else if (x === "\r") continue;
    else if (x === "\n") (l.push(c), lignes.push(l), (l = []), (c = ""));
    else c += x;
  }
  return lignes;
}

const NOW = new Date(2026, 9, 12);
const m = {
  date_export: "2026-10-10T10:27:36+00:00",
  licence_base: {
    nom: "ODbL 1.0",
    url: "https://opendatacommons.org/licenses/odbl/1-0/",
    mention: "Données dérivées de la base, sous licence ODbL 1.0 ; les contenus restent soumis à la licence de leur producteur.",
  },
  sources: { elections: { mention: "Ministère de l'Intérieur (data.gouv.fr) — Licence Ouverte 2.0" } },
  blocs: [
    { code: "EXG", libelle: "Extrême gauche" },
    { code: "GAU", libelle: "Gauche" },
  ],
  codage: { absent: "." },
} as unknown as Manifeste;
const s = {
  id: "2022_pres_t1",
  libelle: "Présidentielle 2022 — 1er tour",
  methode: "reconstruit",
  legende: "Classement des blocs : reconstruction par le projet, aucune grille officielle pour ce scrutin ; grille la plus proche appliquée.",
} as Scrutin;

const ligne = (o: Partial<Ligne>): Ligne =>
  ({
    scrutin: s,
    inscrits: 1000,
    votants: 700,
    exprimes: 680,
    participation: 70,
    voix: { EXG: 100, GAU: 580, NC: 0 },
    parts: { EXG: 14.7059, GAU: 85.2941, NC: 0 },
    ...o,
  }) as Ligne;

describe("cellule", () => {
  it("échappe ; guillemets et sauts de ligne", () => {
    expect(cellule("a;b")).toBe('"a;b"');
    expect(cellule('dit "oui"')).toBe('"dit ""oui"""');
  });
  it("garde les zéros des codes INSEE, vide les absences, virgule décimale, 0 reste 0", () => {
    expect(cellule("01001")).toBe("01001");
    expect(cellule(null)).toBe("");
    expect(cellule(12.3456)).toBe("12,35");
    expect(cellule(0)).toBe("0");
  });
  it("neutralise une formule, y compris après un saut de ligne initial", () => {
    expect(cellule("=1+1")).toBe("'=1+1");
    expect(cellule("\n=1+1")).toBe("\"'\n=1+1\"");
  });
});

const historique = () =>
  exportHistorique(m, { code: "01001", nom: "L'Abergement; Clémenciat" }, [ligne({}), ligne({ inscrits: null, votants: null, exprimes: null, voix: { EXG: null, GAU: null, NC: null }, parts: { EXG: null, GAU: null, NC: null }, participation: null })], () => [], "type : Présidentielle, tour : 1er tour");

describe("CSV", () => {
  const t = csv(historique(), NOW);
  const lignes = lireCsv(t);
  it("tableau dès la ligne 1, BOM, CRLF", () => {
    expect(t.startsWith("﻿Code INSEE;Commune;Scrutin;Classement des blocs;Inscrits;Votants;Exprimés;Participation (% des inscrits);")).toBe(true);
    expect(t.endsWith("\r\n")).toBe(true);
    expect(lignes[1]?.slice(0, 4)).toEqual(["01001", "L'Abergement; Clémenciat", "Présidentielle 2022 — 1er tour", "Reconstruction documentée"]);
  });
  it("absences vides (jamais 0), colonnes sans objet retirées (NC, Remarques)", () => {
    expect(lignes[2]?.slice(4)).toEqual(Array(lignes[2]!.length - 4).fill(""));
    expect(lignes[0]).not.toContain("Voix NC");
    expect(lignes[0]).not.toContain("Part NC (% des exprimés)");
    expect(lignes[0]).not.toContain("Remarques");
    expect(lignes[0]).toContain("Voix EXG");
    expect(lignes[0]).toContain("Part GAU (% des exprimés)");
    expect(lignes[1]?.[lignes[0]!.indexOf("Part EXG (% des exprimés)")]).toBe("14,71");
  });
  it("notes à la fin après une ligne vide, préfixées « # », sans artefacts", () => {
    const i = lignes.findIndex((l) => l.length === 1 && l[0] === "");
    expect(i).toBe(3);
    const fin = lignes.slice(i + 1).filter((l) => l.length > 1);
    expect(fin.every((l) => l[0]!.startsWith("# "))).toBe(true);
    expect(fin.map((l) => l[0])).toEqual(expect.arrayContaining(["# Titre", "# Source", "# Licence de la base", "# Filtre actif", "# Méthode", "# Format du fichier", "# Colonne — Votants"]));
    expect(t).not.toMatch(/ , |Classement des blocs : Classement des blocs/);
    expect(t).toMatch(/blob\/v\d+\.\d+\.\d+\/docs\/methodologie\.md/);
    expect(fin.find((l) => l[0] === "# Classement des blocs — Présidentielle 2022 — 1er tour")?.[1]).toMatch(/^Reconstruction documentée\. Reconstruction par le projet/);
  });
});

describe("Excel", () => {
  it("onglet Données : codes en texte, nombres numériques, absences sans cellule, onglet Notes", async () => {
    const f = await fichierExport(historique(), "xlsx", NOW);
    expect(f.nom).toBe("ministere-info_historique_01001_2026-10-12.xlsx");
    const z = unzipSync(f.octets);
    const d = strFromU8(z["xl/worksheets/sheet1.xml"]!);
    expect(d).toContain('<pane ySplit="1"');
    expect(d).toContain('<c r="A1" s="1" t="inlineStr"><is><t xml:space="preserve">Code INSEE</t>');
    expect(d).toContain('<c r="A2" s="4" t="inlineStr"><is><t xml:space="preserve">01001</t>');
    expect(d).toMatch(/<c r="E2" s="2"><v>1000<\/v><\/c>/);
    expect(d).toMatch(/<c r="H2" s="3"><v>70<\/v><\/c>/);
    expect(d).not.toMatch(/<c r="E3"/); // n.d. : pas de cellule, pas de 0
    expect(d).not.toContain("Part NC");
    const n = strFromU8(z["xl/worksheets/sheet2.xml"]!);
    expect(n).toContain("Licence de la base");
    expect(n).toContain("Filtre actif");
    expect(strFromU8(z["xl/workbook.xml"]!)).toMatch(/name="Données".*name="Notes"/);
    expect(n).not.toMatch(/ , /);
  });
});

it("nom de fichier sûr", () => {
  expect(nomFichier("bureaux de vote", "2A004_é", "csv", NOW)).toBe("ministere-info_bureaux-de-vote_2A004_e_2026-10-12.csv");
});

it("NC conservé s'il y a des non classés", () => {
  const e = exportHistorique(m, { code: "01001", nom: "A" }, [ligne({ voix: { EXG: 1, GAU: 2, NC: 5 }, parts: { EXG: 1, GAU: 2, NC: 5 } })], () => []);
  expect(e.colonnes.map((c) => c.titre)).toContain("Voix NC");
  expect(notes(e, NOW).map((k) => k[0])).toContain("Bloc NC");
});

it("scrutin : n.d. jamais en 0, codes en texte, voix par bloc", () => {
  const e = exportScrutin(
    m,
    s,
    ["01001", "2A004"],
    ["A", "B"],
    { etat: ["a", "."], part_tete: [41.234, null], participation: [60, null], inscrits: [100, null], votants: [60, null], exprimes: [58, null], EXG: [20, null], GAU: [38, null], NC: [0, null] },
    (car: string) => (car === "a" ? "Gauche" : "n.d."),
  );
  const l = lireCsv(csv(e, NOW));
  expect(l[0]).toEqual(["Code INSEE", "Commune", "Bloc en tête", "Part du bloc en tête (% des exprimés)", "Inscrits", "Votants", "Exprimés", "Participation (% des inscrits)", "Voix EXG", "Voix GAU"]);
  expect(l[1]).toEqual(["01001", "A", "Gauche", "41,23", "100", "60", "58", "60", "20", "38"]);
  expect(l[2]).toEqual(["2A004", "B", "n.d.", "", "", "", "", "", "", ""]);
});

it("bureaux : code de bureau en texte, absences vides", () => {
  const b = { ...ligne({ inscrits: null }), bv: "0012" } as Ligne & { bv: string };
  const e = exportBureaux(m, { code: "01001", nom: "A" }, [b]);
  const l = lireCsv(csv(e, NOW));
  expect(l[0]?.slice(0, 5)).toEqual(["Code INSEE", "Commune", "Scrutin", "Bureau de vote", "Votants"]); // Inscrits absent partout : colonne retirée
  expect(l[1]?.slice(0, 4)).toEqual(["01001", "A", "Présidentielle 2022 — 1er tour", "0012"]);
});
