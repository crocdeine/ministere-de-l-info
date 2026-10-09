// Fiche territoire « commune » (lot A3) : identité, chiffres-clés, historique électoral
// (graphique + tableau équivalent), bureaux de vote, élus, territoire, économie, sources.
// Aucun commentaire rédigé, aucune tendance calculée : valeurs, méthode et ruptures seulement.
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { date, entier, lireJsonGz, type Manifeste, ND, pct, urlDonnees } from "./donnees";
import {
  avecRuptures,
  blocEnTete,
  type ColonnesDep,
  codeDepuisHash,
  departementDe,
  derniereValeur,
  type FichesDep,
  filtrer,
  LIBELLES_RAISONS,
  type Ligne,
  lignesBureaux,
  lignesCommune,
  mentionFusion,
  raisonsSerie,
} from "./fiche";
import { GraphiqueEvolution } from "./GraphiqueEvolution";
import { EtiquetteMethode } from "./Legende";

const NC = { code: "NC", libelle: "Non classé" };

const ECONOMIE: { cle: string; libelle: string; format: (v: number) => string; source: string }[] = [
  { cle: "taux_pauvrete", libelle: "Taux de pauvreté", format: pct, source: "insee_filosofi_rp" },
  { cle: "niveau_vie_median", libelle: "Niveau de vie médian", format: (v) => `${entier(v)} €`, source: "insee_filosofi_rp" },
  { cle: "tx_chomage_dec", libelle: "Taux de chômage (recensement)", format: pct, source: "insee_filosofi_rp" },
  { cle: "part_ouvriers_employes", libelle: "Part des ouvriers et employés", format: pct, source: "insee_filosofi_rp" },
  { cle: "part_emploi_industriel", libelle: "Part de l'emploi industriel", format: pct, source: "insee_filosofi_rp" },
  { cle: "part_logements_sociaux", libelle: "Part des logements sociaux", format: pct, source: "insee_filosofi_rp" },
  { cle: "nb_foyers_rsa", libelle: "Foyers allocataires du RSA", format: entier, source: "cnaf" },
  {
    cle: "apl_medecins",
    libelle: "Accessibilité aux médecins généralistes (APL)",
    format: (v) => v.toLocaleString("fr-FR", { maximumFractionDigits: 2 }),
    source: "drees",
  },
];

type Donnees = { dep: string; communes: ColonnesDep; fiches: FichesDep };
type Tri = { cle: string; sens: 1 | -1 };

function fichierDep(m: Manifeste, rel: string) {
  return lireJsonGz<never>(urlDonnees(rel), m.fichiers[rel]?.sha256_brut, rel);
}

const ordinal = (n: number) => (n === 1 ? "1re" : `${n}e`);
const circonscription = (code: string) => `${ordinal(Number(code.split("-")[1]))} circonscription`;

function Source({ m, cles, children }: { m: Manifeste; cles: string[]; children?: ReactNode }) {
  return (
    <div className="source">
      <p className="source-titre">Source</p>
      <p>
        {cles.map((c) => m.sources[c]?.mention ?? c).join(" ; ")}. {children}
      </p>
    </div>
  );
}

