import * as maplibregl from "maplibre-gl";
import type { ExpressionSpecification, Map as CarteML } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// Worker MapLibre empaqueté par Vite (sinon introuvable après build).
import urlWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import {
  blocDominant,
  type Donnees,
  libelleTour,
  participation,
  pct,
  type Scrutin,
  scoreBloc,
} from "./donnees";

export type Mode = "dominant" | "score";

type Props = { donnees: Donnees; scrutin: Scrutin; mode: Mode; bloc: string };

type Infobulle = { x: number; y: number; i: number; nom: string; code: string } | null;

const SOURCE = "communes";

maplibregl.setWorkerUrl(urlWorker);

/** Valeur d'un token CSS du design system (une seule source pour les couleurs d'interface). */
export const EGALITE = "EGALITE";
export const COULEUR_EGALITE = "#ffffff";

function token(nom: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
}

function couleurRemplissage(d: Donnees, mode: Mode, bloc: string): ExpressionSpecification {
  const nd = d.meta.couleur_nd;
  if (mode === "dominant") {
    const paires = d.meta.blocs.flatMap((b) => [b.code, b.couleur]);
    // Égalité de voix en tête : couleur neutre (aucun bloc favorisé), décision Mathias 2026-10-06
    return ["match", ["coalesce", ["feature-state", "dom"], ""], ...paires, EGALITE, COULEUR_EGALITE, nd] as unknown as ExpressionSpecification;
  }
  const couleur = d.meta.blocs.find((b) => b.code === bloc)?.couleur ?? nd;
  // Échelle FIXE 0-100 % des exprimés, identique pour tous les scrutins et les deux tours.
  return [
    "case",
    ["<", ["coalesce", ["feature-state", "pct"], -1], 0],
    nd,
    [
      "interpolate",
      ["linear"],
      ["feature-state", "pct"],
      0,
      token("--paper"),
      d.meta.echelle_score_max,
      couleur,
    ],
  ];
}

