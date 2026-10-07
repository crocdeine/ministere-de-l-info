// Chargement de MapLibre depuis ses fichiers ESM d'origine (copiés dans public/vendor/ par
// vite.config.ts) : le module principal et le worker importent le même `maplibre-gl-shared.mjs`,
// chargé une seule fois. Empaqueté par Vite, ce code commun serait dupliqué dans le worker
// (+145 Ko gzip, mesuré : 499 Ko de JS initial au prototype A0 contre une cible de 450 Ko).
import type * as ML from "maplibre-gl";
import { PMTiles, Protocol, type RangeResponse, type Source } from "pmtiles";
import { urlDonnees } from "./donnees";

export type MapLibre = typeof ML;

export const URL_TUILES = urlDonnees("communes.pmtiles");
const vendor = (f: string) => new URL(`${import.meta.env.BASE_URL}vendor/${f}`, location.href).href;

/**
 * Archive lue en entier puis découpée en mémoire : le protocole tauri:// ignore l'en-tête
 * Range (réponse 200 avec le fichier complet, mesuré au prototype A0 ; ≈ 20 Mo en mémoire).
 */
class SourceMemoire implements Source {
  private octets: Promise<ArrayBuffer> | null = null;
  constructor(private readonly url: string) {}
  getKey(): string {
    return this.url;
  }
  async getBytes(offset: number, length: number): Promise<RangeResponse> {
    this.octets ??= fetch(this.url).then((r) => r.arrayBuffer());
    return { data: (await this.octets).slice(offset, offset + length) };
  }
}

let promesse: Promise<MapLibre> | null = null;

/** MapLibre prêt (protocole pmtiles:// et worker enregistrés) ; lancé au plus tôt par main.tsx. */
export function chargerMapLibre(): Promise<MapLibre> {
  promesse ??= (import(/* @vite-ignore */ vendor("maplibre-gl.mjs")) as Promise<MapLibre>).then(
    (ml) => {
      const protocole = new Protocol();
      if (location.protocol === "tauri:") protocole.add(new PMTiles(new SourceMemoire(URL_TUILES)));
      ml.addProtocol("pmtiles", protocole.tile);
      ml.setWorkerUrl(vendor("maplibre-gl-worker.mjs"));
      return ml;
    },
  );
  return promesse;
}
