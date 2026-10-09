import { gzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { creerBascule, type OpsBascule } from "./bascule";
import {
  decoderJsonGz,
  entier,
  ErreurDonnees,
  type Manifeste,
  pct,
  verifierEmpreinte,
  verifierManifeste,
} from "./donnees";
import { normaliser, rechercherCommunes } from "./recherche";
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
  schema: 2,
  scrutins: [s("2017_pres_t1"), s("2017_pres_t2"), s("2020_muni_t1", "officielle"), s("2022_pres_t1"), s("2022_pres_t2"), s("2024_legi_t1")],
  blocs: ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"].map((code, i) => ({
    code,
    car: "abcdef"[i] ?? "",
    libelle: code,
    couleur: `#00000${i}`,
  })),
  codage: { egalite: "=", non_classe: "n", absent: ".", aucun_scrutin: "x" },
  couleur_nd: "#5F6368",
} as unknown as Manifeste;

describe("contrat de données", () => {
  it("refuse une version de schéma inconnue", () => {
    expect(() => verifierManifeste({ schema: 1 })).toThrow(ErreurDonnees);
    expect(() => verifierManifeste(null)).toThrow(/Version des données/);
    expect(verifierManifeste({ schema: 2 }).schema).toBe(2);
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

  it("distingue blocs, égalité, non classé, n.d. et aucun scrutin", () => {
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

describe("bascule entre tours", () => {
  // Opérations simulées : les recalculs en attente sont terminés à la main.
  function simuler() {
    const attentes: ((ok: boolean) => void)[] = [];
    const journal: string[] = [];
    let horloge = 0;
    const ops: OpsBascule = {
      colorer: (k, i) => journal.push(`colorer ${k} ${i}`),
      attendre: (_k, fin) => attentes.push(fin),
      afficher: (v, d) => journal.push(`afficher ${v} ${d}`),
      maintenant: () => horloge,
      dureeFondu: () => 220,
      rendu: () => journal.push("rendu"),
      erreur: () => journal.push("erreur"),
    };
    return { attentes, journal, ops, avancer: (ms: number) => (horloge += ms) };
  }

  it("A → B → A : le recalcul de B, arrivé après le retour à A, ne change pas la carte", () => {
    const { attentes, journal, ops } = simuler();
    const b = creerBascule(ops, 0);
    b.choisir(1); // B demandé
    b.choisir(0); // retour à A avant la fin du recalcul de B
    attentes[0]?.(true);
    expect(b.affiche()).toBe(0);
    expect(journal).toEqual(["colorer 1 1"]);
  });

  it("bascule avec fondu sous le budget, sans fondu au-delà", () => {
    const { attentes, journal, ops, avancer } = simuler();
    const b = creerBascule(ops, 0);
    b.choisir(1);
    avancer(50);
    attentes[0]?.(true);
    expect(b.affiche()).toBe(1);
    avancer(1000);
    b.choisir(2);
    avancer(150);
    attentes[1]?.(true);
    expect(journal).toEqual(["colorer 1 1", "afficher 1 220", "rendu", "colorer 0 2", "afficher 0 0", "rendu"]);
  });

  it("coupe un fondu en cours avant de recolorer la couche qui disparaît", () => {
    const { attentes, journal, ops, avancer } = simuler();
    const b = creerBascule(ops, 0);
    b.choisir(1);
    attentes[0]?.(true); // fondu jusqu'à t = 220
    avancer(100);
    b.choisir(2);
    expect(journal.slice(-2)).toEqual(["afficher 1 0", "colorer 0 2"]);
  });

  it("tuiles en échec : erreur, aucune bascule", () => {
    const { attentes, journal, ops } = simuler();
    const b = creerBascule(ops, 0);
    b.choisir(1);
    attentes[0]?.(false);
    expect(b.affiche()).toBe(0);
    expect(journal).toContain("erreur");
  });
});

describe("recherche et empreintes", () => {
  it("cherche par code, début de nom puis nom contenant le texte, sans accents", () => {
    const codes = ["80021", "42218", "80001", "75056"];
    const noms = ["Amiens", "Saint-Étienne", "Abbeville", "Paris"];
    expect(rechercherCommunes(codes, noms, "etienne").map((c) => c.code)).toEqual(["42218"]);
    expect(rechercherCommunes(codes, noms, "800").map((c) => c.code)).toEqual(["80001", "80021"]);
    expect(rechercherCommunes(codes, noms, "a").length).toBe(0); // deux caractères au moins
    expect(normaliser("Saint-Étienne")).toBe("saint etienne");
  });

  it("refuse un fichier dont l'empreinte diffère du manifeste", async () => {
    const octets = new TextEncoder().encode("abc");
    const sha = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    await expect(verifierEmpreinte(octets, sha, "x")).resolves.toBeUndefined();
    await expect(verifierEmpreinte(octets, "0".repeat(64), "x")).rejects.toThrow(/altéré/);
    await expect(verifierEmpreinte(octets, undefined, "x")).rejects.toThrow(ErreurDonnees);
  });
});
