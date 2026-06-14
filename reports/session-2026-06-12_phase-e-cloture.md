# Clôture Phase E — Module Économie

**Date** : 2026-06-12
**Périmètre** : Données économiques INSEE HdF + UI Streamlit
**Statut** : ✅ Terminée

---

## Synthèse exécutive

La Phase E construit le module Économie de A à Z : exploration des sources disponibles (5 rapports Antigravity CLI, juin 2026), décision d'architecture (ADR-0006), ETL INSEE via un dataset OLAP long unique (data.gouv.fr, 1.73 Go national, cache HdF ~40 Mo), chargement en DuckDB (2 tables, 3 vues), et UI Streamlit 3 onglets. Le module expose 7 indicateurs communaux — taux de pauvreté, niveau de vie médian, chômage déclaratif, part ouvriers/employés, part emploi industriel, part logements sociaux, nombre de logements sociaux — pour 3 838 communes HdF sur les millésimes 2015-2021.

Le croisement économie × élections (onglet 3) répond aux 4 questions éditoriales de l'ADR-0006 : les communes les plus pauvres votent-elles RN ? La désindustrialisation prédit-elle le vote EXD ? La part d'ouvriers/employés détermine-t-elle la couleur politique ? Les communes pauvres s'abstiennent-elles ?

---

## Commits Phase E (ordre chronologique)

| SHA | Message |
|-----|---------|
| `cffd2fc` | docs(economie): ADR-0006 — module Économie sources et schéma DuckDB |
| `d93272e` | feat(economie): add ETL scripts for INSEE Filosofi + RP data (Phase E2) |
| `9aaf326` | fix(economie): correct column name in v_croisement_eco_elections |
| `63eede1` | feat(economie): add part_logements_sociaux + nb_logements_sociaux to economie_rp |
| `f9cd9f8` | chore(ci): omit schema_economie.py from coverage (no-DB ETL init) |
| `b33e216` | feat(economie): add Streamlit UI + queries + tests (Phase E3+E4) |

---

## Données chargées

| Table | Lignes | Millésimes | Source |
|-------|--------|------------|--------|
| economie_filosofi | 17 582 | 2017-2021 | INSEE Filosofi |
| economie_rp | 26 538 | 2015-2021 | INSEE RP |

**Indicateurs disponibles (7) :**
- `taux_pauvrete`, `niveau_vie_median` — Filosofi (seuil 60% médiane nationale)
- `tx_chomage_dec`, `part_ouvriers_employes`, `part_emploi_industriel` — RP emploi
- `part_logements_sociaux`, `nb_logements_sociaux` — RP logements (HLM)

**Secret statistique INSEE** : communes < 50 ménages ou données supprimées pour confidentialité — flag `secret = TRUE` dans les deux tables, communes grises sur la carte (`nan_fill_color="#CCCCCC"`).

---

## Architecture technique

**Source unique** : dataset data.gouv.fr `67289477639527408ae687da`
"Recensement de la population communal et Filosofi depuis 2015"
Format OLAP long (`code_com, annee, source, clef_json, valeur`) — 1.73 Go national
Cache HdF local : `data/raw/economie/donnees-insee-olap-hdf.parquet` (~40 Mo)

**Tables DuckDB créées :**
- `economie_filosofi` (PRIMARY KEY `code_commune, annee`)
- `economie_rp` (PRIMARY KEY `code_commune, annee_millesime`)

**Vues DuckDB créées :**
- `v_economie_commune` — jointure Filosofi LEFT JOIN RP sur `annee = annee_millesime`, expose les 7 indicateurs + `pop_active` + `secret_partiel`
- `v_croisement_eco_elections` — économie × présidentielles T2, jointure `v_economie_commune` + `v_scores_commune_pres` + `v_participation_commune_pres`
- `v_evolution_economie_hdf` — agrégats annuels HdF (moyennes régionales), 5 lignes 2017-2021

**Fichiers ETL :**
- `src/ministere_de_l_info/etl/schema_economie.py` — création tables + vues + ALTER IF NOT EXISTS
- `src/ministere_de_l_info/etl/loaders/economie_filosofi.py` — pivot long→wide Filosofi
- `src/ministere_de_l_info/etl/loaders/economie_rp.py` — pivot long→wide RP (emploi + logements)
- `scripts/load_economie.py` — script ETL orchestrateur (téléchargement + chargement)

---

## UI Streamlit

**Page** : `pages/4_📊_Économie.py` → `src/ministere_de_l_info/pages/economie.py`

**Onglet 1 — Carte des indicateurs**
- Sélecteur indicateur (6 Filosofi+RP) + sélecteur année
- Choroplèthe Folium par commune HdF (`geometry_simplified_communal`)
- Secret statistique en gris (`nan_fill_color="#CCCCCC"`)
- Tooltip avec nom commune + valeur formatée
- Expander drill-down : tableau multi-années + line chart Plotly évolution commune

