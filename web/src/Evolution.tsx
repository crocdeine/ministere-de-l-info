import * as Plot from "@observablehq/plot";
import { useEffect, useRef } from "react";
import { type Donnees, libelleTour, pct } from "./donnees";

type Props = { donnees: Donnees; tour: number };

const fmtAxe = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

/** Évolution de la part des exprimés par bloc, région entière, pour un tour. */
export function Evolution({ donnees, tour }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { blocs, annees } = donnees.meta;
    const libelles = new Map(blocs.map((b) => [b.code, b.libelle]));
    // Une ligne par (année, bloc) ; bloc sans candidat = null -> la ligne s'interrompt
    // (aucune valeur 0 inventée).
    const presents = new Map(
      donnees.evolution
        .filter((p) => p.tour === tour)
        .map((p) => [`${p.annee}_${p.bloc}`, p.pct]),
    );
    const points = annees.flatMap((annee) =>
      blocs.map((b) => ({
        annee,
        bloc: b.code,
        libelle: b.libelle,
        pct: presents.get(`${annee}_${b.code}`) ?? null,
      })),
    );
    const dessiner = () => {
      const graphique = Plot.plot({
        width: el.clientWidth,
        height: 380,
        marginLeft: 44,
        marginRight: 16,
        style: { fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--ink)" },
        x: {
          label: null,
          ticks: annees,
          tickFormat: (d: number) => String(d),
          domain: [annees[0] ?? 2002, annees[annees.length - 1] ?? 2022],
          inset: 12,
        },
        y: {
          label: "Part des exprimés (%)",
          zero: true,
          grid: true,
          tickFormat: (d: number) => fmtAxe.format(d),
        },
        color: {
          domain: blocs.map((b) => b.code),
          range: blocs.map((b) => b.couleur_trait),
        },
        marks: [
          Plot.ruleY([0], { stroke: "var(--ink)" }),
          Plot.line(points, {
            x: "annee",
            y: "pct",
            z: "bloc",
            stroke: "bloc",
            strokeWidth: 2.5,
          }),
          Plot.dot(
            points.filter((p) => p.pct != null),
            { x: "annee", y: "pct", fill: "bloc", r: 4 },
          ),
          Plot.tip(
            points.filter((p) => p.pct != null),
            Plot.pointer({
              x: "annee",
              y: "pct",
              title: (p: { annee: number; bloc: string; pct: number }) =>
                `${libelles.get(p.bloc) ?? p.bloc}\n${p.annee} : ${pct(p.pct)}`,
            }),
          ),
        ],
      });
      el.replaceChildren(graphique);
    };
    let largeur = -1;
    const ro = new ResizeObserver(() => {
      if (el.clientWidth === largeur) return;
      largeur = el.clientWidth;
      dessiner();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [donnees, tour]);

  return (
    <figure className="graphique">
      <div
        ref={ref}
        role="img"
        aria-label={`Évolution de la part des exprimés par bloc, présidentielles 2002-2022, ${libelleTour(tour)}, Hauts-de-France`}
      />
    </figure>
  );
}
