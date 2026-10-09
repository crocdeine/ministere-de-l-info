import { useEffect, useState } from "react";
import { chargerManifeste, type Manifeste } from "./donnees";
import { FicheCommune } from "./FicheCommune";
import { PageElections } from "./PageElections";

// Navigation : 5 entrées (comme l'application Streamlit). Pages non portées : renvoi vers
// la version Streamlit. Numérotation « 0X — » (ADR-0016 : pas de code couleur par module).
export const PAGES = [
  { id: "accueil", numero: "00", titre: "Accueil" },
  { id: "geographie", numero: "01", titre: "Géographie" },
  { id: "elections", numero: "02", titre: "Élections" },
  { id: "economie", numero: "03", titre: "Économie" },
  { id: "legislatif", numero: "04", titre: "Législatif" },
] as const;
// Fiche commune (lot A3) : page hors navigation, ouverte depuis la carte, la commune choisie
// ou un lien (`#/commune?code=80021`).
type IdPage = (typeof PAGES)[number]["id"] | "commune";
const PORTEES: ReadonlySet<IdPage> = new Set(["elections", "commune"]);

function pageCourante(): IdPage {
  const id = location.hash.replace(/^#\/?/, "").split(/[/?]/)[0];
  if (id === "commune") return "commune";
  return PAGES.find((p) => p.id === id)?.id ?? "elections";
}

export function App() {
  const [page, setPage] = useState<IdPage>(pageCourante);
  const [manifeste, setManifeste] = useState<Manifeste | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    const suivre = () => setPage(pageCourante());
    addEventListener("hashchange", suivre);
    return () => removeEventListener("hashchange", suivre);
  }, []);

  useEffect(() => {
    chargerManifeste()
      .then(setManifeste)
      .catch((e: unknown) => setErreur(e instanceof Error ? e.message : String(e)));
  }, []);

  const info = PAGES.find((p) => p.id === page) ?? PAGES[2];
  return (
    <>
      <header className="bandeau">
        <p className="eyebrow">Ministère de l'Info</p>
        <nav aria-label="Pages">
          <ul className="navigation">
            {PAGES.map((p) => (
              <li key={p.id}>
                <a href={`#/${p.id}`} aria-current={p.id === page ? "page" : undefined}>
                  <span className="mono">{p.numero}</span> {p.titre}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main className="page">
        {!PORTEES.has(page) ? (
          <section className="entete">
            <p className="overline">{info.numero} —</p>
            <h1>{info.titre}</h1>
            <p className="chapo">
              Cette page n'est pas encore portée dans l'application. Elle reste disponible dans la
              version Streamlit.
            </p>
          </section>
        ) : erreur ? (
          <p className="alerte" role="alert">
            Données non disponibles : {erreur} Générer les fichiers :{" "}
            <code>uv run python scripts/export_web.py</code>
          </p>
        ) : !manifeste ? (
          <p className="overline" aria-busy="true">
            Chargement…
          </p>
        ) : page === "commune" ? (
          <FicheCommune manifeste={manifeste} />
        ) : (
          <PageElections manifeste={manifeste} numero={info.numero} />
        )}
      </main>
    </>
  );
}