export function FicheCommune({ manifeste: m }: { manifeste: Manifeste }) {
  const [code, setCode] = useState(() => codeDepuisHash(location.hash));
  const [donnees, setDonnees] = useState<Donnees | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [type, setType] = useState(() => (m.scrutins.some((s) => s.type === "pres") ? "pres" : ""));
  const [tour, setTour] = useState(1);
  const [tri, setTri] = useState<Tri>({ cle: "rang", sens: 1 });
  const [copie, setCopie] = useState<"ok" | "echec" | null>(null);
  const [bureaux, setBureaux] = useState<ColonnesDep | "chargement" | string | null>(null);
  const [rangBv, setRangBv] = useState<number | null>(null);

  useEffect(() => {
    const suivre = () => setCode(codeDepuisHash(location.hash));
    addEventListener("hashchange", suivre);
    return () => removeEventListener("hashchange", suivre);
  }, []);

  const dep = code ? departementDe(code, m) : null;
  useEffect(() => {
    setDonnees(null);
    setErreur(null);
    setBureaux(null);
    setRangBv(null);
    if (!dep) return;
    let annule = false;
    Promise.all([
      fichierDep(m, `departements/${dep}/communes.json.gz`),
      fichierDep(m, `departements/${dep}/fiches.json.gz`),
    ])
      .then(([communes, fiches]) => {
        if (!annule) setDonnees({ dep, communes, fiches });
      })
      .catch((e: unknown) => !annule && setErreur(e instanceof Error ? e.message : String(e)));
    return () => {
      annule = true;
    };
  }, [m, dep]);

  const info = code && donnees ? donnees.fiches.communes[code] : undefined;
  const toutes = useMemo(
    () => (code && donnees ? lignesCommune(m, donnees.communes, code, info) : []),
    [m, donnees, code, info],
  );
  const serie = useMemo(() => avecRuptures(filtrer(toutes, type, tour)), [toutes, type, tour]);

  useEffect(() => {
    if (copie !== "ok") return;
    const t = setTimeout(() => setCopie(null), 2000);
    return () => clearTimeout(t);
  }, [copie]);

  const entete = (titre: string, texte: ReactNode) => (
    <section className="entete">
      <p className="overline">Commune —</p>
      <h1>{titre}</h1>
      <p className="chapo">{texte}</p>
    </section>
  );
  if (code === null) return entete("Fiche commune", "Aucune commune indiquée dans l'adresse (exemple : #/commune?code=80021).");
  if (code === "" || !dep)
    return entete("Fiche commune", `Commune inconnue dans les données exportées (code « ${new URLSearchParams(location.hash.split("?")[1]).get("code")} »).`);
  if (erreur)
    return (
      <p className="alerte" role="alert">
        Données non disponibles : {erreur}
      </p>
    );
  if (!donnees)
    return (
      <p className="overline" aria-busy="true">
        Chargement de la fiche…
      </p>
    );
  if (!info) return entete("Fiche commune", `Commune « ${code} » inconnue dans les données exportées.`);

  const blocs = m.blocs;
  const libelleBloc = (c: string | null) =>
    c === null ? ND : c === "=" ? "Égalité entre blocs" : (blocs.find((b) => b.code === c)?.libelle ?? NC.libelle);
  const fd = donnees.fiches.departement;
  const derniere = toutes.at(-1);
  const pop = info.population.filter((p) => p[1] !== null).at(-1);
  const raisons = raisonsSerie(serie);
  const methodes = [...new Set(serie.map((l) => l.scrutin.methode))];
  const typesPresents = Object.entries(m.types).filter(([t]) => toutes.some((l) => l.scrutin.type === t));
  const sansResultat = m.scrutins.length - toutes.length;
  const deputes = donnees.fiches.elus.filter((e) => e.chambre === "AN" && e.circo && info.circos.includes(e.circo));
  const senateurs = donnees.fiches.elus.filter((e) => e.chambre === "SENAT");
  const colonnes = [...blocs.map((b) => ({ code: b.code, libelle: b.libelle, couleur: b.couleur })), { ...NC, couleur: m.couleur_nd }];

  const valeurTri = (l: Ligne): number | null =>
    tri.cle === "rang" ? l.rang : tri.cle === "inscrits" ? l.inscrits : tri.cle === "participation" ? l.participation : (l.parts[tri.cle] ?? null);
  const triees = [...serie].sort((a, b) => {
    const va = valeurTri(a);
    const vb = valeurTri(b);
    if (va === null) return vb === null ? 0 : 1; // n.d. toujours en fin de tableau
    if (vb === null) return -1;
    return (va - vb) * tri.sens;
  });
  const enTeteTri = (cle: string, contenu: ReactNode) => (
    <th scope="col" aria-sort={tri.cle === cle ? (tri.sens === 1 ? "ascending" : "descending") : undefined}>
      <button type="button" className="tri" onClick={() => setTri((t) => ({ cle, sens: t.cle === cle ? ((-t.sens) as 1 | -1) : cle === "rang" ? 1 : -1 }))}>
        {contenu}
      </button>
    </th>
  );
  const remarques = (l: Ligne) =>
    [
      ...(l.raisons.length ? [`Rupture avec la ligne précédente : ${l.raisons.map((r) => LIBELLES_RAISONS[r]).join(", ")}`] : []),
      mentionFusion(l.anciennes),
      l.plurinominal ? "Scrutin plurinominal : somme des voix supérieure aux exprimés, parts non calculées" : null,
      l.nonClasseSeul ? "Aucune nuance attribuée : toutes les voix sont non classées" : null,
    ].filter(Boolean);

  const choixBv = rangBv ?? serie.at(-1)?.rang ?? derniere?.rang ?? null;
  const ouvrirBv = (ouvert: boolean) => {
    if (!ouvert || bureaux !== null) return;
    setBureaux("chargement");
    fichierDep(m, `departements/${donnees.dep}/bureaux.json.gz`)
      .then((b) => setBureaux(b as ColonnesDep))
      .catch((e: unknown) => setBureaux(`Détail non disponible : ${e instanceof Error ? e.message : String(e)}`));
  };
  const bv = typeof bureaux === "object" && bureaux !== null && choixBv !== null ? lignesBureaux(m, bureaux, code, choixBv) : [];

  const copier = async () => {
    try {
      await navigator.clipboard.writeText(location.href);
      setCopie("ok");
    } catch {
      setCopie("echec");
    }
  };

  return (
    <>
      <nav aria-label="Fil d'Ariane" className="ariane">
        France › {fd.region ?? ND} › {fd.nom ?? ND} › <span aria-current="page">{info.nom}</span>
      </nav>
      <section className="entete">
        <p className="overline">Commune —</p>
        <h1>{info.nom}</h1>
        <p className="sous-titre">
          Code INSEE <span className="mono">{code}</span> · {fd.nom ?? ND} ({fd.code})
        </p>
      </section>
      <p className="aide">
        <button type="button" onClick={copier}>
          Copier le lien de cette fiche
        </button>{" "}
        <a href={`#/elections?commune=${code}`}>Voir la commune sur la carte des élections</a>{" "}
        <span role="status">
          {copie === "ok" && "Lien copié."}
          {copie === "echec" && (
            <>
              Copie impossible : sélectionnez l'adresse <code className="mono">{location.href}</code>
            </>
          )}
        </span>
      </p>

      <section aria-labelledby="t-chiffres">
        <h2 id="t-chiffres">Chiffres-clés</h2>
        <dl className="chiffres">
          <div>
            <dt>Population municipale {pop?.[0] ?? ""}</dt>
            <dd>{entier(pop?.[1])}</dd>
          </div>
          <div>
            <dt>Inscrits — {derniere?.scrutin.libelle ?? ND}</dt>
            <dd>{entier(derniere?.inscrits)}</dd>
          </div>
          <div>
            <dt>Participation — {derniere?.scrutin.libelle ?? ND}</dt>
            <dd>{pct(derniere?.participation)}</dd>
          </div>
          <div>
            <dt>Bloc en tête — {derniere?.scrutin.libelle ?? ND}</dt>
            <dd className="chiffre-texte">{derniere ? libelleBloc(blocEnTete(derniere)) : ND}</dd>
            {derniere && <EtiquetteMethode methode={derniere.scrutin.methode} />}
          </div>
        </dl>
        <Source m={m} cles={["insee_pop", "elections"]}>
          Bloc en tête : bloc qui totalise le plus de voix (somme des voix de ses candidats ou listes), en % des
          suffrages exprimés.
        </Source>
      </section>

      <section aria-labelledby="t-historique" className="section">
        <h2 id="t-historique">Historique électoral</h2>
        <div className="filtres" role="group" aria-label="Scrutins affichés">
          <div className="champ">
            <label className="libelle" htmlFor="fiche-type">
              Type de scrutin
            </label>
            <select id="fiche-type" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">Tous les types</option>
              {typesPresents.map(([t, libelle]) => (
                <option key={t} value={t}>
                  {libelle}
                </option>
              ))}
            </select>
          </div>
          <div className="champ">
            <label className="libelle" htmlFor="fiche-tour">
              Tour
            </label>
            <select id="fiche-tour" value={tour} onChange={(e) => setTour(Number(e.target.value))}>
              <option value={1}>1er tour</option>
              <option value={2}>2e tour</option>
              <option value={0}>Les deux tours</option>
            </select>
          </div>
        </div>

        {serie.length === 0 ? (
          <p className="chapo">Aucun résultat pour cette commune avec ces critères.</p>
        ) : (
          <>
            {raisons.length > 0 && serie.length > 1 && (
              <p className="limite" role="note">
                <span className="limite-titre">Comparaison limitée</span> Entre certains scrutins affichés, changent :{" "}
                {raisons.map((r) => LIBELLES_RAISONS[r]).join(" ; ")}. Les lignes du graphique sont interrompues à
                chaque rupture ; le détail figure dans la colonne « Remarques » du tableau.
              </p>
            )}
            <div className="titre-carte">
              <h3>Voix par bloc, en % des suffrages exprimés</h3>
              {methodes.map((x) => (
                <EtiquetteMethode key={x} methode={x} />
              ))}
            </div>
            <figure className="plaque">
              <GraphiqueEvolution
                lignes={serie}
                series={colonnes.map((c) => ({ cle: c.code, libelle: c.code, couleur: c.couleur }))}
                valeur={(l, c) => l.parts[c] ?? null}
                description={`Voix par bloc en % des exprimés, ${serie.length} scrutins ; valeurs dans le tableau ci-dessous.`}
              />
            </figure>
            <ul className="legende" aria-label="Légende des blocs">
              {colonnes.map((c) => (
                <li key={c.code}>
                  <span className="carre" style={{ background: c.couleur }} /> {c.code} — {c.libelle}
                </li>
              ))}
            </ul>
            <h3>Participation, en % des inscrits</h3>
            <figure className="plaque">
              <GraphiqueEvolution
                lignes={serie}
                series={[{ cle: "p", libelle: "Particip.", couleur: "var(--ink)" }]}
                valeur={(l) => l.participation}
                description={`Participation en % des inscrits, ${serie.length} scrutins ; valeurs dans le tableau ci-dessous.`}
              />
            </figure>

            <div className="tableau-defilant">
              <table className="tableau">
                <caption>Résultats par scrutin (cliquer un en-tête pour trier)</caption>
                <thead>
                  <tr>
                    {enTeteTri("rang", "Scrutin")}
                    <th scope="col">Méthode</th>
                    {enTeteTri("inscrits", "Inscrits")}
                    {enTeteTri("participation", "Participation")}
                    {colonnes.map((c) => (
                      <th key={c.code} scope="col" aria-sort={tri.cle === c.code ? (tri.sens === 1 ? "ascending" : "descending") : undefined}>
                        <button
                          type="button"
                          className="tri"
                          title={c.libelle}
                          onClick={() => setTri((t) => ({ cle: c.code, sens: t.cle === c.code ? ((-t.sens) as 1 | -1) : -1 }))}
                        >
                          <span className="carre" style={{ background: c.couleur }} /> {c.code}
                        </button>
                      </th>
                    ))}
                    <th scope="col">Remarques</th>
                  </tr>
                </thead>
                <tbody>
                  {triees.map((l) => (
                    <tr key={l.rang} className={l.raisons.length ? "rupture" : undefined}>
                      <th scope="row">{l.scrutin.libelle}</th>
                      <td>
                        <EtiquetteMethode methode={l.scrutin.methode} />
                      </td>
                      <td className="mono">{entier(l.inscrits)}</td>
                      <td className="mono">{pct(l.participation)}</td>
                      {colonnes.map((c) => (
                        <td key={c.code} className="mono">
                          {pct(l.parts[c.code])}
                        </td>
                      ))}
                      <td className="remarques">{remarques(l).join(". ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <p className="methode">
          Parts en % des suffrages exprimés ; participation = votants / inscrits. Blocs : classement propre à
          chaque scrutin (colonne « Méthode » ; légende du classement dans la page Élections).
          {sansResultat > 0 &&
            ` Aucun résultat pour cette commune à ${entier(sansResultat)} des ${entier(m.scrutins.length)} tours chargés (second tour non organisé, commune hors du champ publié ou inexistante à cette date).`}
        </p>
        <Source m={m} cles={["elections"]}>
          Niveau : commune (bureaux de vote agrégés). {m.licence_base.mention} Export du {date(m.date_export)}.
        </Source>

        <details className="details-bv" onToggle={(e) => ouvrirBv(e.currentTarget.open)}>
          <summary>Détail par bureau de vote</summary>
          {bureaux === "chargement" && <p aria-busy="true">Chargement des bureaux de vote…</p>}
          {typeof bureaux === "string" && bureaux !== "chargement" && <p className="erreur-detail">{bureaux}</p>}
          {typeof bureaux === "object" && bureaux !== null && (
            <>
              <div className="champ">
                <label className="libelle" htmlFor="fiche-bv">
                  Scrutin
                </label>
                <select id="fiche-bv" value={choixBv ?? ""} onChange={(e) => setRangBv(Number(e.target.value))}>
                  {toutes.map((l) => (
                    <option key={l.rang} value={l.rang}>
                      {l.scrutin.libelle}
                    </option>
                  ))}
                </select>
              </div>
              <p className="aide">
                Les bureaux de vote et leurs numéros changent d'un scrutin à l'autre : pas de comparaison entre
                scrutins à ce niveau.
              </p>
              {bv.length === 0 ? (
                <p>Données non disponibles pour ce scrutin.</p>
              ) : (
                <div className="tableau-defilant">
                  <table className="tableau">
                    <caption>
                      {bv.length} bureaux de vote — {bv[0]?.scrutin.libelle}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Bureau</th>
                        <th scope="col">Inscrits</th>
                        <th scope="col">Participation</th>
                        {colonnes.map((c) => (
                          <th key={c.code} scope="col" title={c.libelle}>
                            <span className="carre" style={{ background: c.couleur }} /> {c.code}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {bv.map((l) => (
                        <tr key={l.bv}>
                          <th scope="row" className="mono">
                            {l.bv}
                          </th>
                          <td className="mono">{entier(l.inscrits)}</td>
                          <td className="mono">{pct(l.participation)}</td>
                          {colonnes.map((c) => (
                            <td key={c.code} className="mono">
                              {pct(l.parts[c.code])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <Source m={m} cles={["elections"]}>
                Niveau : bureau de vote. Parts en % des exprimés du bureau.
              </Source>
            </>
          )}
        </details>
      </section>

      <section aria-labelledby="t-elus" className="section">
        <h2 id="t-elus">Représentée par</h2>
        <h3>Députés</h3>
        {info.circos.length > 1 && (
          <p className="aide">
            Commune partagée entre {info.circos.length} circonscriptions : chacune a son député.
          </p>
        )}
        {deputes.length === 0 ? (
          <p>Données non disponibles.</p>
        ) : (
          <ul className="elus">
            {deputes.map((e) => (
              <li key={`${e.circo}-${e.nom}`}>
                <strong>
                  {e.prenom} {e.nom}
                </strong>{" "}
                — {e.circo ? circonscription(e.circo) : ND} · groupe {e.groupe ?? ND}
                {e.groupe_nom && e.groupe_nom !== e.groupe ? ` (${e.groupe_nom})` : ""} · bloc{" "}
                <span className="carre" style={{ background: blocs.find((b) => b.code === e.bloc)?.couleur ?? m.couleur_nd }} />{" "}
                {libelleBloc(e.bloc)}
              </li>
            ))}
          </ul>
        )}
        <h3>Sénateurs du département</h3>
        {senateurs.length === 0 ? (
          <p>Données non disponibles.</p>
        ) : (
          <ul className="elus">
            {senateurs.map((e) => (
              <li key={`${e.nom}-${e.prenom}`}>
                <strong>
                  {e.prenom} {e.nom}
                </strong>{" "}
                — groupe {e.groupe ?? ND} · bloc{" "}
                <span className="carre" style={{ background: blocs.find((b) => b.code === e.bloc)?.couleur ?? m.couleur_nd }} />{" "}
                {libelleBloc(e.bloc)}
              </li>
            ))}
          </ul>
        )}
        <Source m={m} cles={["datan", "senat", "circos"]}>
          Élus en cours de mandat ; bloc : celui du groupe parlementaire pour la législature (non-inscrits : bloc
          de leur nuance d'élection). Sénat : composition chargée avant le renouvellement du 27 septembre 2026.
          Circonscriptions : intersection des contours de la commune et des circonscriptions (découpage de 2010).
        </Source>
      </section>

      <section aria-labelledby="t-territoire" className="section">
        <h2 id="t-territoire">Territoire</h2>
        <dl className="identite">
          <dt>Département</dt>
          <dd>
            {fd.nom ?? ND} ({fd.code})
          </dd>
          <dt>Région</dt>
          <dd>{fd.region ?? ND}</dd>
          <dt>Intercommunalité (EPCI)</dt>
          <dd>{info.epci ?? ND}</dd>
          <dt>Circonscription(s) législative(s)</dt>
          <dd>{info.circos.length ? info.circos.map(circonscription).join(", ") : ND}</dd>
        </dl>
        <table className="tableau">
          <caption>Population municipale (populations légales)</caption>
          <thead>
            <tr>
              <th scope="col">Millésime</th>
              <th scope="col">Habitants</th>
            </tr>
          </thead>
          <tbody>
            {info.population.length === 0 ? (
              <tr>
                <td colSpan={2}>Données non disponibles</td>
              </tr>
            ) : (
              info.population.map(([a, p]) => (
                <tr key={a}>
                  <th scope="row" className="mono">
                    {a}
                  </th>
                  <td className="mono">{entier(p)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <Source m={m} cles={["insee_pop", "ign"]}>
          Niveau : commune. Communes anciennes rattachées : signalées dans l'historique électoral.
        </Source>
      </section>

      <section aria-labelledby="t-economie" className="section">
        <h2 id="t-economie">Économie</h2>
        {info.economie === null ? (
          <p className="chapo">Données économiques disponibles pour les Hauts-de-France uniquement pour l'instant.</p>
        ) : (
          <table className="tableau">
            <caption>Dernière valeur disponible par indicateur</caption>
            <thead>
              <tr>
                <th scope="col">Indicateur</th>
                <th scope="col">Valeur</th>
                <th scope="col">Année</th>
              </tr>
            </thead>
            <tbody>
              {ECONOMIE.map((x) => {
                const v = info.economie ? derniereValeur(info.economie, x.cle) : null;
                return (
                  <tr key={x.cle}>
                    <th scope="row">{x.libelle}</th>
                    <td className="mono">{v ? x.format(v[1]) : "n.d. (secret statistique ou donnée absente)"}</td>
                    <td className="mono">{v ? v[0] : ND}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <Source m={m} cles={["insee_filosofi_rp", "cnaf", "drees"]}>
          Niveau : commune. APL : consultations accessibles par an et par habitant.
        </Source>
      </section>
    </>
  );
}
