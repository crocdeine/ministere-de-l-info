# Mission : vague A, lot 5 — page Méthodologie et glossaire

**Agent** : documentaliste (rédaction) + developpeur-ui (page) · **Branche** : feat/web-methodologie
**Base** : origin/main (après A1) · **Complexité** : M (2-3 jours, relecture de Mathias comprise)
**Décision d'origine** : feuille de route, vague A (remplace les renvois vers `docs/adr/`, illisibles pour l'utilisateur)
**Dépendances** : A1. Parallélisable avec A2-A4.

## Objectif
Une page lisible par un non-spécialiste qui explique d'où viennent les chiffres et comment ils
sont calculés : sources et licences, classement des nuances en blocs (grilles officielles 2020,
2023, 2026 et reconstruction pour les autres scrutins), dénominateurs, valeurs absentes,
ruptures entre scrutins, limites connues ; plus un glossaire (nuance, bloc, exprimés,
inscrits, tour, circonscription, EPCI…). Chaque visualisation renvoie à la section utile.

## Hors périmètre
- Toute modification des classements ou des ADR (relecture seulement, écarts signalés).
- Contenu juridique nouveau (la note CNCCFP relève de la vague D).

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Classements | `docs/adr/0005`, `0010`, `0011`, `0013` | citer la doctrine, pas la paraphraser au-delà |
| Sources | `src/ministere_de_l_info/sources.py`, `docs/sources.md` | registre unique ; la page est générée depuis le registre |
| Légendes | `_blocs_politiques.py:50` | `legende_classement_blocs` |
| Ton | `docs/guide-utilisateur.md` | phrases courtes, sans jargon |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `docs/methodologie.md` | créer | texte source unique (Markdown), versionné et relu |
| `src/ministere_de_l_info/export_web/` | modifier | export de la table des sources et de la table nuance → bloc (229 correspondances) en JSON |
| `web/src/pages/Methodologie.tsx` | créer | rendu du Markdown (sans bibliothèque si possible : texte compilé au build) + ancres |

## Tâches
### 1. Rédaction
- **Action** : sections Sources, Blocs politiques, Calculs, Valeurs absentes, Ruptures, Limites,
  Glossaire ; chaque affirmation renvoie à sa source officielle (circulaire, jeu de données).
- **Valider** : relecture de Mathias (texte éditorial = décision de fond).
### 2. Page et ancres
- **Action** : ancres stables (`#blocs`, `#valeurs-absentes`…) ; lien « Méthode » sous chaque
  visualisation ; tableau consultable des correspondances nuance → bloc par scrutin.
- **Valider** : `npx vitest run` (toutes les ancres citées existent).

## Garde-fous de neutralité
La page est le support des garde-fous 1 à 6 : elle les énonce ; le classement est présenté
comme une convention documentée (« reconstruction par le projet » quand aucune grille
officielle n'existe), jamais comme un fait.

## Contraintes du projet
Communes aux fiches ; aucune modification de classement.

## Validation finale
```bash
uv run pytest -m "not slow and not network"
cd web && npx tsc --noEmit && npx vitest run && npm run build
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Écart entre texte et code | moyenne | tables générées depuis la base et `sources.py`, pas recopiées |
| Formulations orientées | moyenne | relecture Mathias ; liste de mots proscrits du garde-fou 6 |

## Acceptation
- [ ] Texte validé par Mathias
- [ ] Liens « Méthode » partout ; plus aucun lien vers `docs/adr/` dans l'interface
- [ ] Rapport court

## Si l'option B n'est pas retenue
Rédaction inchangée ; seul le rendu change (page Streamlit `st.markdown` en option A).
