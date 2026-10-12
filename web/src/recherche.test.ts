import { describe, expect, it } from "vitest";
import { type BrutIndex, chercher, decoderIndex, normaliserRequete } from "./recherche";

const COLONNES = ["type", "code", "libelle", "norm", "dep", "extra", "ref"];
const brut: BrutIndex = {
  colonnes: COLONNES,
  departements: { "42": "Loire", "80": "Somme", "75": "Paris", "21": "Côte-d'Or", "01": "Ain" },
  codes_postaux: true,
  lignes: [
    ["c", "42218", "Saint-Étienne", "saint etienne", "42", "42000 42100 42230", null],
    ["c", "01350", "Saint-Étienne-du-Bois", "saint etienne du bois", "01", "01370", null],
    ["c", "01053", "Bourg-en-Bresse", "bourg en bresse", "01", "01000", null],
    ["c", "21090", "Bourg", "bourg", "21", "21000", null],
    ["c", "80021", "Amiens", "amiens", "80", "80000 80080 80090", null],
    ["c", "75056", "Paris", "paris", "75", "75001 75002 75116", null],
    ["d", "80", "Somme", "somme", "80", "", "80021"],
    ["e", "80-01", "1ère circonscription", "1ere circonscription 80 01", "80", "", "80021"],
    ["u", "AN:PA1", "Jean Dupont", "dupont jean", "80", "Député", "80021"],
  ],
};
const index = decoderIndex(brut);
const codes = (t: string) => chercher(index, t).map((r) => r.entree.code);

describe("recherche globale", () => {
  it("tolère accents, tirets et « St »", () => {
    expect(codes("saint-etienne")[0]).toBe("42218");
    expect(codes("St Étienne")[0]).toBe("42218");
    expect(normaliserRequete("Ste-Marie")).toBe("sainte marie");
  });
  it("code INSEE, code postal, département, circonscription", () => {
    expect(codes("75056")).toEqual(["75056"]);
    expect(chercher(index, "80080")[0]).toMatchObject({ cible: "80021", codePostal: "80080" });
    expect(codes("80")[0]).toBe("80"); // département avant les communes en « 80… »
    expect(codes("80-01")).toEqual(["80-01"]);
  });
  it("élu par nom ou prénom, renvoi vers la commune la plus peuplée", () => {
    expect(chercher(index, "dupont")[0]).toMatchObject({ cible: "80021" });
    expect(codes("jean dupont")).toEqual(["AN:PA1"]);
  });
  it("homonymes : exact, préfixe, sous-chaîne ; ordre lexical", () => {
    expect(codes("bourg")).toEqual(["21090", "01053"]); // exact, puis préfixe
    expect(codes("etienne")).toEqual(["42218", "01350"]); // sous-chaînes par ordre alphabétique
  });
  it("moins de deux caractères ou rien de trouvé : aucun résultat", () => {
    expect(codes("a")).toEqual([]);
    expect(codes("zzzz")).toEqual([]);
  });
  it("rapide sur 36 000 entrées (filtrage linéaire)", () => {
    const lignes = Array.from({ length: 36000 }, (_, i) => ["c", String(i).padStart(5, "0"), `Commune ${i}`, `commune ${i}`, "01", "", null]);
    const gros = decoderIndex({ ...brut, lignes });
    const t0 = performance.now();
    chercher(gros, "commune 35");
    expect(performance.now() - t0).toBeLessThan(100);
  });
});
