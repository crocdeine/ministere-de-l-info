// Contenu du panneau Méthodologie (chargé à la demande) : texte de docs/methodologie.md,
// compilé dans ce module au build, et tables lues dans methodologie.json.gz (export Python).
import { type ReactNode, useEffect, useMemo, useState } from "react";
import texte from "../../docs/methodologie.md?raw";
import { chargerManifeste, ErreurDonnees, entier, lireJsonGz, type Manifeste, urlDonnees } from "./donnees";
import { analyser, type Bloc, morceaux } from "./markdown";

type Donnees = {
  sources: { donnees: string; producteur: string; licence: string; url: string }[];
  correspondances: { annee: number[]; origine: string[]; code: string[]; bloc: string[]; justification: string[] };
};

const BLOCS = analyser(texte);

function aller(id: string) {
  document.getElementById(id)?.scrollIntoView({ block: "start" });
}

function Ligne({ texte }: { texte: string }) {
  return (
    <>
      {morceaux(texte).map((m, i) => {
        if (m.t === "gras") return <strong key={i}>{m.v}</strong>;
        if (m.t === "code") return <code key={i}>{m.v}</code>;
        if (m.t === "texte") return m.v;
        // Ancre interne : défilement dans le panneau, sans toucher au hash (routage des pages).
        if (m.cible.startsWith("#"))
          return (
            <a key={i} href={m.cible} onClick={(e) => (e.preventDefault(), aller(m.cible.slice(1)))}>
              {m.v}
            </a>
          );
        return (
          <a key={i} href={m.cible} target="_blank" rel="noreferrer">
            {m.v}
          </a>
        );
      })}
    </>
  );
}

function Table({ entete, lignes }: { entete: ReactNode[]; lignes: ReactNode[][] }) {
  return (
    <div className="meth-table">
      <table>
        <thead>
          <tr>
            {entete.map((c, i) => (
              <th key={i} scope="col">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((l, i) => (
            <tr key={i}>
              {l.map((c, j) => (
                <td key={j}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Correspondances({ d, m }: { d: Donnees["correspondances"]; m: Manifeste }) {
  const annees = useMemo(() => [...new Set(d.annee)].sort((a, b) => b - a), [d]);
  const [annee, setAnnee] = useState<number | "toutes">(() => annees[0] ?? "toutes");
  const blocs = new Map(m.blocs.map((b) => [b.code, b]));
  const lignes = d.annee.flatMap((a, i) => {
    if (annee !== "toutes" && a !== annee) return [];
    const b = blocs.get(d.bloc[i] as string);
    return [
      [
        <span className="mono">{a}</span>,
        d.origine[i] === "nuance" ? <code>{d.code[i]}</code> : d.code[i],
        <span className="meth-bloc">
          <span className="carre" style={b ? { background: b.couleur } : undefined} />
          {b?.libelle ?? d.bloc[i]}
        </span>,
        d.justification[i],
      ],
    ];
  });
  return (
    <>
      <div className="champ">
        <label className="libelle" htmlFor="meth-annee">
          Année
        </label>
        <select
          id="meth-annee"
          value={annee}
          onChange={(e) => setAnnee(e.target.value === "toutes" ? "toutes" : Number(e.target.value))}
        >
          <option value="toutes">Toutes</option>
          {annees.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>
      <p className="meth-compte" aria-live="polite">
        {entier(lignes.length)} correspondance{lignes.length > 1 ? "s" : ""}
      </p>
      <Table entete={["Année", "Code ou candidat", "Bloc", "Justification"]} lignes={lignes} />
    </>
  );
}

function rendre(b: Bloc, i: number, insertions: Record<string, ReactNode>): ReactNode {
  switch (b.t) {
    case "titre": {
      const Titre = b.niveau <= 1 ? "h2" : b.niveau === 2 ? "h3" : "h4";
      return (
        <Titre key={i} id={b.id}>
          {b.texte}
        </Titre>
      );
    }
    case "p":
      return (
        <p key={i}>
          <Ligne texte={b.texte} />
        </p>
      );
    case "source":
      return (
        <p key={i} className="meth-source">
          <Ligne texte={b.texte} />
        </p>
      );
    case "ul":
    case "ol": {
      const Liste = b.t;
      return (
        <Liste key={i}>
          {b.items.map((x, j) => (
            <li key={j}>
              <Ligne texte={x} />
            </li>
          ))}
        </Liste>
      );
    }
    case "table":
      return (
        <Table
          key={i}
          entete={b.entete.map((c, j) => <Ligne key={j} texte={c} />)}
          lignes={b.lignes.map((l) => l.map((c, j) => <Ligne key={j} texte={c} />))}
        />
      );
    case "insertion":
      return <div key={i}>{insertions[b.nom] ?? null}</div>;
  }
}

export default function Methodologie({ ancre }: { ancre: string }) {
  const [etat, setEtat] = useState<{ m: Manifeste; d: Donnees } | string | null>(null);

  useEffect(() => {
    chargerManifeste()
      .then(async (m) => {
        const info = m.fichiers["methodologie.json.gz"];
        if (!info) throw new ErreurDonnees("methodologie.json.gz absent de l'export.");
        const d = await lireJsonGz<Donnees>(urlDonnees("methodologie.json.gz"), info.sha256_brut, "methodologie.json.gz");
        setEtat({ m, d });
      })
      .catch((e: unknown) => setEtat(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => aller(ancre), [ancre]);

  const absent = (
    <p className="alerte" role="status">
      Données non disponibles{typeof etat === "string" ? ` : ${etat}` : "."}
    </p>
  );
  const insertions: Record<string, ReactNode> =
    etat === null
      ? { sources: <p aria-busy="true">Chargement…</p>, correspondances: <p aria-busy="true">Chargement…</p> }
      : typeof etat === "string"
        ? { sources: absent, correspondances: absent }
        : {
            sources: (
              <Table
                entete={["Données", "Producteur", "Licence", "Lien"]}
                lignes={etat.d.sources.map((s) => [
                  s.donnees,
                  s.producteur,
                  s.licence,
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {new URL(s.url).hostname}
                  </a>,
                ])}
              />
            ),
            correspondances: <Correspondances d={etat.d.correspondances} m={etat.m} />,
          };

  return <div className="methodologie">{BLOCS.map((b, i) => rendre(b, i, insertions))}</div>;
}
