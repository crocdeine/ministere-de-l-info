import { describe, expect, it } from "vitest";
import type { Manifeste } from "./donnees";
import {
  avecRuptures,
  blocEnTete,
  codeDepuisHash,
  departementDe,
  derniereValeur,
  filtrer,
  lignesBureaux,
  lignesCommune,
  mentionFusion,
  raisonsSerie,
} from "./fiche";

const s = (id: string, legende = "L2020", ancien = false) => {
  const [a, type, t] = id.split("_");
  return { id, type: type ?? "", annee: Number(a), tour: Number(t?.slice(1)), libelle: id, methode: "reconstruit", legende, ancien_decoupage: ancien };
};

const M = {
  schema: 3,
  scrutins: [s("2007_legi_t1", "L2020", true), s("2012_legi_t1"), s("2017_pres_t1"), s("2020_muni_t1", "officielle"), s("2022_pres_t1"), s("2024_legi_t1", "L2023")],
  blocs: ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"].map((code) => ({ code, car: "", libelle: code, couleur: "" })),
  fichiers: { "departements/80/fiches.json.gz": {}, "departements/2A/fiches.json.gz": {}, "departements/971/fiches.json.gz": {} },
} as unknown as Manifeste;

const vide = { EXG: 0, GAU: 0, DIV: 0, CENT: 0, DTE: 0, EXD: 0, NC: 0 };
type L = { scrutin: number; code_commune: string; inscrits: number | null; votants: number | null; exprimes: number | null } & Partial<Record<keyof typeof vide, number | null>> & Record<string, number | string | null>;
const colonnes = (lignes: L[]) => {
  const cles = ["scrutin", "code_commune", "inscrits", "votants", "exprimes", ...Object.keys(vide)];
  return Object.fromEntries(cles.map((c) => [c, lignes.map((l) => l[c] ?? null)]));
};

const COLS = colonnes([
  { scrutin: 4, code_commune: "80021", inscrits: 100, votants: 80, exprimes: 75, ...vide, GAU: 30, EXD: 45 },
  { scrutin: 0, code_commune: "80021", inscrits: 100, votants: 60, exprimes: 50, ...vide, NC: 50 },
  { scrutin: 1, code_commune: "80021", inscrits: 100, votants: 60, exprimes: 50, ...vide, DTE: 25, GAU: 25 },
  { scrutin: 2, code_commune: "80021", inscrits: 100, votants: 0, exprimes: 0, EXG: null, GAU: null, DIV: null, CENT: null, DTE: null, EXD: null, NC: null },
  { scrutin: 3, code_commune: "80021", inscrits: 100, votants: 50, exprimes: 40, ...vide, GAU: 40, DTE: 40 },
  { scrutin: 4, code_commune: "80022", inscrits: 5, votants: 5, exprimes: 5, ...vide, CENT: 5 },
]);

describe("fiche commune", () => {
  it("lit le code de l'URL et trouve le dossier du département", () => {
    expect(codeDepuisHash("#/commune?code=80021")).toBe("80021");
    expect(codeDepuisHash("#/commune?code=1001")).toBe("");
    expect(codeDepuisHash("#/commune")).toBeNull();
    expect(departementDe("80021", M)).toBe("80");
    expect(departementDe("2A004", M)).toBe("2A");
    expect(departementDe("97101", M)).toBe("971");
    expect(departementDe("59350", M)).toBeNull();
  });

  it("calcule les parts en % des exprimés, n.d. sans voix, sans mélanger les communes", () => {
    const l = lignesCommune(M, COLS, "80021", { fusions: { "0": ["80830"] } } as never);
    expect(l.map((x) => x.rang)).toEqual([0, 1, 2, 3, 4]);
    expect(l[4]?.parts.EXD).toBe(60);
    expect(l[4]?.participation).toBe(80);
    expect(l[2]?.parts.GAU).toBeNull(); // aucune voix : n.d., jamais 0
    expect(l[0]?.nonClasseSeul).toBe(true);
    expect(l[0]?.anciennes).toEqual(["80830"]);
    expect(l[3]?.plurinominal).toBe(true); // 80 voix pour 40 exprimés
    expect(l[3]?.parts.GAU).toBeNull();
    expect(blocEnTete(l[4] as never)).toBe("EXD");
    expect(blocEnTete(l[1] as never)).toBe("=");
    expect(blocEnTete(l[2] as never)).toBeNull();
  });

  it("signale les ruptures : grille, découpage, périmètre, nuançage, type", () => {
    const l = lignesCommune(M, COLS, "80021", { fusions: { "0": ["80830"] } } as never);
    const legi = avecRuptures(filtrer(l, "legi", 1));
    expect(legi[0]?.raisons).toEqual([]);
    expect(legi[1]?.raisons).toEqual(["decoupage", "perimetre", "nuancage"]);
    const tous = avecRuptures(filtrer(l, "", 0));
    expect(tous[2]?.raisons).toContain("type");
    expect(raisonsSerie(tous)[0]).toBe("type");
    expect(raisonsSerie(avecRuptures(filtrer(l, "pres", 1)))).toEqual([]);
  });

  it("lit les bureaux de vote d'une commune pour un scrutin", () => {
    const bv = { ...COLS, code_bv: ["0001", "0001", "0001", "0001", "0001", "0001"] };
    const r = lignesBureaux(M, bv, "80021", 4);
    expect(r).toHaveLength(1);
    expect(r[0]?.bv).toBe("0001");
    expect(r[0]?.parts.GAU).toBe(40);
  });

  it("mentionne les communes rattachées et la dernière valeur économique", () => {
    expect(mentionFusion([])).toBeNull();
    expect(mentionFusion(["80830"])).toContain("ancienne commune 80830");
    expect(mentionFusion(["1", "2"])).toContain("anciennes communes 1, 2");
    expect(derniereValeur({ annee: [2020, 2021, 2022], x: [1, 2, null] }, "x")).toEqual([2021, 2]);
    expect(derniereValeur({ annee: [2020], x: [null] }, "x")).toBeNull();
  });
});
