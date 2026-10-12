import { describe, expect, it } from "vitest";
import type { Manifeste, Scrutin } from "./donnees";
import { cellule, csv, csvBureaux, csvScrutin, nomFichier } from "./export-csv";
import type { Ligne } from "./fiche";

/** Relecteur RFC 4180 (séparateur « ; », BOM retiré), lignes `#` ignorées. */
function lireCsv(texte: string): string[][] {
  const lignes: string[][] = [];
  let l: string[] = [];
  let c = "";
  let q = false;
  const t = texte.replace(/^\uFEFF/, "");
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
  return lignes.filter((r) => !r[0]?.startsWith("#"));
}

const NOW = new Date(2026, 9, 12);
const m = {
  date_export: "2026-10-10T10:27:36+00:00",
  licence_base: { mention: "Base sous ODbL 1.0 ; contenus sous licence de leur producteur." },
  sources: { elections: { mention: "Ministère de l'Intérieur — Licence Ouverte 2.0" } },
  blocs: [{ code: "GAU", libelle: "Gauche" }],
  codage: { absent: "." },
} as unknown as Manifeste;
const s = { id: "2022_pres_t1", libelle: "Présidentielle 2022", methode: "officielle", legende: "Grille X" } as Scrutin;

describe("cellule", () => {
  it("échappe ; guillemets et sauts de ligne", () => {
    expect(cellule("a;b")).toBe('"a;b"');
    expect(cellule('dit "oui"')).toBe('"dit ""oui"""');
    expect(cellule("a\nb")).toBe('"a\nb"');
  });
  it("garde les zéros des codes INSEE et vide les absences", () => {
    expect(cellule("01001")).toBe("01001");
    expect(cellule(null)).toBe("");
    expect(cellule(undefined)).toBe("");
  });
  it("décimale à virgule, 0 reste 0", () => {
    expect(cellule(12.3456)).toBe("12,35");
    expect(cellule(0)).toBe("0");
    expect(cellule(Number.NaN)).toBe("");
  });
  it("neutralise une formule", () => {
    expect(cellule("=1+1")).toBe("'=1+1");
  });
});

describe("csv", () => {
  const t = csv(
    { titre: "T", sources: ["S1 ; S2"], licence: m.licence_base.mention, donnees: m.date_export },
    ["Code", "Nom"],
    [
      ["01001", "L'Abergement; Clémenciat"],
      ["02", null],
    ],
    NOW,
  );
  it("BOM, CRLF, en-tête documenté", () => {
    expect(t.startsWith("﻿# Titre : T\r\n")).toBe(true);
    expect(t).toContain("# Source : S1 , S2\r\n");
    expect(t).toContain("# Licence : Base sous ODbL 1.0 , contenus");
    expect(t).toContain("# Données du : 2026-10-10\r\n# Export du : 2026-10-12\r\n# Méthode : https://");
    expect(t.endsWith("\r\n")).toBe(true);
  });
  it("tableau relu à l'identique", () => {
    expect(lireCsv(t)).toEqual([
      ["Code", "Nom"],
      ["01001", "L'Abergement; Clémenciat"],
      ["02", ""],
    ]);
  });
});

it("nom de fichier sûr", () => {
  expect(nomFichier("bureaux de vote", "2A004_é", NOW)).toBe("ministere-info_bureaux-de-vote_2A004_e_2026-10-12.csv");
});

it("scrutin : n.d. jamais en 0, code et légende conservés", () => {
  const t = csvScrutin(
    m,
    s,
    ["01001", "2A004"],
    ["A", "B"],
    { etat: ["a", "."], part_tete: [41.234, null], participation: [60, null], inscrits: [100, null], votants: [60, null], exprimes: [58, null] },
    (car) => (car === "a" ? "Gauche" : "n.d."),
    NOW,
  );
  expect(lireCsv(t).slice(1)).toEqual([
    ["01001", "A", "Gauche", "41,23", "60", "100", "60", "58"],
    ["2A004", "B", "n.d.", "", "", "", "", ""],
  ]);
  expect(t).toContain("Classement des blocs (Présidentielle 2022) : Grille X");
});

it("bureaux : code de bureau en texte, absences vides", () => {
  const l = { scrutin: s, bv: "0012", inscrits: null, participation: null, parts: { GAU: null } } as unknown as Ligne & { bv: string };
  expect(lireCsv(csvBureaux(m, { code: "01001", nom: "A" }, [l], [{ code: "GAU" }], NOW))[1]).toEqual([
    "01001",
    "A",
    "Présidentielle 2022",
    "0012",
    "",
    "",
    "",
  ]);
});
