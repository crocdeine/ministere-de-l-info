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
/** Au-delà de ce délai de recoloration, le fondu est abandonné (budget ADR-0015). */
export const BUDGET_CHANGEMENT_MS = 100;

export function token(nom: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
}

/**
 * Appelle `rappel` au premier rendu où toutes les tuiles des communes sont (re)calculées, sans
 * attendre le fond Plan IGN (réseau, facultatif) ; `idle` sert de filet de sécurité.
 */
function apresRecalcul(m: CarteML, source: string, rappel: () => void): void {
  let fait = false;
  const fin = () => {
    if (fait) return;
    fait = true;
    m.off("sourcedata", donnees);
    m.off("idle", fin);
    rappel();
  };
  const donnees = (e: MapSourceDataEvent) => {
    if (e.sourceId === source && e.tile && m.isSourceLoaded(source)) m.once("render", fin);
  };
  m.on("sourcedata", donnees);
  m.once("idle", fin);
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

export function Carte({ manifeste, etats, scrutin, onSurvol, onRendu }: Props) {
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<CarteML | null>(null);
  const affiche = useRef(scrutin); // scrutin dont les couleurs sont visibles
  const visible = useRef(0); // indice de la couche visible dans COUCHES
  const generation = useRef(0);
  const rappels = useRef({ onSurvol, onRendu });
  rappels.current = { onSurvol, onRendu };
  const [prete, setPrete] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    let annule = false;
    let m: CarteML | undefined;
    chargerMapLibre()
      .then((ml) => {
        if (annule || !conteneur.current) return;
        const couleur = couleurScrutin(etats, manifeste.couleur_nd, affiche.current);
        const tuiles = (attribution?: string): SourceSpecification => ({
          type: "vector",
          url: `pmtiles://${URL_TUILES}`,
          promoteId: { [COUCHE_TUILES]: "code" },
          attribution,
        });
        const [a, b] = COUCHES;
        m = new ml.Map({
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
        m.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        const carteML = m;
        apresRecalcul(carteML, a, () => {
          rappels.current.onRendu?.({ type: "premiere", ms: performance.now(), fondu: false });
          carteML.addSource(b, tuiles());
          carteML.addLayer(remplissage(b, couleur, 0), "communes-trait");
          setPrete(true);
        });
        const survol = (e: MapLayerMouseEvent) => {
          const p = e.features?.[0]?.properties;
          if (typeof p?.code !== "string" || typeof p.s !== "string") return;
          rappels.current.onSurvol({
            x: e.point.x,
            y: e.point.y,
            code: p.code,
            s: p.s,
          });
        };
        m.on("mousemove", [...COUCHES], survol);
        m.on("mouseleave", [...COUCHES], () => rappels.current.onSurvol(null));
        carte.current = m;
      })
      .catch((e: unknown) => setErreur(String(e)));
    return () => {
      annule = true;
      m?.remove();
      carte.current = null;
      setPrete(false);
    };
  }, [manifeste, etats]);

  // Changement de scrutin : couleurs du nouveau scrutin sur la couche cachée (un seul
  // setPaintProperty, sans boucle sur les communes), puis fondu croisé des opacités. Si la
  // recoloration dépasse le budget, bascule immédiate (le fondu ajouterait du retard).
  useEffect(() => {
    const m = carte.current;
    if (!m || !prete || affiche.current === scrutin) return;
    const gen = ++generation.current;
    const t0 = performance.now();
    const avant = COUCHES[visible.current] as string;
    const apres = COUCHES[1 - visible.current] as string;
    m.setPaintProperty(apres, "fill-color", couleurScrutin(etats, manifeste.couleur_nd, scrutin));
    apresRecalcul(m, apres, () => {
      if (gen !== generation.current) return; // remplacé par un changement plus récent
      const ms = performance.now() - t0;
      const duree = ms <= BUDGET_CHANGEMENT_MS ? dureeFondu(token("--duration-map-fade")) : 0;
      for (const c of COUCHES) m.setPaintProperty(c, "fill-opacity-transition", { duration: duree, delay: 0 });
      m.setPaintProperty(apres, "fill-opacity", OPACITE);
      m.setPaintProperty(avant, "fill-opacity", 0);
      visible.current = 1 - visible.current;
      affiche.current = scrutin;
      rappels.current.onRendu?.({ type: "changement", ms, fondu: duree > 0 });
    });
    m.triggerRepaint();
  }, [manifeste, etats, scrutin, prete]);

  if (erreur)
    return <p className="alerte">Carte non disponible ({erreur}).</p>;
  return (
    <div
      ref={conteneur}
      className="carte-conteneur"
      role="region"
      aria-label={`Carte des communes, ${manifeste.scrutins[scrutin]?.libelle ?? ""}`}
      aria-busy={!prete}
    />
  );
}
