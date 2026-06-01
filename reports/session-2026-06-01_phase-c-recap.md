# Phase C — Module Élections présidentielles

**Période :** 2026-05-27 → 2026-06-01
**Statut :** ✅ Terminé (périmètre présidentielles)
**Suite prévue :** Phase D — extension législatives, municipales, granularité bureau de vote

## Objectif initial

Construire un module d'analyse électorale pour le projet ministere-de-l-info, démarrant par les présidentielles 2002-2022, avec focus sur la 21e circonscription du Nord (Valenciennes) et comparaison Hauts-de-France.

## Périmètre livré

- **Scrutins** : présidentielles 2002, 2007, 2012, 2017, 2022 (1er + 2e tour)
- **Géographie** : filtrage Hauts-de-France (code_region = '32'), 5 départements
- **Granularité stockage** : bureau de vote (préservée pour usage futur)
- **Granularité affichage** : commune (agrégation via vues SQL)
- **Volumes chargés** : 63 878 bureaux × 10 scrutins = 452 553 lignes candidats
- **Page UI** : pages/2_🗳️_Élections.py (sélecteurs, carte choroplèthe, graphe d'évolution, tableau)

## Décisions structurantes

1. **Nomenclature officielle Ministère** : adoption des 6 blocs officiels (EXG, GAU, DIV, CENT, DTE, EXD) plutôt qu'une nomenclature maison. Voir ADR-0005.
2. **Classement officiel de l'époque** : un parti est classé selon le bloc qui lui était attribué à la date du scrutin (FI = GAU jusqu'en 2024, EXG seulement à partir de 2026).
3. **Traçabilité par circulaires archivées** : 4 PDF officiels dans docs/sources-officielles/nuances/ + index documenté.
4. **Vues calculées (Option A)** plutôt que tables matérialisées : un changement de classement = une ligne SQL, pas un rechargement.
5. **Bind mount DB en dev Docker** : pas de rebuild quand les données changent en local.

## Commits clés (chronologique)

| Commit | Étape | Description |
|--------|-------|-------------|
| cfeebf9 | C2a | Schéma DuckDB initial (6 tables, 7 blocs maison) |
| 271a594 | C2a-bis | Alignement nomenclature officielle Ministère (6 blocs) |
| ff0b6a0 | C2b | Chargement filtré HdF + 5 vues d'agrégation |
| cbfab71 | C3 | Page Streamlit complète (carte + graphe + tableau) |
| 7c54159 | Fix Docker | Bind mount DB locale en dev |
| 7ee9862 | C4 | Tests d'intégration durables |

## Métriques projet à la clôture

- **Tests** : 184 / 184 verts (+ 2 désélectés par défaut : smoke Streamlit `@pytest.mark.slow`)
- **Coverage** : 75.25% (seuil 60%)
- **CI** : verte sur tous les commits
- **DB** : 914 MB (compression colonnaire DuckDB efficace)
- **Sources archivées** : 4 circulaires officielles + 4 décisions Conseil d'État référencées
- **ADR créés** : 0005 (nuances et blocs officiels)

## Premier résultat concret

Évolution politique de la circo 21 (Valenciennes) au 1er tour, sur 25 ans :

| Année | Bloc dominant | Voix |
|-------|---------------|------|
| 2002 | GAU | 16 994 |
| 2007 | DTE | 20 268 |
| 2012 | GAU | 25 234 |
| 2017 | EXD | 18 311 |
| 2022 | EXD | 21 637 |

## Points reportés à la Phase D

1. **Législatives 2002-2024** (6 scrutins, 19→24 nuances selon millésime)
2. **Municipales 2008-2026** (4 scrutins, granularité liste pour communes >3500 hab)
3. **Granularité bureau de vote dans l'UI** (sélecteur commune + vue BV + carte zoomée — données déjà chargées en stockage)
4. **Décision à acter** : France entière ou HdF uniquement pour les futurs scrutins

## Leçons techniques tirées

- Les codes INSEE de circonscriptions trouvés sur le web sont peu fiables — toujours valider par jointure spatiale ST_Within
- Le nommage des Parquet data.gouv est inversé (general-results = candidats, candidats-results = participation) — piège documenté en C1
- Les named volumes Docker isolent du host : préférer bind mounts en dev pour éviter les rebuilds
- Les blocs de clivages officiels n'existent que depuis sénatoriales 2023 (IOMA2322276J), avant on reconstruit selon la nomenclature officielle datée

## État de la branche main

Tag : v0.3-elections-pres
Commit final de la phase : 7ee9862
