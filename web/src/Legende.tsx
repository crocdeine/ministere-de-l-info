import type { Scrutin } from "./donnees";
import type { Etat } from "./etats";

/** Étiquette de méthode du classement des blocs (ADR-0016) ; panneau Méthodologie : lot A5. */
export function EtiquetteMethode({ methode }: { methode: Scrutin["methode"] }) {
  const officielle = methode === "officielle";
  return (
    <span
      className="etiquette-methode"
      title={
        officielle
          ? "Classement des blocs selon la grille officielle du ministère de l'Intérieur pour ce scrutin."
          : "Aucune grille officielle pour ce scrutin : classement reconstruit par le projet (ADR-0010)."
      }
    >
      {officielle ? "Grille officielle" : "Reconstruit"}
    </span>
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
          classement : nuances et blocs ne sont pas directement comparables d'un scrutin à l'autre.
        </p>
      )}
      <p className="methode">{scrutin.legende}</p>
    </>
  );
}
