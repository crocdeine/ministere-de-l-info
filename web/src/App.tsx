import { useEffect, useState } from "react";
import { COULEUR_EGALITE, Carte, type Mode } from "./Carte";
import { chargerDonnees, type Donnees, entier, libelleTour, pct, type Source } from "./donnees";
import { Evolution } from "./Evolution";

const FLECHE = (
  <svg
    className="fleche"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="square"
    aria-hidden="true"
  >
    <path d="M6 6 L18 18 M18 8 V18 H8" />
  </svg>
);

type Option<T> = { valeur: T; libelle: string };

/** Groupe de boutons radio natifs présentés en pastilles (clavier et lecteurs d'écran natifs). */
function Pastilles<T extends string | number>(props: {
  nom: string;
  legende: string;
  options: Option<T>[];
  valeur: T;
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="champ">
      <legend>{props.legende}</legend>
      <div className="pastilles">
        {props.options.map((o) => (
          <label key={String(o.valeur)} className="pastille">
            <input
              type="radio"
              name={props.nom}
              checked={o.valeur === props.valeur}
              onChange={() => props.onChange(o.valeur)}
            />
            <span>{o.libelle}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function SourceLegende({ sources, classement }: { sources: Source[]; classement: string }) {
  return (
    <div className="source">
      <p className="source-titre">Source</p>
      <p>
        {sources.map((s) => `${s.producteur}, ${s.donnees} — ${s.licence}`).join(" ; ")}.{" "}
        {classement}
      </p>
    </div>
  );
}

export function App() {
  const [donnees, setDonnees] = useState<Donnees | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [annee, setAnnee] = useState(2022);
  const [tour, setTour] = useState(1);
  const [mode, setMode] = useState<Mode>("dominant");
  const [bloc, setBloc] = useState("CENT");

  useEffect(() => {
    const t0 = performance.now();
    chargerDonnees()
      .then((d) => {
        console.info(`Données chargées en ${Math.round(performance.now() - t0)} ms`);
        setDonnees(d);
        const derniere = d.meta.annees[d.meta.annees.length - 1];
        if (derniere) setAnnee(derniere);
      })
      .catch((e: unknown) => setErreur(String(e)));
  }, []);

  if (erreur)
    return (
      <main className="page">
        <p className="alerte">
          Données non disponibles ({erreur}). Générer les fichiers :{" "}
          <code>uv run python scripts/export_web.py</code>
        </p>
      </main>
    );
  if (!donnees)
    return (
      <main className="page" aria-busy="true">
        <p className="overline">Chargement des données…</p>
      </main>
    );

  const { meta } = donnees;
  const scrutin = donnees.resultats.scrutins[`${annee}_${tour}`];
  const libelleBloc = (code: string | null) =>
    meta.blocs.find((b) => b.code === code)?.libelle ?? "n.d.";
  const classement = meta.legendes_classement[String(annee)] ?? "";
  const blocSel = meta.blocs.find((b) => b.code === bloc);

  return (
    <main className="page">
      <header className="entete">
        <p className="eyebrow">Ministère de l'Info</p>
        <p className="overline">01 — Élections</p>
        <h1>Présidentielles</h1>
        <div className="sous-titre">
          <span>Hauts-de-France, 2002-2022, résultats par commune</span>
          {FLECHE}
        </div>
      </header>

      <section className="filtres" aria-label="Sélection du scrutin">
        <Pastilles
          nom="annee"
          legende="Année"
          options={meta.annees.map((a) => ({ valeur: a, libelle: String(a) }))}
          valeur={annee}
          onChange={setAnnee}
        />
        <Pastilles
          nom="tour"
          legende="Tour"
          options={meta.tours.map((t) => ({ valeur: t, libelle: libelleTour(t) }))}
          valeur={tour}
          onChange={setTour}
        />
        <Pastilles
          nom="mode"
          legende="Mode de carte"
          options={[
            { valeur: "dominant" as Mode, libelle: "Bloc dominant" },
            { valeur: "score" as Mode, libelle: "Score d'un bloc" },
          ]}
          valeur={mode}
          onChange={setMode}
        />
        {mode === "score" && (
          <label className="champ">
            <span className="libelle">Bloc</span>
            <select value={bloc} onChange={(e) => setBloc(e.target.value)}>
              {meta.blocs.map((b) => (
                <option key={b.code} value={b.code}>
                  {b.code} — {b.libelle}
                </option>
              ))}
            </select>
          </label>
        )}
      </section>

      {!scrutin ? (
        <p className="alerte">
          Données non disponibles pour {annee}, {libelleTour(tour)}.
        </p>
      ) : (
        <>
          <section className="chiffres" aria-label="Chiffres-clés">
            <div className="chiffre">
              <p className="libelle">Communes</p>
              <p className="valeur">{entier(scrutin.chiffres.communes)}</p>
            </div>
            <div className="chiffre">
              <p className="libelle">Inscrits</p>
              <p className="valeur">{entier(scrutin.chiffres.inscrits)}</p>
            </div>
            <div className="chiffre">
              <p className="libelle">Participation</p>
              <p className="valeur">{pct(scrutin.chiffres.participation)}</p>
              <p className="note">Total des votants divisé par le total des inscrits.</p>
            </div>
            <div className="chiffre">
              <p className="libelle">Bloc majoritaire</p>
              <p className="valeur">{libelleBloc(scrutin.chiffres.bloc_majoritaire)}</p>
              <p className="note">Bloc ayant réuni le plus de voix dans la région.</p>
            </div>
          </section>
          <SourceLegende sources={[meta.sources.elections]} classement={classement} />

          <section className="section">
            <p className="overline">02 —</p>
            <h2>
              Carte — {annee}, {libelleTour(tour)}
            </h2>
            <Carte donnees={donnees} scrutin={scrutin} mode={mode} bloc={bloc} />
            {mode === "dominant" ? (
              <ul className="legende" aria-label="Légende : bloc arrivé en tête">
                {meta.blocs.map((b) => (
                  <li key={b.code}>
                    <span className="carre" style={{ background: b.couleur }} />
                    {b.libelle}
                  </li>
                ))}
                <li>
                  <span className="carre" style={{ background: COULEUR_EGALITE }} />
                  Égalité entre blocs en tête
                </li>
                <li>
                  <span className="carre" style={{ background: meta.couleur_nd }} />
                  n.d. (donnée non disponible)
                </li>
              </ul>
            ) : (
              <div className="legende-score">
                <p className="libelle">
                  {blocSel?.libelle} — part des exprimés, échelle fixe 0-
                  {meta.echelle_score_max} % (identique pour tous les scrutins et les deux tours)
                </p>
                <div
                  className="degrade"
                  style={{
                    background: `linear-gradient(to right, var(--paper), ${blocSel?.couleur ?? meta.couleur_nd})`,
                  }}
                />
                <div className="graduations mono">
                  <span>0 %</span>
                  <span>50 %</span>
                  <span>100 %</span>
                </div>
                <p className="legende-nd">
                  <span className="carre" style={{ background: meta.couleur_nd }} />
                  n.d. (donnée non disponible)
                </p>
              </div>
            )}
            <SourceLegende
              sources={[meta.sources.elections, meta.sources.ign]}
              classement={`${classement} ${meta.fond_carte.attribution}. En cas d'égalité de voix entre les blocs arrivés en tête, la commune est en blanc (aucun bloc favorisé).`}
            />
          </section>
        </>
      )}

      <section className="section">
        <p className="overline">03 —</p>
        <h2>Évolution des blocs, 2002-2022</h2>
        <p className="chapo">
          Part des exprimés de chaque bloc dans l'ensemble des Hauts-de-France, {libelleTour(tour)}.
          Ligne interrompue : aucun candidat du bloc à ce tour.
        </p>
        <ul className="legende" aria-label="Légende des blocs">
          {meta.blocs.map((b) => (
            <li key={b.code}>
              <span className="trait" style={{ background: b.couleur_trait }} />
              {b.libelle}
            </li>
          ))}
        </ul>
        <Evolution donnees={donnees} tour={tour} />
        <SourceLegende
          sources={[meta.sources.elections]}
          classement={[
            ...new Set(meta.annees.map((a) => meta.legendes_classement[String(a)] ?? "")),
          ].join(" ")}
        />
      </section>

      <footer className="pied mono">
        Données exportées le {new Date(meta.date_export).toLocaleDateString("fr-FR")}. Maquette —
        usage interne.
      </footer>
    </main>
  );
}
