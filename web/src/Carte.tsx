import * as maplibregl from "maplibre-gl";
import type { ExpressionSpecification, Map as CarteML } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// Worker MapLibre empaqueté par Vite (sinon introuvable après build).
import urlWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { PMTiles, Protocol, type RangeResponse, type Source } from "pmtiles";
import { useEffect, useRef, useState } from "react";
import { type Meta, urlDonnees } from "./donnees";

/**
 * Stratégies de changement de scrutin comparées par le prototype A0 :
 * - `paint`   : un seul setPaintProperty (expression `slice` sur la propriété `s`) ;
 *               MapLibre recalcule alors les tuiles chargées dans son worker ;
 * - `couches` : une couche par scrutin, on ne change que l'opacité (pas de recalcul, fondu natif) ;
 * - `etat`    : boucle setFeatureState sur toutes les communes (méthode de la maquette HdF).
 */
export type Strategie = "paint" | "couches" | "etat";

type Props = {
  meta: Meta;
  scrutin: number;
  strategie: Strategie;
  fondu: boolean;
  onCarte?: (m: CarteML) => void;
  onSurvol?: (info: { x: number; y: number; code: string; car: string } | null) => void;
};

export const SOURCE = "communes";
const COUCHE = "communes"; // nom de la couche dans les tuiles (tippecanoe -l)
const OPACITE = 0.85;
const FONDU_MS = 220;

/**
 * Archive lue en entier puis découpée en mémoire : le protocole tauri:// ignore l'en-tête
 * Range (réponse 200 avec le fichier complet, mesuré), ce qui bloque la lecture par plages.
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

const URL_TUILES = urlDonnees("communes.pmtiles");
const protocole = new Protocol();
if (location.protocol === "tauri:") protocole.add(new PMTiles(new SourceMemoire(URL_TUILES)));
maplibregl.addProtocol("pmtiles", protocole.tile);
maplibregl.setWorkerUrl(urlWorker);

function token(nom: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
}

/** Couleurs par caractère de codage : blocs, égalité (neutre), listes non classées, n.d. */
export function couleurs(meta: Meta): { car: string; couleur: string }[] {
  return [
    ...meta.blocs.map((b) => ({ car: b.car, couleur: b.couleur })),
    { car: meta.codage.egalite, couleur: token("--paper") },
    { car: meta.codage.non_classe, couleur: token("--grey-300") },
  ];
}

function correspondance(meta: Meta, entree: ExpressionSpecification): ExpressionSpecification {
  const paires = couleurs(meta).flatMap((c) => [c.car, c.couleur]);
  return ["match", entree, ...paires, meta.couleur_nd] as unknown as ExpressionSpecification;
}

/** Couleur d'un scrutin : i-ème caractère de la propriété `s` des tuiles. */
function couleurScrutin(meta: Meta, i: number): ExpressionSpecification {
  return correspondance(meta, ["slice", ["get", "s"], i, i + 1]);
}

