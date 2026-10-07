import type { Map as CarteML } from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { BANC, lancerBanc, PARAMS, surveillerOuverture } from "./banc";
import { Carte, couleurs, type Strategie } from "./Carte";
import { chargerMeta, entier, type Meta, pct, urlDonnees } from "./donnees";
import type { Reponse } from "./worker/details";

type Survol = { x: number; y: number; code: string; car: string } | null;
type Detail = Extract<Reponse, { type: "commune" }> | null;

const REDUIT = matchMedia("(prefers-reduced-motion: reduce)").matches;

function libelleCar(meta: Meta, car: string): string {
  if (car === meta.codage.egalite) return "égalité entre blocs en tête";
  if (car === meta.codage.non_classe) return "listes non classées en tête";
  return meta.blocs.find((b) => b.car === car)?.libelle ?? "n.d.";
}

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [scrutin, setScrutin] = useState(0);
  const [fondu, setFondu] = useState(!REDUIT && PARAMS.get("fondu") !== "0");
  const [survol, setSurvol] = useState<Survol>(null);
  const [detail, setDetail] = useState<Detail>(null);
  const strategie = (PARAMS.get("strategie") ?? "paint") as Strategie;
  const worker = useMemo(
    () => new Worker(new URL("./worker/details.ts", import.meta.url), { type: "module" }),
    [],
  );
  const pretDetail = useRef(false);

  useEffect(() => {
    chargerMeta()
      .then((m) => {
        setMeta(m);
        setScrutin(m.scrutins.length - 1);
      })
      .catch((e: unknown) => setErreur(String(e)));
  }, []);

  // Infobulle : nom et résultats détaillés demandés au worker (chargés après la 1re carte).
  useEffect(() => {
    if (!meta || !survol) return;
    worker.onmessage = (e: MessageEvent<Reponse>) => {
      if (e.data.type === "commune") setDetail(e.data);
    };
    if (!pretDetail.current) {
      pretDetail.current = true;
      worker.postMessage({
        type: "charger",
        format: PARAMS.get("format") === "json" ? "json" : "bin",
        url: urlDonnees(`detail/${meta.detail.scrutin}.${PARAMS.get("format") === "json" ? "json" : "bin"}`),
        urlCodes: urlDonnees("detail/codes.json"),
        colonnes: meta.detail.colonnes,
        nul: meta.detail.nul,
      });
    }
    worker.postMessage({ type: "commune", code: survol.code });
  }, [meta, survol, worker]);

  const surCarte = (m: CarteML) => {
    if (!BANC || !meta) return;
    surveillerOuverture(m);
    void lancerBanc(m, setScrutin, meta, worker);
  };

  if (erreur)
    return (
      <main className="page">
        <p className="alerte">
          Données non disponibles ({erreur}). Générer les fichiers :{" "}
          <code>uv run python scripts/export_tuiles.py --db COPIE.duckdb</code>
        </p>
      </main>
    );
  if (!meta)
    return (
      <main className="page" aria-busy="true">
        <p className="overline">Chargement…</p>
      </main>
    );

  const s = meta.scrutins[scrutin];
  const n = meta.scrutins.length;
  const d = detail?.code === survol?.code ? detail : null;
  const v = s?.id === meta.detail.scrutin ? d?.valeurs : null;
  const blocTete = meta.blocs.find((b) => b.car === survol?.car);

  return (
    <main className="page">
      <header className="entete">
        <p className="eyebrow">Ministère de l'Info</p>
        <p className="overline">Prototype A0 — performance</p>
        <h1>Bloc en tête par commune</h1>
        <div className="sous-titre">
          <span>France entière, {entier(n)} scrutins, 34 877 communes</span>
        </div>
      </header>

      <section className="filtres" aria-label="Sélection du scrutin">
        <div className="champ">
          <label className="libelle" htmlFor="scrutin">
            Scrutin
          </label>
          <select id="scrutin" value={scrutin} onChange={(e) => setScrutin(Number(e.target.value))}>
            {meta.scrutins.map((x, i) => (
              <option key={x.id} value={i}>
                {x.libelle}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => setScrutin((scrutin + n - 1) % n)}>
            Précédent
          </button>
          <button type="button" onClick={() => setScrutin((scrutin + 1) % n)}>
            Suivant
          </button>
        </div>
        {strategie === "couches" && (
          <label className="champ">
            <input
              type="checkbox"
              checked={fondu}
              disabled={REDUIT}
              onChange={(e) => setFondu(e.target.checked)}
            />{" "}
            Fondu entre scrutins (220 ms)
          </label>
        )}
      </section>

      <section className="section">
        <h2>{s?.libelle}</h2>
        <figure className="carte">
          <Carte
            meta={meta}
            scrutin={scrutin}
            strategie={strategie}
            fondu={fondu}
            onCarte={surCarte}
            onSurvol={setSurvol}
          />
          {survol && (
            <div className="infobulle" role="status" style={{ left: survol.x, top: survol.y }}>
              <strong>{d?.nom ?? survol.code}</strong>
              <span className="mono">{survol.code}</span>
              <span>Bloc en tête : {libelleCar(meta, survol.car)}</span>
              {v && blocTete && (
                <span>
                  {blocTete.libelle} :{" "}
                  {pct(
                    v[blocTete.code] == null || !v.exprimes
                      ? null
                      : (100 * (v[blocTete.code] ?? 0)) / v.exprimes,
                  )}{" "}
                  des exprimés
                </span>
              )}
              {v && (
                <span>
                  Participation :{" "}
                  {pct(v.inscrits && v.votants != null ? (100 * v.votants) / v.inscrits : null)}
                </span>
              )}
            </div>
          )}
        </figure>
        <ul className="legende" aria-label="Légende : bloc arrivé en tête">
          {couleurs(meta).map((c) => (
            <li key={c.car}>
              <span className="carre" style={{ background: c.couleur }} />
              {libelleCar(meta, c.car)}
            </li>
          ))}
          <li>
            <span className="carre" style={{ background: meta.couleur_nd }} />
            n.d. (donnée non disponible)
          </li>
        </ul>
        <div className="source">
          <p className="source-titre">Source</p>
          <p>
            {meta.sources.elections.mention} ; {meta.sources.ign.mention}. {s?.legende} En cas
            d'égalité de voix entre les blocs arrivés en tête, la commune est en blanc (aucun bloc
            favorisé).
          </p>
        </div>
      </section>
    </main>
  );
}
