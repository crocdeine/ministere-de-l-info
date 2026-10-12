// Classeur Excel (.xlsx) minimal, écriture seule : ZIP (fflate) de quelques fichiers XML.
// Onglet « Données » : tableau dès la ligne 1, en-têtes en gras et figés, nombres numériques,
// codes en cellules texte, cellule vide pour n.d. Onglet « Notes » : clé / valeur.
// Chargé à la demande (import dynamique depuis export-csv.ts).
import { strToU8, zipSync } from "fflate";
import type { Cellule, Colonne, Export } from "./export-csv";

const esc = (t: string) =>
  // eslint-disable-next-line no-control-regex
  t.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] as string);

/** Lettre(s) de colonne : 0 -> A, 26 -> AA. */
export function lettre(i: number): string {
  let s = "";
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

// Styles (cellXfs) : 0 défaut ; 1 en-tête ; 2 entier ; 3 pourcentage ; 4 texte ; 5 note (clé) ; 6 note (valeur).
const S = { entete: 1, entier: 2, pct: 3, texte: 4, cle: 5, valeur: 6 } as const;

const chaine = (ref: string, s: number, t: string) =>
  `<c r="${ref}" s="${s}" t="inlineStr"><is><t xml:space="preserve">${esc(t)}</t></is></c>`;

function cellule(ref: string, c: Colonne, v: Cellule): string {
  if (v == null || v === "") return "";
  if (c.type === "texte") return chaine(ref, S.texte, String(v));
  if (typeof v !== "number" || !Number.isFinite(v)) return "";
  return `<c r="${ref}" s="${c.type === "pct" ? S.pct : S.entier}"><v>${c.type === "pct" ? Math.round(v * 100) / 100 : v}</v></c>`;
}

const largeurs = (cols: number[]) =>
  `<cols>${cols.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join("")}</cols>`;

const feuille = (vues: string, cols: string, lignes: string[]) =>
  `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews>${vues}</sheetViews>${cols}<sheetData>${lignes.join("")}</sheetData></worksheet>`;

function donnees(e: Export): string {
  const longueurs = e.colonnes.map((c, j) =>
    Math.max(Math.min(c.titre.length, 24), ...e.lignes.map((l) => String(l[j] ?? "").length)),
  );
  const entete = `<row r="1">${e.colonnes.map((c, j) => chaine(`${lettre(j)}1`, S.entete, c.titre)).join("")}</row>`;
  const corps = e.lignes.map(
    (l, i) => `<row r="${i + 2}">${e.colonnes.map((c, j) => cellule(`${lettre(j)}${i + 2}`, c, l[j])).join("")}</row>`,
  );
  const figes = `<sheetView workbookViewId="0" tabSelected="1"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView>`;
  return feuille(figes, largeurs(longueurs.map((n) => Math.min(Math.max(n + 3, 10), 60))), [entete, ...corps]);
}

function pageNotes(lignes: [string, string][]): string {
  const rows = lignes.map(
    ([k, v], i) => `<row r="${i + 1}">${chaine(`A${i + 1}`, S.cle, k)}${chaine(`B${i + 1}`, S.valeur, v)}</row>`,
  );
  return feuille(`<sheetView workbookViewId="0"/>`, largeurs([42, 110]), rows);
}

const styles = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="7"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;

const NS = "http://schemas.openxmlformats.org/";
const rel = (id: string, type: string, cible: string) => `<Relationship Id="${id}" Type="${NS}officeDocument/2006/relationships/${type}" Target="${cible}"/>`;
const entete = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`;

/** Classeur complet : onglets « Données » puis « Notes ». */
export function xlsx(e: Export, lignesNotes: [string, string][]): Uint8Array {
  return zipSync(
    {
      "[Content_Types].xml": strToU8(
        `${entete}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`,
      ),
      "_rels/.rels": strToU8(`${entete}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${rel("rId1", "officeDocument", "xl/workbook.xml")}</Relationships>`),
      "xl/workbook.xml": strToU8(
        `${entete}<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="${NS}officeDocument/2006/relationships"><sheets><sheet name="Données" sheetId="1" r:id="rId1"/><sheet name="Notes" sheetId="2" r:id="rId2"/></sheets></workbook>`,
      ),
      "xl/_rels/workbook.xml.rels": strToU8(
        `${entete}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${rel("rId1", "worksheet", "worksheets/sheet1.xml")}${rel("rId2", "worksheet", "worksheets/sheet2.xml")}${rel("rId3", "styles", "styles.xml")}</Relationships>`,
      ),
      "xl/styles.xml": strToU8(styles),
      "xl/worksheets/sheet1.xml": strToU8(donnees(e)),
      "xl/worksheets/sheet2.xml": strToU8(pageNotes(lignesNotes)),
    },
    { level: 6 },
  );
}
