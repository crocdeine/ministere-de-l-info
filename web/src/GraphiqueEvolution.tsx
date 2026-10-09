// Évolution sur plusieurs scrutins : axe horizontal temporel (années réelles), échelle fixe
// 0-100 %, une ligne par série, interrompue à chaque rupture et à chaque n.d. (jamais de
// ligne continue à travers une rupture). Graphique décoratif pour les lecteurs d'écran :
// le tableau de la fiche en est l'équivalent accessible.
import type { Ligne } from "./fiche";

export type Serie = { cle: string; libelle: string; couleur: string };

type Props = {
  lignes: Ligne[];
  series: Serie[];
  valeur: (l: Ligne, cle: string) => number | null;
  description: string;
};

const W = 720;
const H = 240;
const G = 44; // marge gauche (graduations)
const D = 64; // marge droite (étiquettes directes)
const HAUT = 12;
const BAS = 28;

export function GraphiqueEvolution({ lignes, series, valeur, description }: Props) {
  if (lignes.length === 0) return null;
  const xs = lignes.map((l) => l.scrutin.annee + (l.scrutin.tour - 1) * 0.3);
  const min = Math.min(...xs) - 0.5;
  const max = Math.max(...xs) + 0.5;
  const x = (v: number) => G + ((v - min) / (max - min)) * (W - G - D);
  const y = (p: number) => HAUT + (1 - p / 100) * (H - HAUT - BAS);
  // Années : une étiquette seulement si elle ne chevauche pas la précédente (36 unités).
  const annees: number[] = [];
  for (const a of new Set(lignes.map((l) => l.scrutin.annee)))
    if (annees.length === 0 || x(a) - x(annees.at(-1) as number) >= 36) annees.push(a);
  // Étiquettes directes : dernière valeur de chaque série, écartées d'au moins 13 unités.
  const etiquettes = series
    .map((s) => {
      const d = lignes.map((l, i) => ({ v: valeur(l, s.cle), x: xs[i] as number })).filter((p) => p.v !== null).at(-1);
      return d && d.v !== null ? { cle: s.cle, libelle: s.libelle, x: x(d.x) + 8, y: y(d.v) + 4 } : null;
    })
    .filter((e) => e !== null)
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < etiquettes.length; i++) {
    const e = etiquettes[i] as (typeof etiquettes)[number];
    e.y = Math.max(e.y, (etiquettes[i - 1]?.y ?? 0) + 13);
  }

  return (
    <svg className="graphique" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={description}>
      {[0, 25, 50, 75, 100].map((p) => (
        <g key={p}>
          <line x1={G} x2={W - D} y1={y(p)} y2={y(p)} className="graphique-grille" />
          <text x={G - 6} y={y(p) + 4} textAnchor="end" className="graphique-texte">
            {p} %
          </text>
        </g>
      ))}
      {annees.map((a) => (
        <text key={a} x={x(a)} y={H - 8} textAnchor="middle" className="graphique-texte">
          {a}
        </text>
      ))}
      {series.map((s) => {
        const points = lignes.map((l, i) => ({ v: valeur(l, s.cle), x: xs[i] as number, rupture: l.raisons.length > 0 }));
        return (
          <g key={s.cle} stroke={s.couleur} fill={s.couleur}>
            {points.map((p, i) => {
              const q = points[i - 1];
              return q && q.v !== null && p.v !== null && !p.rupture ? (
                <line key={`l${i}`} x1={x(q.x)} y1={y(q.v)} x2={x(p.x)} y2={y(p.v)} strokeWidth={2} />
              ) : null;
            })}
            {points.map((p, i) => (p.v === null ? null : <circle key={`c${i}`} cx={x(p.x)} cy={y(p.v)} r={3.5} />))}
          </g>
        );
      })}
      {etiquettes.map((e) => (
        <text key={e.cle} x={e.x} y={e.y} className="graphique-etiquette">
          {e.libelle}
        </text>
      ))}
    </svg>
  );
}
