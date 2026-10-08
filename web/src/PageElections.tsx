import { useEffect, useMemo, useState } from "react";
import { Carte, type Rendu, type Survol, token } from "./Carte";
import { date, entier, type Manifeste, pct, urlDonnees } from "./donnees";
import { annees, choisir, type Etat, etats as listeEtats, libelleEtat, scrutinInitial, tours } from "./etats";
import { EtiquetteMethode, Legende } from "./Legende";
import { journal, noter } from "./mesure";
import type { Demande, Fichier, Reponse, Valeurs } from "./worker/details";

type ReponseCommune = Extract<Reponse, { type: "commune" }>;
type ReponseRecherche = Extract<Reponse, { type: "resultats" }>;

function fichier(m: Manifeste, rel: string): Fichier {
  return { url: urlDonnees(rel), sha256: m.fichiers[rel]?.sha256_brut, nom: rel };
}

/** Lignes communes à l'infobulle et à la commune choisie au clavier. */
function Resultats({ m, etats, car, v, erreur }: { m: Manifeste; etats: Etat[]; car: string; v: Valeurs | null | undefined; erreur?: string }) {
  const blocEnTete = m.blocs.some((b) => b.car === car);
  const num = (x: number | string | null | undefined) => (typeof x === "number" ? x : null);
  return (
    <>
      <span>
        {libelleEtat(etats, car)}
        {car === m.codage.absent && v?.total === 0 && " — 0 voix dans la source"}
      </span>
      {erreur && <span className="erreur-detail">Détail non disponible : {erreur}</span>}
      {v && blocEnTete && <span>Part du bloc en tête : {pct(num(v.part_tete))} des exprimés</span>}
      {v && car !== m.codage.aucun_scrutin && <span>Participation : {pct(num(v.participation))}</span>}
      {v && car !== m.codage.aucun_scrutin && <span>Inscrits : {entier(num(v.inscrits))}</span>}
    </>
  );
}

