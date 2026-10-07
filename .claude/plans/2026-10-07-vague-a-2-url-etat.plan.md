# Mission : vague A, lot 2 — état de la vue dans l'URL (partageable)

**Agent** : developpeur-ui · **Branche** : feat/web-url-etat
**Base** : origin/main (après A1) · **Complexité** : S (1 jour)
**Décision d'origine** : feuille de route, vague A (orientations du 2026-10-06, décision 1)
**Dépendances** : A1. **Débloque** : A3 (adresse d'une fiche), A4 (destination des résultats).

## Objectif
Chaque vue (page, scrutin, mode, bloc, territoire, zoom) s'écrit dans l'URL ; recopier l'adresse
redonne exactement la même vue. Dans l'application Mac, un bouton « Copier le lien de cette vue »
produit un lien lisible (texte), et le retour arrière fonctionne.

## Hors périmètre
- Ouverture de liens depuis l'extérieur de l'app (schéma d'URL personnalisé macOS) : à proposer seulement.
- Comptes, favoris, historique persistant.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Sélecteurs | `web/src/App.tsx` (A1) | boutons radio natifs, état React unique |
| Identifiants | `CLAUDE.md`, conventions données | `{YYYY}_{type}_t{N}`, codes INSEE en chaîne |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `web/src/etat-url.ts` | créer | lecture/écriture de l'état (`URLSearchParams`, `history.replaceState`/`pushState`), aucune dépendance |
| `web/src/etat-url.test.ts` | créer | aller-retour état → URL → état ; valeurs invalides |
| `web/src/App.tsx` | modifier | état initial depuis l'URL |

## Tâches
### 1. Schéma d'URL
- **Action** : routage par hachage (`#/elections?scrutin=2022_pres_t1&mode=bloc`), compatible
  Tauri sans serveur ; paramètres courts et lisibles ; codes INSEE jamais convertis en nombre.
- **Valider** : `npx vitest run etat-url`
### 2. Robustesse
- **Action** : paramètre inconnu ou scrutin absent du manifeste → valeur par défaut et message
  discret, jamais d'écran vide.
- **Valider** : tests sur `scrutin=1999_xxx_t9`, `commune=1001` (rejeté, doit être `01001`).

## Garde-fous de neutralité
L'URL ne contient que des identifiants techniques, aucun libellé politique.

## Contraintes du projet
Communes aux fiches (worktree, commits fréquents, pas de push, économie de jetons).

## Validation finale
```bash
cd web && npx tsc --noEmit && npx vitest run && npm run build
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Historique saturé par chaque clic | moyenne | `replaceState` pour les réglages, `pushState` pour un changement de page ou de territoire |

## Acceptation
- [ ] Lien copié → même vue au rechargement (Chromium et `.app`)
- [ ] Retour arrière cohérent
- [ ] Rapport court (résumé ≤ 10 lignes)

## Si l'option B n'est pas retenue
Inchangé pour C et D. Option A (Streamlit) : `st.query_params`, effort comparable.
