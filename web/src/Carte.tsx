import type {
  ExpressionSpecification,
  LayerSpecification,
  Map as CarteML,
  MapLayerMouseEvent,
  MapSourceDataEvent,
  SourceSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import type { Manifeste } from "./donnees";
import { type Bascule, creerBascule } from "./bascule";
import { couleurScrutin, dureeFondu, type Etat } from "./etats";
import { chargerMapLibre, URL_TUILES } from "./maplibre";

/** `s` : caractères d'état de la commune, un par scrutin (propriété des tuiles). */
export type Survol = { x: number; y: number; code: string; s: string } | null;
export type Rendu = { type: "premiere" | "changement"; ms: number; fondu: boolean };

type Props = {
  manifeste: Manifeste;
  etats: Etat[];
  scrutin: number;
  onSurvol: (s: Survol) => void;
  onRendu?: (r: Rendu) => void;
};

const COUCHE_TUILES = "communes"; // tippecanoe -l
// Deux couches de remplissage, chacune sur sa propre source (mêmes tuiles) : scrutin affiché et
// scrutin suivant, fondu croisé par opacité. Sources séparées : recolorer la couche cachée ne
// recalcule que ses tuiles (une source commune recalculerait les deux couches : 98 ms au lieu
// d'environ 60, mesuré). La seconde source est ajoutée après la première carte (budget
// des données d'ouverture).
const COUCHES = ["communes-a", "communes-b"] as const;
const OPACITE = 0.85;

export function token(nom: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
}

/**
 * Appelle `fin(true)` au premier rendu où toutes les tuiles des communes sont (re)calculées, sans
 * attendre le fond Plan IGN (réseau, facultatif). Filet de sécurité : `idle` ; si la carte est
 * au repos sans que la source soit chargée (tuiles en échec), `fin(false)`.
 */
function apresRecalcul(m: CarteML, source: string, fin: (ok: boolean) => void): void {
  let fait = false;
  const terminer = (ok: boolean) => {
    if (fait) return;
    fait = true;
    m.off("sourcedata", donnees);
    m.off("idle", repos);
    fin(ok);
  };
  const repos = () => terminer(m.isSourceLoaded(source));
  const donnees = (e: MapSourceDataEvent) => {
    if (e.sourceId !== source || !e.tile || !m.isSourceLoaded(source)) return;
    m.once("render", () => terminer(true));
    m.triggerRepaint(); // garantit un rendu même si la carte n'en prévoyait plus
  };
  m.on("sourcedata", donnees);
  m.once("idle", repos);
  m.triggerRepaint(); // couleurs inchangées (retour à un tour déjà calculé) : `idle` suivra
}

function remplissage(id: string, couleur: ExpressionSpecification, opacite: number): LayerSpecification {
  return {
    id,
    type: "fill",
    source: id,
    "source-layer": COUCHE_TUILES,
    paint: {
      "fill-color": couleur,
      "fill-opacity": opacite,
      "fill-opacity-transition": { duration: 0, delay: 0 },
    },
  };
}

const ERREUR_TUILES = "Contours des communes non chargés (fichier de tuiles absent ou illisible).";

export function Carte({ manifeste, etats, scrutin, onSurvol, onRendu }: Props) {
  const conteneur = useRef<HTMLDivElement>(null);
  const bascule = useRef<Bascule | null>(null);
  const voulu = useRef(scrutin); // dernier tour demandé (couleurs initiales d'une carte recréée)
  voulu.current = scrutin;
  const rappels = useRef({ onSurvol, onRendu });
  rappels.current = { onSurvol, onRendu };
  const [prete, setPrete] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    let annule = false;
    let m: CarteML | undefined;
    setErreur(null);
    chargerMapLibre()
      .then((ml) => {
        if (annule || !conteneur.current) return;
        const initial = voulu.current;
        const couleur = couleurScrutin(etats, manifeste.couleur_nd, initial);
        const tuiles = (attribution?: string): SourceSpecification => ({
          type: "vector",
          url: `pmtiles://${URL_TUILES}`,
          promoteId: { [COUCHE_TUILES]: "code" },
          attribution,
        });
        const [a, b] = COUCHES;
        const carte = new ml.Map({
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
                attribution: `Fond : ${manifeste.sources.ign.producteur} — Plan IGN`,
              },
              [a]: tuiles(manifeste.sources.elections.mention),
            },
            layers: [
              { id: "plaque", type: "background", paint: { "background-color": token("--paper") } },
              { id: "fond", type: "raster", source: "fond", paint: { "raster-opacity": 0.35 } },
              remplissage(a, couleur, OPACITE),
              {
                id: "communes-trait",
                type: "line",
                source: a,
                "source-layer": COUCHE_TUILES,
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
        m = carte;
        carte.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        // Erreurs des tuiles des communes : message visible (le fond IGN, facultatif, est ignoré).
        carte.on("error", (e) => {
          if ((e as { sourceId?: string }).sourceId !== "fond") setErreur(ERREUR_TUILES);
        });
        // Nouvelle carte : nouvelle bascule (couche visible = 0, aucun recalcul en attente).
        bascule.current = creerBascule(
          {
            colorer: (k, i) =>
              carte.setPaintProperty(COUCHES[k] as string, "fill-color", couleurScrutin(etats, manifeste.couleur_nd, i)),
            attendre: (k, fin) => apresRecalcul(carte, COUCHES[k] as string, fin),
            afficher: (visible, duree) =>
              COUCHES.forEach((c, k) => {
                carte.setPaintProperty(c, "fill-opacity-transition", { duration: duree, delay: 0 });
                carte.setPaintProperty(c, "fill-opacity", k === visible ? OPACITE : 0);
              }),
            maintenant: () => performance.now(),
            dureeFondu: () => dureeFondu(token("--duration-map-fade")),
            rendu: (r) => rappels.current.onRendu?.({ type: "changement", ...r }),
            erreur: () => setErreur(ERREUR_TUILES),
          },
          initial,
        );
        apresRecalcul(carte, a, (ok) => {
          if (!ok) {
            setErreur(ERREUR_TUILES); // la carte n'est pas déclarée prête
            return;
          }
          rappels.current.onRendu?.({ type: "premiere", ms: performance.now(), fondu: false });
          carte.addSource(b, tuiles());
          carte.addLayer(remplissage(b, couleur, 0), "communes-trait");
          setPrete(true);
        });
        const survol = (e: MapLayerMouseEvent) => {
          const p = e.features?.[0]?.properties;
          if (typeof p?.code !== "string" || typeof p.s !== "string") return;
          rappels.current.onSurvol({ x: e.point.x, y: e.point.y, code: p.code, s: p.s });
        };
        carte.on("mousemove", [...COUCHES], survol);
        carte.on("mouseleave", [...COUCHES], () => rappels.current.onSurvol(null));
      })
      .catch((e: unknown) => setErreur(`MapLibre non chargé (${String(e)}).`));
    return () => {
      annule = true;
      m?.remove();
      bascule.current = null;
      setPrete(false);
    };
  }, [manifeste, etats]);

  // Changement de tour : voir bascule.ts (un setPaintProperty, fondu croisé, abandons).
  useEffect(() => {
    if (prete) bascule.current?.choisir(scrutin);
  }, [scrutin, prete]);

  return (
    <>
      {erreur && (
        <p className="alerte" role="alert">
          Carte non disponible : {erreur}
        </p>
      )}
      <div
        ref={conteneur}
        className="carte-conteneur"
        role="region"
        aria-label={`Carte des communes, ${manifeste.scrutins[scrutin]?.libelle ?? ""}`}
        aria-busy={!prete}
      />
    </>
  );
}
