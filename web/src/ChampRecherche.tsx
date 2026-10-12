// Recherche globale (lot A4) : champ permanent du bandeau, motif WAI-ARIA « combobox » (liste).
// Commune, département, circonscription, élu ; le résultat change l'URL (`#/commune?code=…`).
// Raccourcis : ⌘K / Ctrl+K, ou « / » hors d'un champ. Aucun résultat mis en avant (ordre lexical).
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { lireJsonGz, type Manifeste, urlDonnees } from "./donnees";
import { type BrutIndex, chercher, decoderIndex, type Index, type Resultat } from "./recherche";
import "./recherche.css";

const TYPES = { c: "Commune", d: "Département", e: "Circonscription" } as const;
const FICHIER = "recherche.json.gz";

type Etat = { index: Index } | { erreur: string } | "chargement" | null;

export function meta(r: Resultat, index: Index): string {
  const e = r.entree;
  const dep = index.departements[e.dep] ?? e.dep;
  const lieu = `${dep} (${e.dep})`;
  if (e.type === "c") return `Commune · ${lieu} · ${e.code}${r.codePostal ? ` · code postal ${r.codePostal}` : ""}`;
  const debut = e.type === "u" ? `${e.extra} · ${lieu}` : `${TYPES[e.type]} · ${lieu}`;
  return `${debut} · ouvre la fiche de ${index.communes.get(r.cible) ?? r.cible} (commune la plus peuplée)`;
}

export function Recherche({ manifeste }: { manifeste: Manifeste | null }) {
  const id = useId();
  const champ = useRef<HTMLInputElement>(null);
  const [etat, setEtat] = useState<Etat>(null);
  const [texte, setTexte] = useState("");
  const [ouvert, setOuvert] = useState(false);
  const [actif, setActif] = useState(-1);

  const index = etat && typeof etat === "object" && "index" in etat ? etat.index : null;
  const resultats = useMemo(() => (index ? chercher(index, texte) : []), [index, texte]);

  // Index chargé à la première utilisation (hors du chemin critique d'ouverture).
  const charger = () => {
    if (etat || !manifeste) return;
    const f = manifeste.fichiers[FICHIER];
    if (!f) {
      setEtat({ erreur: "index absent de l'export (réexporter les données)." });
      return;
    }
    setEtat("chargement");
    lireJsonGz<BrutIndex>(urlDonnees(FICHIER), f.sha256_brut, FICHIER)
      .then((brut) => setEtat({ index: decoderIndex(brut) }))
      .catch((e: unknown) => setEtat({ erreur: e instanceof Error ? e.message : String(e) }));
  };

  useEffect(() => {
    const touche = (e: KeyboardEvent) => {
      const cible = e.target as HTMLElement | null;
      const dansChamp = !!cible && (/^(INPUT|TEXTAREA|SELECT)$/.test(cible.tagName) || cible.isContentEditable);
      if (((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") || (e.key === "/" && !dansChamp && !e.metaKey && !e.ctrlKey)) {
        e.preventDefault();
        champ.current?.focus();
        champ.current?.select();
      }
    };
    addEventListener("keydown", touche);
    return () => removeEventListener("keydown", touche);
  }, []);

  const ouvrir = (r: Resultat) => {
    location.hash = `#/commune?code=${r.cible}`;
    setTexte("");
    setOuvert(false);
    setActif(-1);
    champ.current?.blur();
  };

  const surTouche = (e: React.KeyboardEvent<HTMLInputElement>) => {
    const n = resultats.length;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!n) return;
      setOuvert(true);
      const pas = e.key === "ArrowDown" ? 1 : -1;
      setActif(actif < 0 ? (pas > 0 ? 0 : n - 1) : (actif + pas + n) % n);
    } else if (e.key === "Enter") {
      const r = resultats[actif < 0 ? 0 : actif];
      if (ouvert && r) {
        e.preventDefault();
        ouvrir(r);
      }
    } else if (e.key === "Escape") {
      if (ouvert) {
        e.preventDefault();
        setOuvert(false);
        setActif(-1);
      } else setTexte("");
    }
  };

  const saisi = texte.trim().length >= 2;
  const liste = `${id}-liste`;
  const erreur = etat && typeof etat === "object" && "erreur" in etat ? etat.erreur : null;
  const placeholder = index && !index.codesPostaux ? "Commune, code INSEE, département, élu" : "Commune, code postal, département, élu";
  return (
    <div className="recherche-globale" role="search">
      <label className="sr-seul" htmlFor={`${id}-champ`}>
        Rechercher une commune, un département, une circonscription ou un élu
      </label>
      <input
        ref={champ}
        id={`${id}-champ`}
        type="search"
        role="combobox"
        autoComplete="off"
        spellCheck={false}
        placeholder={placeholder}
        aria-expanded={ouvert && saisi}
        aria-controls={liste}
        aria-autocomplete="list"
        aria-activedescendant={ouvert && actif >= 0 ? `${id}-o${actif}` : undefined}
        value={texte}
        onFocus={() => {
          charger();
          if (texte) setOuvert(true);
        }}
        onBlur={() => setOuvert(false)}
        onChange={(e) => {
          setTexte(e.target.value);
          setOuvert(true);
          setActif(-1);
          charger();
        }}
        onKeyDown={surTouche}
      />
      <kbd className="raccourci" aria-hidden="true">
        ⌘K
      </kbd>
      <ul
        id={liste}
        role="listbox"
        aria-label="Résultats de la recherche"
        className="resultats-recherche"
        hidden={!(ouvert && saisi)}
        onMouseDown={(e) => e.preventDefault()}
      >
        {resultats.map((r, i) => (
          <li
            key={`${r.entree.type}:${r.entree.code}`}
            id={`${id}-o${i}`}
            role="option"
            aria-selected={i === actif}
            onClick={() => ouvrir(r)}
            onMouseMove={() => i !== actif && setActif(i)}
          >
            <span className="r-libelle">{r.entree.libelle}</span>
            <span className="r-meta">{meta(r, index as Index)}</span>
          </li>
        ))}
        {ouvert && saisi && index && resultats.length === 0 && (
          <li role="presentation" className="r-vide">
            Aucun résultat pour « {texte.trim()} ». Vérifier l'orthographe ou essayer un code{" "}
            {index.codesPostaux ? "postal ou INSEE" : "INSEE (codes postaux non chargés)"}.
          </li>
        )}
        {ouvert && saisi && !index && (
          <li role="presentation" className="r-vide">
            {erreur ? `Recherche indisponible : ${erreur}` : "Chargement de l'index…"}
          </li>
        )}
      </ul>
      <p className="sr-seul" role="status" aria-live="polite">
        {ouvert && saisi && index ? `${resultats.length} résultat${resultats.length > 1 ? "s" : ""}` : ""}
      </p>
    </div>
  );
}