export function Carte({ meta, scrutin, strategie, fondu, onCarte, onSurvol }: Props) {
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<CarteML | null>(null);
  const precedent = useRef(scrutin);
  const chaines = useRef<Map<string, string> | null>(null); // stratégie `etat` seulement
  const [prete, setPrete] = useState(false);

  useEffect(() => {
    if (!conteneur.current) return;
    const transition = { duration: fondu ? FONDU_MS : 0, delay: 0 };
    const couches: maplibregl.LayerSpecification[] =
      strategie === "couches"
        ? meta.scrutins.map((_, k) => ({
            id: `communes-${k}`,
            type: "fill",
            source: SOURCE,
            "source-layer": COUCHE,
            paint: {
              "fill-color": couleurScrutin(meta, k),
              "fill-opacity": k === scrutin ? OPACITE : 0,
              "fill-opacity-transition": transition,
            },
          }))
        : [
            {
              id: "communes-0",
              type: "fill",
              source: SOURCE,
              "source-layer": COUCHE,
              paint: {
                "fill-color":
                  strategie === "paint"
                    ? couleurScrutin(meta, scrutin)
                    : correspondance(meta, ["coalesce", ["feature-state", "c"], meta.codage.absent]),
                "fill-opacity": OPACITE,
              },
            },
          ];
    const m = new maplibregl.Map({
      container: conteneur.current,
      style: {
        version: 8,
        sources: {
          fond: {
            type: "raster",
            tiles: [
              "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&FORMAT=image/png",
            ],
            tileSize: 256,
            attribution: "Fond : © IGN — Plan IGN",
          },
          [SOURCE]: {
            type: "vector",
            url: `pmtiles://${URL_TUILES}`,
            promoteId: { [COUCHE]: "code" },
            attribution: meta.sources.elections.mention,
          },
        },
        layers: [
          { id: "papier", type: "background", paint: { "background-color": token("--paper") } },
          { id: "fond", type: "raster", source: "fond", paint: { "raster-opacity": 0.35 } },
          ...couches,
          {
            id: "communes-trait",
            type: "line",
            source: SOURCE,
            "source-layer": COUCHE,
            minzoom: 8,
            paint: { "line-color": token("--map-stroke-on-fill"), "line-width": 0.4 },
          },
        ],
      },
      bounds: [
        [-5.2, 41.3],
        [9.6, 51.1],
      ],
      fitBoundsOptions: { padding: 16 },
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
      locale: {
        "NavigationControl.ZoomIn": "Zoom avant",
        "NavigationControl.ZoomOut": "Zoom arrière",
      },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("style.load", () => setPrete(true));
    const survol = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      const code = f?.properties?.code as string | undefined;
      const s = f?.properties?.s as string | undefined;
      if (!code || s === undefined) return;
      onSurvol?.({ x: e.point.x, y: e.point.y, code, car: s[precedent.current] ?? "." });
    };
    const couche = strategie === "couches" ? `communes-${scrutin}` : "communes-0";
    // ponytail: en mode `couches`, l'infobulle suit la couche initiale (prototype seulement)
    m.on("mousemove", couche, survol);
    m.on("mouseleave", couche, () => onSurvol?.(null));
    carte.current = m;
    onCarte?.(m);
    return () => {
      m.remove();
      carte.current = null;
      setPrete(false);
    };
    // Carte recréée seulement si la stratégie change (le scrutin est appliqué ci-dessous).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta, strategie, fondu]);

  // Changement de scrutin : aucune boucle sur les communes (sauf stratégie `etat`, référence).
  useEffect(() => {
    const m = carte.current;
    if (!m || !prete) return;
    const avant = precedent.current;
    precedent.current = scrutin;
    if (strategie === "paint") {
      m.setPaintProperty("communes-0", "fill-color", couleurScrutin(meta, scrutin));
    } else if (strategie === "couches") {
      if (avant !== scrutin) m.setPaintProperty(`communes-${avant}`, "fill-opacity", 0);
      m.setPaintProperty(`communes-${scrutin}`, "fill-opacity", OPACITE);
    } else {
      const appliquer = () => {
        if (!chaines.current) {
          // ponytail: communes des tuiles déjà chargées seulement (référence de mesure)
          chaines.current = new Map();
          for (const f of m.querySourceFeatures(SOURCE, { sourceLayer: COUCHE })) {
            chaines.current.set(String(f.properties.code), String(f.properties.s));
          }
        }
        for (const [code, s] of chaines.current) {
          m.setFeatureState({ source: SOURCE, sourceLayer: COUCHE, id: code }, { c: s[scrutin] });
        }
      };
      if (chaines.current || m.isSourceLoaded(SOURCE)) appliquer();
      else m.once("idle", appliquer);
    }
  }, [meta, scrutin, strategie, prete]);

  return (
    <div
      ref={conteneur}
      className="carte-conteneur"
      role="region"
      aria-label={`Carte des communes de France, ${meta.scrutins[scrutin]?.libelle ?? ""}`}
    />
  );
}