export function PageElections({ manifeste, numero }: { manifeste: Manifeste; numero: string }) {
  const etats = useMemo(() => listeEtats(manifeste, token), [manifeste]);
  const [scrutin, setScrutin] = useState(() => scrutinInitial(manifeste));
  const [rupture, setRupture] = useState(false);
  const [survol, setSurvol] = useState<Survol>(null);
  const [details, setDetails] = useState<Record<string, ReponseCommune>>({});
  const [carteAffichee, setCarteAffichee] = useState(false);
  const [worker, setWorker] = useState<Worker | null>(null);
  const [texte, setTexte] = useState("");
  const [trouvees, setTrouvees] = useState<ReponseRecherche | null>(null);
  const [choisie, setChoisie] = useState<{ code: string; nom: string } | null>(null);
  const s = manifeste.scrutins[scrutin];

  const changer = (i: number) => {
    const avant = manifeste.scrutins[scrutin];
    const apres = manifeste.scrutins[i];
    if (!apres || i === scrutin) return;
    setRupture(avant?.type !== apres.type || avant.methode !== apres.methode);
    setScrutin(i);
  };
  journal.choisir = changer;
  journal.scrutins = manifeste.scrutins.length;

  // Worker créé et arrêté par un effet : en mode strict (montage double), le premier est arrêté.
  useEffect(() => {
    const w = new Worker(new URL("./worker/details.ts", import.meta.url), { type: "module" });
    w.onmessage = (e: MessageEvent<Reponse>) => {
      const r = e.data;
      if (r.type === "resultats") setTrouvees(r);
      else
        setDetails((d) => {
          const n = { ...d, [`${r.code}|${r.scrutin}`]: r };
          const cles = Object.keys(n);
          if (cles.length > 50) delete n[cles[0] as string]; // survols récents seulement
          return n;
        });
    };
    setWorker(w);
    return () => w.terminate();
  }, []);

  const idScrutin = s?.id;
  const communes = useMemo(() => fichier(manifeste, "communes.json.gz"), [manifeste]);
  const tour = useMemo(
    () => (idScrutin ? fichier(manifeste, `scrutins/${idScrutin}.json.gz`) : null),
    [manifeste, idScrutin],
  );

  // Résultats détaillés : préchargés après la première carte (budget des données d'ouverture).
  useEffect(() => {
    if (!worker || !carteAffichee || !tour || !idScrutin) return;
    worker.postMessage({ type: "precharger", communes, scrutin: idScrutin, fichier: tour } satisfies Demande);
  }, [worker, carteAffichee, communes, tour, idScrutin]);

  const codeSurvol = survol?.code;
  const codeChoisi = choisie?.code;
  useEffect(() => {
    if (!worker || !tour || !idScrutin) return;
    for (const code of new Set([codeSurvol, codeChoisi])) {
      if (code) worker.postMessage({ type: "commune", communes, scrutin: idScrutin, fichier: tour, code } satisfies Demande);
    }
  }, [worker, communes, tour, idScrutin, codeSurvol, codeChoisi]);

  useEffect(() => {
    if (!worker) return;
    const t = setTimeout(() => worker.postMessage({ type: "rechercher", communes, texte } satisfies Demande), 150);
    return () => clearTimeout(t);
  }, [worker, communes, texte]);

  const rendu = (r: Rendu) => {
    if (r.type === "premiere") setCarteAffichee(true);
    noter(r);
  };

  if (!s) return <p className="alerte">Aucun scrutin dans les données exportées.</p>;
  const d = codeSurvol ? details[`${codeSurvol}|${s.id}`] : undefined;
  // État lu pour le tour choisi (et non au moment du survol) : juste après un changement.
  const car = survol?.s[scrutin] ?? manifeste.codage.absent;
  const c = codeChoisi ? details[`${codeChoisi}|${s.id}`] : undefined;
  const carChoisie = typeof c?.valeurs?.etat === "string" ? c.valeurs.etat : manifeste.codage.absent;
  const sans = manifeste.scrutins_sans_resultats;

  return (
    <>
      <section className="entete">
        <p className="overline">{numero} —</p>
        <h1>Élections</h1>
        <p className="sous-titre">
          Bloc arrivé en tête par commune · {manifeste.perimetre.departements ? "échantillon" : "France entière"}{" "}
          · {entier(manifeste.scrutins.length)} tours de scrutin · {entier(manifeste.perimetre.communes)} communes
        </p>
      </section>

      <section className="filtres" aria-label="Choix du scrutin">
        <div className="champ">
          <label className="libelle" htmlFor="type">
            Type de scrutin
          </label>
          <select id="type" value={s.type} onChange={(e) => changer(choisir(manifeste, e.target.value, s.annee, s.tour))}>
            {Object.entries(manifeste.types).map(([code, libelle]) => (
              <option key={code} value={code}>
                {libelle}
              </option>
            ))}
          </select>
        </div>
        <div className="champ">
          <label className="libelle" htmlFor="annee">
            Année
          </label>
          <select
            id="annee"
            value={s.annee}
            onChange={(e) => changer(choisir(manifeste, s.type, Number(e.target.value), s.tour))}
          >
            {annees(manifeste, s.type).map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <fieldset className="champ">
          <legend>Tour</legend>
          <div className="pastilles">
            {tours(manifeste, s.type, s.annee).map((t) => (
              <label key={t} className="pastille">
                <input
                  type="radio"
                  name="tour"
                  value={t}
                  checked={t === s.tour}
                  onChange={() => changer(choisir(manifeste, s.type, s.annee, t))}
                />
                <span>{t === 1 ? "1er tour" : `${t}e tour`}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      <section className="filtres recherche" aria-label="Choix d'une commune au clavier">
        <div className="champ">
          <label className="libelle" htmlFor="commune">
            Commune (nom ou code INSEE)
          </label>
          <input
            id="commune"
            type="search"
            autoComplete="off"
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            aria-describedby="commune-aide"
          />
          <span id="commune-aide" className="aide">
            Deux caractères au moins ; résultats pour le tour affiché.
          </span>
        </div>
        {trouvees?.texte === texte && texte.trim().length >= 2 && (
          <ul className="liste-communes" aria-label="Communes trouvées">
            {trouvees.erreur && <li className="erreur-detail">Recherche indisponible : {trouvees.erreur}</li>}
            {!trouvees.erreur && trouvees.communes.length === 0 && <li>Aucune commune trouvée.</li>}
            {trouvees.communes.map((x) => (
              <li key={x.code}>
                <button type="button" aria-pressed={x.code === codeChoisi} onClick={() => setChoisie(x)}>
                  {x.nom} <span className="mono">{x.code}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="commune-choisie" aria-live="polite">
          {choisie && (
            <>
              <strong>
                {choisie.nom} <span className="mono">{choisie.code}</span> — {s.libelle}
              </strong>
              {c ? <Resultats m={manifeste} etats={etats} car={carChoisie} v={c.valeurs} erreur={c.erreur} /> : <span>Chargement…</span>}
            </>
          )}
        </div>
      </section>

      <section className="section-carte">
        <div className="titre-carte">
          <h2>{s.libelle}</h2>
          <EtiquetteMethode methode={s.methode} />
        </div>
        <figure className="carte">
          <Carte manifeste={manifeste} etats={etats} scrutin={scrutin} onSurvol={setSurvol} onRendu={rendu} />
          {survol && (
            // Infobulle de la souris : non annoncée (aria-hidden) ; au clavier, champ « Commune ».
            <div className="infobulle" aria-hidden="true" style={{ left: survol.x, top: survol.y }}>
              <strong>{d?.nom ?? survol.code}</strong>
              <span className="mono">{survol.code}</span>
              <Resultats m={manifeste} etats={etats} car={car} v={d?.valeurs} erreur={d?.erreur} />
            </div>
          )}
        </figure>
        <Legende etats={etats} scrutin={s} rupture={rupture} />
        <div className="source">
          <p className="source-titre">Source</p>
          <p>
            Résultats : {manifeste.sources.elections.mention}. Contours : {manifeste.sources.ign.mention}.{" "}
            {manifeste.licence_base.mention} Export du {date(manifeste.date_export)}.
          </p>
          <p>
            Bloc en tête : bloc qui totalise le plus de voix dans la commune (somme des voix de ses
            candidats ou listes), et non le bloc de la liste arrivée en tête. En cas d'égalité, la
            commune est en blanc (aucun bloc favorisé). n.d. : résultats présents mais sans voix
            exploitables (dont 0 voix dans la source).
            {sans.length > 0 &&
              ` Tours déclarés sans résultats chargés : ${sans.map((x) => x.libelle).join(", ")}.`}
          </p>
        </div>
      </section>
    </>
  );
}
