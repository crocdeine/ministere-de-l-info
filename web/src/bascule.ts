// Changement de tour sur la carte : deux couches (affichée, cachée), fondu croisé.
// Logique pure (opérations MapLibre injectées), testée par vitest.

/** Au-delà de ce délai de recoloration, le fondu est abandonné (budget ADR-0015). */
export const BUDGET_CHANGEMENT_MS = 100;

export type OpsBascule = {
  /** Couleurs du tour `scrutin` sur la couche `couche` (un seul setPaintProperty). */
  colorer: (couche: number, scrutin: number) => void;
  /** Appelle `fin(true)` quand les tuiles de `couche` sont recalculées, `fin(false)` si elles
   * n'ont pas pu être chargées. */
  attendre: (couche: number, fin: (ok: boolean) => void) => void;
  /** Rend `visible` opaque et l'autre couche transparente, en `dureeMs` (0 = immédiat). */
  afficher: (visible: number, dureeMs: number) => void;
  maintenant: () => number;
  dureeFondu: () => number;
  rendu: (r: { ms: number; fondu: boolean }) => void;
  erreur: () => void;
};

export type Bascule = { choisir: (scrutin: number) => void; affiche: () => number };

/** Une bascule par carte créée : `visible` repart de la couche 0 à chaque recréation. */
export function creerBascule(ops: OpsBascule, initial: number): Bascule {
  let visible = 0;
  let affiche = initial;
  let generation = 0;
  let finFondu = 0;
  return {
    affiche: () => affiche,
    choisir(scrutin) {
      // Toute demande invalide les recalculs en cours, y compris un retour au tour affiché
      // (sinon un recalcul plus ancien basculerait la carte sur un tour qui n'est plus demandé).
      const gen = ++generation;
      if (scrutin === affiche) return;
      // La couche cachée est peut-être encore en train de disparaître : couper le fondu avant
      // de la recolorer, sinon les nouvelles couleurs apparaîtraient pendant sa disparition.
      if (ops.maintenant() < finFondu) {
        ops.afficher(visible, 0);
        finFondu = 0;
      }
      const cachee = 1 - visible;
      const t0 = ops.maintenant();
      ops.colorer(cachee, scrutin);
      ops.attendre(cachee, (ok) => {
        if (gen !== generation) return;
        if (!ok) {
          ops.erreur();
          return;
        }
        const ms = ops.maintenant() - t0;
        const duree = ms <= BUDGET_CHANGEMENT_MS ? ops.dureeFondu() : 0;
        visible = cachee;
        affiche = scrutin;
        ops.afficher(visible, duree);
        finFondu = ops.maintenant() + duree;
        ops.rendu({ ms, fondu: duree > 0 });
      });
    },
  };
}
