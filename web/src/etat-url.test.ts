import { describe, expect, it } from "vitest";
import { ecrireUrl, lireUrl } from "./etat-url";

const PAGES = ["accueil", "elections"];
const IDS = ["2022_pres_t1", "2022_pres_t2"];
const lire = (h: string) => lireUrl(h, PAGES, IDS, "elections");

describe("etat-url", () => {
  it("aller-retour état -> URL -> état", () => {
    const e = { page: "elections", scrutin: "2022_pres_t2", commune: "2A004" };
    const r = lire(ecrireUrl(e));
    expect(r).toMatchObject(e);
    expect(r.avertissements).toEqual([]);
  });
  it("hachage vide ou page inconnue : page par défaut", () => {
    expect(lire("").page).toBe("elections");
    expect(lire("#/nimporte").page).toBe("elections");
  });
  it("scrutin absent du manifeste : ignoré avec message", () => {
    const r = lire("#/elections?scrutin=1999_xxx_t9");
    expect(r.scrutin).toBeUndefined();
    expect(r.avertissements).toHaveLength(1);
  });
  it("commune sans zéro de tête rejetée, code conservé en chaîne sinon", () => {
    expect(lire("#/elections?commune=1001").commune).toBeUndefined();
    expect(lire("#/elections?commune=1001").avertissements).toHaveLength(1);
    expect(lire("#/elections?commune=01001").commune).toBe("01001");
  });
  it("paramètre inconnu ignoré", () => {
    expect(lire("#/elections?x=1").avertissements).toEqual([]);
  });
});
