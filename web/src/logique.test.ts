import { gzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { decoderJsonGz, entier, ErreurDonnees, type Manifeste, pct, verifierManifeste } from "./donnees";
import {
  annees,
  choisir,
  couleurScrutin,
  dureeFondu,
  etats,
  libelleEtat,
  scrutinInitial,
  tours,
} from "./etats";

const s = (id: string, methode: "officielle" | "reconstruit" = "reconstruit") => {
  const [a, type, t] = id.split("_");
  return { id, type: type ?? "", annee: Number(a), tour: Number(t?.slice(1)), libelle: id, methode, legende: "" };
};

const M = {
  schema: 1,
  scrutins: [s("2017_pres_t1"), s("2017_pres_t2"), s("2020_muni_t1", "officielle"), s("2022_pres_t1"), s("2022_pres_t2"), s("2024_legi_t1")],
  blocs: ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"].map((code, i) => ({
    code,
    car: "abcdef"[i] ?? "",
    libelle: code,
    couleur: `#00000${i}`,
  })),
  codage: { egalite: "=", non_classe: "n", absent: ".", hors_perimetre: "x" },
  couleur_nd: "#5F6368",
} as unknown as Manifeste;

describe("contrat de données", () => {
  it("refuse une version de schéma inconnue", () => {
    expect(() => verifierManifeste({ schema: 2 })).toThrow(ErreurDonnees);
    expect(() => verifierManifeste(null)).toThrow(/Version des données/);
    expect(verifierManifeste({ schema: 1 }).schema).toBe(1);
  });

  it("décode un JSON gzip, ou déjà décompressé par le serveur", async () => {
    const json = JSON.stringify({ a: [1, null] });
    expect(await decoderJsonGz(new Uint8Array(gzipSync(json)))).toEqual({ a: [1, null] });
    expect(await decoderJsonGz(new TextEncoder().encode(json))).toEqual({ a: [1, null] });
  });

  it("formate en français, n.d. pour une absence (jamais 0)", () => {
    expect(entier(48213)).toBe("48 213");
    expect(pct(71.24)).toBe("71,2 %");
    expect(pct(null)).toBe("n.d.");
    expect(entier(undefined)).toBe("n.d.");
  });
});

describe("états de la carte", () => {
  const liste = etats(M, (t) => `var(${t})`);

  it("distingue blocs, égalité, non classé, n.d. et hors périmètre", () => {
    expect(liste.map((e) => e.car)).toEqual(["a", "b", "c", "d", "e", "f", "=", "n", ".", "x"]);
    expect(new Set(liste.map((e) => e.libelle)).size).toBe(liste.length);
    expect(liste.find((e) => e.car === "x")?.couleur).toBeNull();
    expect(liste.find((e) => e.car === ".")?.couleur).toBe("#5F6368");
    expect(libelleEtat(liste, "?")).toMatch(/^n\.d\./);
  });

  it("colore un scrutin par une seule expression sur le i-ème caractère", () => {
    const e = couleurScrutin(liste, M.couleur_nd, 3) as unknown[];
    expect(e.slice(0, 2)).toEqual(["match", ["slice", ["get", "s"], 3, 4]]);
    expect(e.at(-1)).toBe("#5F6368");
    expect(e).toContain("rgba(0, 0, 0, 0)");
  });

  it("lit la durée du fondu depuis le jeton (0 si mouvement réduit)", () => {
    expect(dureeFondu("220ms")).toBe(220);
    expect(dureeFondu("0ms")).toBe(0);
    expect(dureeFondu("0.22s")).toBe(220);
    expect(dureeFondu("")).toBe(0);
  });
});

describe("sélection du scrutin", () => {
  it("liste années et tours d'un type", () => {
    expect(annees(M, "pres")).toEqual([2022, 2017]);
    expect(tours(M, "pres", 2022)).toEqual([1, 2]);
  });

  it("garde l'année et le tour quand ils existent, sinon le plus récent et le 1er tour", () => {
    expect(M.scrutins[choisir(M, "pres", 2017, 2)]?.id).toBe("2017_pres_t2");
    expect(M.scrutins[choisir(M, "legi", 2017, 2)]?.id).toBe("2024_legi_t1");
    expect(M.scrutins[choisir(M, "muni", 2022, 1)]?.id).toBe("2020_muni_t1");
    expect(M.scrutins[scrutinInitial(M)]?.id).toBe("2022_pres_t1");
  });
});
