import { lazy, type ReactNode, Suspense, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Scrutin } from "./donnees";
import type { Etat } from "./etats";
import type { Ancre } from "./markdown";
import "./methodologie.css";

// Contenu du panneau chargé à la demande (texte et tables hors du JS initial).
const Methodologie = lazy(() => import("./Methodologie"));

/**
 * Ouvre le panneau Méthodologie à la section `ancre`, sans quitter la vue (ADR-0016, point 6 ;
 * décision du 2026-10-07, point 5). Fenêtre modale native : Échap et « Fermer » la referment.
 */
export function LienMethode({ ancre, className, titre, children }: { ancre: Ancre; className: string; titre?: string; children: ReactNode }) {
  const panneau = useRef<HTMLDialogElement>(null);
  const [ouvert, setOuvert] = useState(false);
  return (
    <>
      <button
        type="button"
        className={className}
        title={titre}
        aria-haspopup="dialog"
        onClick={() => {
          setOuvert(true);
          panneau.current?.showModal();
        }}
      >
        {children}
      </button>
      {/* Portail : un <dialog> ne peut pas être imbriqué dans un paragraphe de légende. */}
      {createPortal(
      <dialog
        ref={panneau}
        className="panneau-methodologie"
        aria-label="Méthodologie"
        onClose={() => setOuvert(false)}
        // Clic sur le fond (hors du contenu) : fermeture.
        onClick={(e) => e.target === panneau.current && panneau.current.close()}
      >
        <div className="panneau-barre">
          <p className="overline">Méthodologie</p>
          <button type="button" className="panneau-fermer" onClick={() => panneau.current?.close()}>
            Fermer
          </button>
        </div>
        {ouvert && (
          <Suspense fallback={<p aria-busy="true">Chargement…</p>}>
            <Methodologie ancre={ancre} />
          </Suspense>
        )}
      </dialog>,
      document.body,
      )}
    </>
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
