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
  const attente = useRef<ReturnType<typeof setInterval>>(undefined);
  const [etat, setEtat] = useState<Etat>(null);
  const [erreurIndex, setErreurIndex] = useState<string | null>(null);
  const [texte, setTexte] = useState("");
  const [ouvert, setOuvert] = useState(false);
  const [actif, setActif] = useState(-1);

  const index = etat && typeof etat === "object" && "index" in etat ? etat.index : null;
  const resultats = useMemo(() => (index ? chercher(index, texte) : []), [index, texte]);

  // Index chargé à la première utilisation (hors du chemin critique d'ouverture).
  // Un échec remet l'état à null : nouvel essai au prochain focus (`relancer`).
  const charger = (relancer = false) => {
    if (etat || !manifeste || (erreurIndex && !relancer)) return;
    const f = manifeste.fichiers[FICHIER];
    if (!f) {
      setErreurIndex("index absent de l'export (réexporter les données).");
      return;
    }
    setErreurIndex(null);
    setEtat("chargement");
    lireJsonGz<BrutIndex>(urlDonnees(FICHIER), f.sha256_brut, FICHIER)
      .then((brut) => setEtat({ index: decoderIndex(brut) }))
      .catch((e: unknown) => {
        setEtat(null);
        setErreurIndex(e instanceof Error ? e.message : String(e));
      });
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
    // Focus sur le titre de la fiche dès qu'elle est affichée (lecteurs d'écran, clavier).
    const nom = index?.communes.get(r.cible);
    let essais = 0;
    clearInterval(attente.current);
    const attendre = (attente.current = setInterval(() => {
      const h1 = document.querySelector<HTMLElement>("main h1");
      if ((nom && h1?.textContent?.includes(nom)) || ++essais > 50) {
        clearInterval(attendre);
        // Pas de vol de focus si l'utilisateur a déjà repris la saisie.
        const reprise = document.activeElement === champ.current && champ.current?.value !== "";
        if (h1 && nom && h1.textContent?.includes(nom) && !reprise) {
          h1.tabIndex = -1;
          h1.focus();
        }
      }
    }, 100));
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
      } else {
        e.preventDefault(); // le champ « search » s'effacerait aussi de lui-même
        setTexte("");
      }
    }
  };

  const saisi = texte.trim().length >= 2;
  const liste = `${id}-liste`;
  const affiche = ouvert && saisi;
  // Messages hors de la listbox (qui ne contient que des options), annoncés par le role=status.
  const message = !affiche
    ? ""
    : !index
      ? erreurIndex
        ? `Recherche indisponible : ${erreurIndex}`
        : "Chargement de l'index…"
      : resultats.length === 0
        ? `Aucun résultat pour « ${texte.trim()} ». Vérifier l'orthographe ou essayer un code ${
            index.codesPostaux ? "postal ou INSEE" : "INSEE (codes postaux non chargés)"
          }.`
        : `${resultats.length} résultat${resultats.length > 1 ? "s" : ""}`;
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
          charger(true);
          if (texte) setOuvert(true);
        }}
        onBlur={() => setOuvert(false)}
        onChange={(e) => {
          clearInterval(attente.current); // l'utilisateur a repris la saisie : pas de focus forcé
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
        hidden={!affiche || resultats.length === 0}
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
      </ul>
      <p className={index && resultats.length > 0 ? "sr-seul" : "r-statut"} role="status" aria-live="polite">
        {message}
      </p>
    </div>
  );
}
