import { useEffect, useMemo, useState } from "react";
import { Carte, type Rendu, type Survol, token } from "./Carte";
import { date, entier, type Manifeste, pct, urlDonnees } from "./donnees";
import { annees, choisir, etats as listeEtats, libelleEtat, scrutinInitial, tours } from "./etats";
import { EtiquetteMethode, Legende } from "./Legende";
import { journal, noter } from "./mesure";
import type { Demande, Reponse } from "./worker/details";

const URL_COMMUNES = urlDonnees("communes.json.gz");

export function PageElections({ manifeste, numero }: { manifeste: Manifeste; numero: string }) {
  const etats = useMemo(() => listeEtats(manifeste, token), [manifeste]);
  const [scrutin, setScrutin] = useState(() => scrutinInitial(manifeste));
  const [rupture, setRupture] = useState(false);
  const [survol, setSurvol] = useState<Survol>(null);
  const [detail, setDetail] = useState<Reponse | null>(null);
  const [carteAffichee, setCarteAffichee] = useState(false);
  const worker = useMemo(
    () => new Worker(new URL("./worker/details.ts", import.meta.url), { type: "module" }),
    [],
  );
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

  useEffect(() => {
    worker.onmessage = (e: MessageEvent<Reponse>) => setDetail(e.data);
    return () => worker.terminate();
  }, [worker]);

  const demande = (type: Demande["type"], code = ""): Demande | null =>
    s
      ? {
          type,
          code,
          urlCommunes: URL_COMMUNES,
          scrutin: s.id,
          url: urlDonnees(`scrutins/${s.id}.json.gz`),
        }
      : null;

  // Résultats détaillés : préchargés après la première carte (budget des données d'ouverture).
  useEffect(() => {
    const d = carteAffichee ? demande("precharger") : null;
    if (d) worker.postMessage(d);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carteAffichee, scrutin, worker]);

  useEffect(() => {
    const d = survol ? demande("commune", survol.code) : null;
    if (d) worker.postMessage(d);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [survol?.code, scrutin, worker]);

  const rendu = (r: Rendu) => {
    if (r.type === "premiere") setCarteAffichee(true);
    noter(r);
  };

  if (!s) return <p className="alerte">Aucun scrutin dans les données exportées.</p>;
  const d = detail?.code === survol?.code && detail?.scrutin === s.id ? detail : null;
  const v = d?.valeurs;
  // État lu pour le scrutin choisi (et non au moment du survol) : juste après un changement.
  const car = survol?.s[scrutin] ?? manifeste.codage.absent;
  const blocEnTete = manifeste.blocs.some((b) => b.car === car);
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

      <section className="section-carte">
        <div className="titre-carte">
          <h2>{s.libelle}</h2>
          <EtiquetteMethode methode={s.methode} />
        </div>
        <figure className="carte">
          <Carte manifeste={manifeste} etats={etats} scrutin={scrutin} onSurvol={setSurvol} onRendu={rendu} />
          {survol && (
            <div className="infobulle" role="status" style={{ left: survol.x, top: survol.y }}>
              <strong>{d?.nom ?? survol.code}</strong>
              <span className="mono">{survol.code}</span>
              <span>{libelleEtat(etats, car)}</span>
              {v && blocEnTete && <span>Part du bloc en tête : {pct(v.part_tete)} des exprimés</span>}
              {v && <span>Participation : {pct(v.participation)}</span>}
              {v && <span>Inscrits : {entier(v.inscrits)}</span>}
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
            Bloc en tête : somme des voix des candidats ou listes de chaque bloc dans la commune. En
            cas d'égalité, la commune est en blanc (aucun bloc favorisé).
            {sans.length > 0 &&
              ` Tours déclarés sans résultats chargés : ${sans.map((x) => x.libelle).join(", ")}.`}
          </p>
        </div>
      </section>
    </>
  );
}
