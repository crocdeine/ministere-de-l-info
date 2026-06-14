# Phase E+ — Enrichissement module Économie

**Date** : 2026-06-14
**Statut** : ✅ Terminée

## Données chargées

| Table | Lignes | Couverture | Source |
|---|---|---|---|
| economie_social (RSA) | 17 381 | 2020-2024 | CNAF data.caf.fr |
| economie_social (APL) | 3 788 | 2023 | DREES data.gouv.fr |
| economie_emploi_urssaf | 1 157 338 | 2006-2025 | URSSAF open.urssaf.fr |

## Indicateurs ajoutés

- nb_foyers_rsa : allocataires RSA par commune (arrondi ×5 CNAF)
- apl_medecins : APL médecins généralistes (consult/hab/an)
- desert_medical : TRUE si APL < 2.5 (943 communes HdF en zone sous-dense)
- economie_emploi_urssaf : effectifs salariés privés par commune×APE 2006-2025

## Décisions techniques

- Secret statistique CNAF = arrondi ×5 (pas de NULL, pas de flag)
- UPSERT DREES via Arrow → DuckDB ON CONFLICT DO UPDATE
- URSSAF : format wide CSV → Polars melt → long (1.15M lignes HdF)
- DREES XLSX : skiprows=8, détection automatique onglet le plus récent

## Chiffres de référence HdF

- 943 communes HdF en désert médical (25% des communes, millésime 2023)
- Lille 59350 : APL=6.1 (hors désert), ~11 005 foyers RSA 2024

## Tests

- 7 nouveaux tests Phase E+ : tous PASSED
- Total test_economie.py : 17 tests (Phase E 10 + Phase E+ 7)
- Coverage sans DB : 55.01% (plancher pessimiste — CI ≥ 60.7%, documenté)

## Commits

- `7a53dd5` — feat(economie): add Phase E+ loaders — CNAF RSA + URSSAF + DREES APL

## Prochaines étapes (Phase E++)

- Intégrer economie_contexte (BIT série longue + PIB Eurostat)
- Mettre à jour l'UI Streamlit pour afficher RSA, APL, URSSAF
- ANCT zonages QPV/ZRR (filtres UI)