**Onglet 2 — Évolution HdF**
- Line chart Plotly Express : agrégats annuels HdF 2017-2021
- 3 indicateurs sélectionnables : taux de pauvreté, niveau de vie médian, chômage

**Onglet 3 — Économie × Élections**
- Scatter plot : indicateur éco (axe X) × % voix bloc électoral (axe Y) T2
- Sélecteurs : année présidentielle, bloc (EXG/GAU/DIV/CENT/DTE/EXD), indicateur
- Taille des points proportionnelle à `pop_active`
- Note éditoriale : "Corrélation ne signifie pas causalité"
- Pas de trendline OLS (évite dépendance statsmodels)

**Requêtes** : `src/ministere_de_l_info/viz/economie_queries.py`
- 8 fonctions `@st.cache_data` (TTL 3600s)
- Protection SQL injection via `_INDICATEURS_VALIDES = frozenset({...})`
- Connexion DuckDB `read_only=True` dans chaque fonction (open/try/finally/close)

---

## Métriques qualité

| Métrique | Valeur |
|----------|--------|
| Tests totaux (suite complète) | 341 |
| Tests module Économie | 10 |
| Coverage avec DB | 75.34% |
| Coverage sans DB (CI) | ~60.7% |
| Coverage sans DB (local, plancher) | 55% |

---

## Décisions techniques notables

- **Source unique OLAP long** : pivot MAX CASE WHEN clef_json dans les loaders — évite N fichiers CSV par indicateur
- **Suffixe `_p` INSEE RP = effectif pondéré** (pas %) — vérifié empiriquement sur Lille : `actifs_15_64_ans_p = 118 017` (cohérent avec INSEE)
- **Cache HdF local** : évite re-téléchargement 1.73 Go à chaque ETL
- **SQL injection** : `_INDICATEURS_VALIDES frozenset` pour valider les noms de colonnes dans les f-strings (évite appel `@st.cache_data` imbriqué)
- **`geometry_simplified_communal`** utilisée directement depuis la DB — pas de `simplify()` Python supplémentaire
- **Secret statistique** : communes grises `nan_fill_color="#CCCCCC"` + `valeur=NULL` dans les données Choropleth quand `secret=True`
- **`pop_active`** exposé par `v_economie_commune` — pas de JOIN redondant sur `economie_rp` dans `get_croisement_eco_elections`

---

## Sources explorées et décisions

### Intégrées en Phase E
- INSEE Filosofi : revenus/pauvreté communal 2017-2021 ✅
- INSEE RP emploi : chômage déclaratif, CSP 2015-2021 ✅
- INSEE RP logements : HLM par commune ✅

### Identifiées pour Phase E+ (après UI)
- CNAF data.caf.fr : taux RSA par commune (quick win)
- DREES : APL, déserts médicaux par commune (quick win)
- URSSAF open.urssaf.fr : effectifs salariés privés par secteur NAF
- ANCT Observatoire : zonages QPV, ZRR, typologies densité
- INSEE série longue : chômage BIT HdF vs France (zone emploi)
- Eurostat tgs00005 : PIB HdF vs France (NUTS2)

### Écartées définitivement
- DVF (prix immobilier) : hors périmètre éditorial Phase E
- Déserts médicaux série longue : données insuffisamment granulaires pour niveau commune
- IPS établissements scolaires : granularité établissement, pas commune
- Banque de France, Eurostat NUTS2 : granularité département/région insuffisante pour analyse communale

---

## Rapports d'exploration Antigravity

8 rapports produits par sous-agents Antigravity CLI (juin 2026) :
- `reports/exploration-economie-sources.md` — cartographie des sources disponibles
- `reports/exploration-economie-indicateurs.md` — sélection des 7 indicateurs retenus
- `reports/exploration-economie-formats.md` — analyse des formats de données INSEE
- `reports/exploration-economie-benchmark.md` — benchmark des outils ETL
- `reports/exploration-skills-existants.md` — skills Claude Code réutilisables
- `reports/brainstorm-economie-indicateurs-complementaires.md` — pistes Phase E+
- `reports/sweep-sources-economie-elargi.md` — balayage sources élargies
- `reports/verification-sources-economie-contexte.md` — vérification sources contexte

---

## Prochaines étapes (Phase E+)

- [ ] Intégrer CNAF (RSA) + DREES (APL) — quick wins identifiés
- [ ] Intégrer economie_contexte (BIT série longue + PIB Eurostat NUTS2)
- [ ] URSSAF effectifs salariés (désindustrialisation série longue)
- [ ] ANCT zonages QPV/ZRR (filtres UI par type de territoire)
- [ ] Tests AppTest UI économie (`@pytest.mark.slow`)