export function Carte({ donnees, scrutin, mode, bloc }: Props) {
  const conteneur = useRef<HTMLDivElement>(null);
  const carte = useRef<CarteML | null>(null);
  const [prete, setPrete] = useState(false);
  const [info, setInfo] = useState<Infobulle>(null);
  const index = useRef(new Map(donnees.resultats.codes.map((c, i) => [c, i])));

  // Création unique de la carte.
  useEffect(() => {
    if (!conteneur.current) return;
    const { meta, communes } = donnees;
    const m = new maplibregl.Map({
      container: conteneur.current,
      style: {
        version: 8,
        sources: {
          fond: {
            type: "raster",
            tiles: [meta.fond_carte.url],
            tileSize: 256,
            attribution: meta.fond_carte.attribution,
          },
          [SOURCE]: { type: "geojson", data: communes, promoteId: "code" },
        },
        layers: [
          { id: "papier", type: "background", paint: { "background-color": token("--paper") } },
          {
            id: "fond",
            type: "raster",
            source: "fond",
            paint: { "raster-opacity": meta.fond_carte.opacite },
          },
          {
            id: "communes-fond",
            type: "fill",
            source: SOURCE,
            paint: { "fill-color": meta.couleur_nd, "fill-opacity": 0.85 },
          },
          {
            id: "communes-trait",
            type: "line",
            source: SOURCE,
            paint: {
              "line-color": [
                "case",
                ["boolean", ["feature-state", "survol"], false],
                token("--ink"),
                token("--map-stroke-on-fill"),
              ],
              "line-width": ["case", ["boolean", ["feature-state", "survol"], false], 2, 0.4],
            },
          },
        ],
      },
      bounds: meta.bornes ?? undefined,
      fitBoundsOptions: { padding: 16 },
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
      cooperativeGestures: true,
      locale: {
        "CooperativeGesturesHandler.WindowsHelpText": "Ctrl + molette pour zoomer",
        "CooperativeGesturesHandler.MacHelpText": "⌘ + molette pour zoomer",
        "CooperativeGesturesHandler.MobileHelpText": "Deux doigts pour déplacer la carte",
        "NavigationControl.ZoomIn": "Zoom avant",
        "NavigationControl.ZoomOut": "Zoom arrière",
      },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    // Le fond IGN est facultatif : les communes sont dans le style initial, donc affichées
    // même si les tuiles échouent (hors ligne) ; on n'attend pas l'événement « load ».
    m.on("style.load", () => setPrete(true));

    let survol: string | null = null;
    const montrer = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      const code = f?.properties?.code as string | undefined;
      if (!f || !code) return;
      if (survol !== code) {
        if (survol) m.setFeatureState({ source: SOURCE, id: survol }, { survol: false });
        survol = code;
        m.setFeatureState({ source: SOURCE, id: code }, { survol: true });
      }
      const i = index.current.get(code);
      if (i === undefined) return;
      setInfo({ x: e.point.x, y: e.point.y, i, code, nom: String(f.properties?.nom ?? code) });
    };
    m.on("mousemove", "communes-fond", montrer);
    m.on("click", "communes-fond", montrer);
    m.on("mouseleave", "communes-fond", () => {
      if (survol) m.setFeatureState({ source: SOURCE, id: survol }, { survol: false });
      survol = null;
      setInfo(null);
    });
    carte.current = m;
    return () => {
      m.remove();
      carte.current = null;
    };
  }, [donnees]);

  // Recoloration : un état par commune (pas de rechargement de la géométrie).
  useEffect(() => {
    const m = carte.current;
    if (!m || !prete) return;
    const t0 = performance.now();
    donnees.resultats.codes.forEach((code, i) => {
      const dom = blocDominant(scrutin, i, donnees.meta.blocs);
      m.setFeatureState(
        { source: SOURCE, id: code },
        {
          dom: dom ? (dom.egalite ? EGALITE : dom.code) : null,
          pct: mode === "score" ? scoreBloc(scrutin, i, bloc) : null,
        },
      );
    });
    m.setPaintProperty("communes-fond", "fill-color", couleurRemplissage(donnees, mode, bloc));
    m.once("render", () => {
      // Mesure simple de fluidité (rapport POC) : du changement de sélection à l'image suivante.
      console.info(`Carte recolorée en ${Math.round(performance.now() - t0)} ms`);
    });
  }, [donnees, scrutin, mode, bloc, prete]);

  const blocs = donnees.meta.blocs;
  const libelle = (code: string) => blocs.find((b) => b.code === code)?.libelle ?? code;
  let contenu: React.ReactNode = null;
  if (info) {
    const dom = blocDominant(scrutin, info.i, blocs);
    contenu = (
      <>
        <strong>{info.nom}</strong>
        <span className="mono">{info.code}</span>
        {mode === "dominant" ? (
          <span>
            Bloc dominant : {dom ? (dom.egalite ? "égalité entre blocs en tête" : libelle(dom.code)) : "n.d."}
            {dom ? ` — ${pct(scoreBloc(scrutin, info.i, dom.code))}` : ""}
          </span>
        ) : (
          <span>
            {libelle(bloc)} : {pct(scoreBloc(scrutin, info.i, bloc))} des exprimés
          </span>
        )}
        <span>Participation : {pct(participation(scrutin, info.i))}</span>
      </>
    );
  }

  return (
    <figure className="carte">
      <div
        ref={conteneur}
        className="carte-conteneur"
        role="region"
        aria-label={`Carte des communes des Hauts-de-France, présidentielle ${scrutin.annee}, ${libelleTour(scrutin.tour)}`}
      />
      {info && (
        <div className="infobulle" role="status" style={{ left: info.x, top: info.y }}>
          {contenu}
        </div>
      )}
    </figure>
  );
}
