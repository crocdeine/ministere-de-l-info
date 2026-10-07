# Mission : vague A, lot 4 — recherche globale

**Agent** : developpeur-ui (+ ingenieur-etl pour l'index) · **Branche** : feat/web-recherche
**Base** : origin/main (après A3) · **Complexité** : M (2-3 jours)
**Décision d'origine** : feuille de route, vague A ; décision 8 du 2026-10-06 (recherche individuelle des élus)
**Dépendances** : A1, A2, A3.

## Objectif
Un champ de recherche unique, toujours visible, qui trouve une commune (nom, code INSEE, code
postal exclu), un département, une circonscription ou un élu, et ouvre la fiche ou la vue
correspondante. Tolère accents, tirets et « Saint/St ».

## Hors périmètre
- Recherche plein texte dans les données ou la documentation ; suggestions populaires ; historique.
- Classement d'élus par un indicateur (écarté, décision 8).

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Index | `src/ministere_de_l_info/export_web/` (A1) | export SQL, champ normalisé calculé à l'export |
| Élus | vue `v_elus_actuels` | nom, prénom, chambre, circonscription ; aucune date de naissance |
| Navigation | `web/src/etat-url.ts` (A2) | résultat = changement d'URL |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `src/ministere_de_l_info/export_web/index_recherche.py` | créer | `recherche.json` : type, code, libellé, libellé normalisé, département |
| `web/src/Recherche.tsx`, `web/src/recherche.ts` (+ test) | créer | filtrage par préfixe et sous-chaîne normalisés, sans bibliothèque |

## Tâches
### 1. Index
- **Action** : ≈ 35 000 communes + 101 départements + 577 circonscriptions + élus en exercice ;
  normalisation (NFD sans diacritiques, minuscules, tirets → espaces) faite en Python.
- **Valider** : taille gzip < 1 Mo ; test pytest d'unicité des clés.
### 2. Composant
- **Action** : combobox ARIA (motif WAI-ARIA « combobox » natif), flèches, Entrée, Échap ;
  homonymes départagés par le département ; tri : correspondance exacte, préfixe, sous-chaîne.
- **Valider** : `npx vitest run recherche` (« saint-etienne », « 75056 », « Bourg » homonymes).

## Garde-fous de neutralité
Ordre des résultats purement lexical ; aucun résultat mis en avant ; aucun libellé politique dans les suggestions.

## Contraintes du projet
Communes aux fiches.

## Validation finale
```bash
uv run pytest -m "not slow and not network" && uvx pyright@1.1.408
cd web && npx tsc --noEmit && npx vitest run && npm run build
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Latence de saisie sur 35 000 entrées | faible | filtrage linéaire < 10 ms mesuré ; worker si besoin seulement |
| Code postal attendu par l'utilisateur | moyenne | message « recherche par nom ou code INSEE » (gotcha 4) |

## Acceptation
- [ ] Commune, département, circonscription, élu trouvés et ouverts au clavier
- [ ] Rapport court

## Si l'option B n'est pas retenue
Option C : requête `ILIKE` sur une table Parquet ; option A : `st.selectbox` filtrable.
