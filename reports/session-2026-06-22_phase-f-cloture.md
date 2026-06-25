# Clôture Phase F — Module Législatif

**Date** : 2026-06-22
**Périmètre** : Données parlementaires nationales (AN + Sénat) + UI Streamlit
**Statut** : ✅ Terminée (limitations documentées)

---

## Synthèse exécutive

Le module Législatif a été construit en 3 sous-phases (F1, F2/F2.2, F3). En cours de route, deux changements majeurs :

1. **Pivot HdF → national** : la portée initiale (HdF seul) a été élargie à la France entière dès F2.2, HdF devenant un filtre UI parmi d'autres.
2. **Panne de 2 APIs tierces** : NosDéputés.fr (endpoint métriques désactivé depuis la dissolution 2024) et API CLAIR (panne serveur totale) ont été abandonnées. Bascule réussie sur Datan (data.gouv.fr, CSV historique 2002-présent) + Sénat CSV officiel (data.senat.fr ODSEN_GENERAL).

La page Streamlit remplace le placeholder et livre 4 onglets fonctionnels avec filtres Chambre + Département.

---

## Commits Phase F (chronologique)

```
01afbd5 feat(legislatif): add Phase F1 schema + Sénat loader + overrides
ff645f7 feat(legislatif): switch to national scope + Datan source (Phase F2.2)
c3ec0f9 feat(legislatif): add Streamlit UI + queries + tests (Phase F3)
```

---

## Données en base

| Table | Lignes | Source | Contenu |
|---|---|---|---|
| leg_elus | 4065 | Datan (AN) + Sénat CSV | Élus nationaux 2002-présent (actifs + anciens) |
| leg_activite | 1653 | Datan (AN uniquement) | Scores participation, loyauté, majorité |
| leg_blocs_override | 2 | Corrections manuelles | Hochart + Szczurek (NI Sénat → EXD) |

### Vues SQL

| Vue | Rôle |
|---|---|
| v_elus_hdf_actuels | Élus actifs avec bloc_final (COALESCE override) |
| v_activite_par_bloc | Agrégats d'activité par bloc × chambre |

### Répartition actuelle (élus actifs)

**AN (577)** : CENT:163, EXD:139, GAU:123, EXG:71, DTE:48, DIV:33
**Sénat (348)** : DTE:151, GAU:83, CENT:59, DIV:55

---

## Sources abandonnées (documentées, code non conservé)

| Source | Raison d'abandon | Date constat |
|---|---|---|
| NosDéputés.fr (métriques) | Endpoint désactivé depuis dissolution 2024 | Phase F1 |
| API CLAIR | Panne serveur totale, non récupérable | Phase F1 |

---

## UI Streamlit — 4 onglets

### Tab 1 — Composition politique
- Camembert(s) par bloc_final, couleurs officielles (circulaire 2026)
- Mode "Toutes" : 2 camemberts côte à côte (AN | Sénat)
- Métriques par bloc sous le graphique

### Tab 2 — Liste des élus
- Dataframe filtrable (925 élus national, ~85 HdF)
- Recherche par nom (text_input + filtre Polars)
- Colonnes : nom, prénom, chambre, département, circo, groupe, bloc, profession

### Tab 3 — Activité parlementaire
- AN uniquement (message informatif si Sénat sélectionné)
- Sélecteur indicateur (participation, loyauté, majorité, participation spécialisée)
- Bar chart horizontal top 20 + tableau détaillé
- Activité moyenne par bloc politique (bar chart comparatif)

### Tab 4 — Évolution historique
- Stacked bar chart : composition AN par législature (12e à 17e, 2002-présent)
- Annotations des périodes (dissolution 16e en juin 2024)
- Tableau détaillé dépliable par législature

### Filtres globaux
- **Chambre** : Toutes / Assemblée nationale / Sénat
- **Département** : Tous (France) / Hauts-de-France (région) / département individuel

---

## Architecture technique

### Fichiers créés (Phase F3)

| Fichier | Lignes | Rôle |
|---|---|---|
| `src/ministere_de_l_info/viz/legislatif_queries.py` | 468 | 10 fonctions requêtes DuckDB cachées |
| `src/ministere_de_l_info/pages/legislatif.py` | 411 | render() + 4 onglets Streamlit |
| `pages/3_🏛️_Législatif.py` | 5 | Entry point (remplace placeholder) |

### Fonctions de requêtes

1. `is_data_loaded()` — vérifie AN + SENAT présents
2. `get_chambres()` — ['AN', 'SENAT']
3. `get_departements_disponibles()` — départements + comptage élus actifs
4. `get_elus_actuels(chambre, codes_departement)` — élus actifs, bloc_final via COALESCE override
5. `get_composition_politique(chambre, codes_departement)` — GROUP BY bloc_final
6. `get_activite_elu(elu_id, chambre)` — scores d'un élu
7. `get_classement_activite(chambre, indicateur, codes_departement, n)` — top N, frozenset validation
8. `get_activite_par_bloc(codes_departement)` — moyennes par bloc (AN)
9. `get_historique_legislatures_an()` — législatures distinctes + comptages
10. `get_evolution_composition_an()` — composition par législature et bloc

### Sécurité SQL
- Paramètres dynamiques via `?` (prepared statements)
- Indicateurs d'activité validés via `_INDICATEURS_ACTIVITE_VALIDES` (frozenset)
- Helper `_dept_clause()` pour construction paramétrisée des clauses IN

---

## Tests

- 7 tests F3 ajoutés à `tests/test_legislatif.py`
- 30 tests législatif total (F1 + F2 + F3)
- 381 tests suite complète, 75.34% coverage
- CI verte : run 28172899736, SHA c3ec0f9

---

## Limitations connues

1. **Pas de scores Sénat** : Datan ne couvre que l'AN. Message informatif en UI.
2. **Pas de votes nominatifs** : les scrutins publics AN sont en XML brut (data.assemblee-nationale.fr), non parsés. Nécessiterait un parser XML dédié.
3. **Législature de référence Datan** : chaque député est compté dans sa dernière législature (champ `legislatureLast`). L'évolution historique est donc approximative pour les députés multi-mandats.
4. **region_nom NULL pour Datan** : le CSV Datan ne contient pas la région, champ NULL pour les députés AN.

---

## Prochaines pistes possibles (non planifiées)

- Parser les scrutins publics AN (XML → votes nominatifs par élu)
- Ajouter les scores d'activité Sénat si une source fiable devient disponible
- Croiser législatif × élections (ex: le député sortant a-t-il été réélu ?)
- Croiser législatif × économie (profil socio-économique des circonscriptions)
