import { Component, lazy, type ReactNode, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import type { Scrutin } from "./donnees";
import type { Etat } from "./etats";
import type { Ancre } from "./markdown";
import "./methodologie.css";

/** Échec de chargement du contenu (morceau paresseux) : message et nouvel essai, jamais de page blanche. */
class Repli extends Component<{ reessayer: () => void; children: ReactNode }, { echec: boolean }> {
  state = { echec: false };
  static getDerivedStateFromError() {
    return { echec: true };
  }
  render() {
    if (!this.state.echec) return this.props.children;
    return (
      <p className="alerte" role="alert">
        Méthodologie indisponible.{" "}
        <button type="button" className="lien-methode" onClick={this.props.reessayer}>
          Réessayer
        </button>
      </p>
    );
  }
}

/** Méthodologie affichée en page (`#/methodologie`) : même contenu que le panneau. */
export function PageMethodologie() {
  const [essai, setEssai] = useState(0);
  const Methodologie = useMemo(() => lazy(() => import("./Methodologie")), [essai]);
  return (
    <Repli key={essai} reessayer={() => setEssai((n) => n + 1)}>
      <Suspense fallback={<p aria-busy="true">Chargement…</p>}>
        <Methodologie ancre="" />
      </Suspense>
    </Repli>
  );
}

/** Panneau unique de la page : une seule fenêtre `<dialog>`, quel que soit le nombre de liens. */
function Panneau({ initiale, enregistrer }: { initiale: Ancre; enregistrer: (f: (a: Ancre) => void) => void }) {
  const panneau = useRef<HTMLDialogElement>(null);
  const [ancre, setAncre] = useState<Ancre>(initiale);
  const [ouvert, setOuvert] = useState(false);
  const [essai, setEssai] = useState(0);
  const fondPresse = useRef(false);
  // Contenu chargé à la demande ; recréé à chaque nouvel essai (React garde l'échec d'un `lazy`).
  const Methodologie = useMemo(() => lazy(() => import("./Methodologie")), [essai]);

  useEffect(() => {
    const ouvrir = (a: Ancre) => {
      setAncre(a);
      setOuvert(true);
      if (!panneau.current?.open) panneau.current?.showModal();
    };
    enregistrer(ouvrir);
    ouvrir(initiale);
  }, [enregistrer, initiale]);

  return (
    <dialog
      ref={panneau}
      className="panneau-methodologie"
      aria-label="Méthodologie"
      onClose={() => setOuvert(false)}
      // Clic sur le fond : fermeture seulement si l'appui et le relâchement y ont lieu tous deux
      // (une sélection de texte commencée dans le panneau ne le ferme pas).
      onPointerDown={(e) => (fondPresse.current = e.target === panneau.current)}
      onPointerUp={(e) => {
        if (fondPresse.current && e.target === panneau.current) panneau.current.close();
        fondPresse.current = false;
      }}
    >
      <div className="panneau-barre">
        <p className="overline">Méthodologie</p>
        <button type="button" className="panneau-fermer" onClick={() => panneau.current?.close()}>
          Fermer
        </button>
      </div>
      {ouvert && (
        <Repli key={essai} reessayer={() => setEssai((n) => n + 1)}>
          <Suspense fallback={<p aria-busy="true">Chargement…</p>}>
            <Methodologie ancre={ancre} />
          </Suspense>
        </Repli>
      )}
    </dialog>
  );
}

let ouvrirPanneau: ((a: Ancre) => void) | null = null;

/** Ouvre le panneau Méthodologie à la section `ancre` (racine React propre, créée au premier appel). */
export function ouvrirMethodologie(ancre: Ancre) {
  if (ouvrirPanneau) return ouvrirPanneau(ancre);
  const hote = document.body.appendChild(document.createElement("div"));
  createRoot(hote).render(<Panneau initiale={ancre} enregistrer={(f) => (ouvrirPanneau = f)} />);
}

/**
 * Bouton qui ouvre la Méthodologie à la section `ancre`, sans quitter la vue (ADR-0016, point 6 ;
 * décision du 2026-10-07, point 5). Fenêtre modale native : Échap et « Fermer » la referment.
 */
export function LienMethode({ ancre, className, titre, children }: { ancre: Ancre; className: string; titre?: string; children: ReactNode }) {
  return (
    <button type="button" className={className} title={titre} aria-haspopup="dialog" onClick={() => ouvrirMethodologie(ancre)}>
      {children}
    </button>
  );
}

/** Étiquette de méthode du classement des blocs (ADR-0016) : ouvre la Méthodologie. */
export function EtiquetteMethode({ methode }: { methode: Scrutin["methode"] }) {
  const officielle = methode === "officielle";
  return (
    <LienMethode
      ancre="methode"
      className="etiquette-methode"
      titre={
        officielle
          ? "Classement des blocs selon la grille officielle du ministère de l'Intérieur pour ce scrutin. Ouvrir la méthodologie."
          : "Aucune grille officielle pour ce scrutin : classement reconstruit par le projet. Ouvrir la méthodologie."
      }
    >
      {officielle ? "Grille officielle" : "Reconstruit"}
    </LienMethode>
  );
}

type Props = { etats: Etat[]; scrutin: Scrutin; rupture: boolean };

export function Legende({ etats, scrutin, rupture }: Props) {
  return (
    <>
      <ul className="legende" aria-label="Légende : bloc arrivé en tête dans la commune">
        {etats.map((e) => (
          <li key={e.car}>
            <span
              className={e.couleur ? "carre" : "carre vide"}
              style={e.couleur ? { background: e.couleur } : undefined}
            />
            {e.libelle}
          </li>
        ))}
      </ul>
      {rupture && (
        <p className="limite" role="status">
          <span className="limite-titre">Limite</span> Changement de type de scrutin ou de grille de
          classement : nuances et blocs ne sont pas directement comparables d'un scrutin à l'autre.{" "}
          <LienMethode ancre="ruptures" className="lien-methode">
            Ruptures entre scrutins
          </LienMethode>
        </p>
      )}
      <p className="methode">
        {scrutin.legende}{" "}
        <LienMethode ancre="blocs" className="lien-methode">
          Méthode
        </LienMethode>
      </p>
    </>
  );
}
