# 0006 — Module Économie : sources, indicateurs et schéma DuckDB

Date : 2026-06-11
Statut : Accepté
Décideurs : Mathias (supervision)

## Contexte

Le module Économie est le 3e module de données du projet ministere-de-l-info
(après Géographie v0.2 et Élections v0.4). Il doit permettre de croiser des
données économiques territoriales avec les données électorales existantes pour
les Hauts-de-France.

5 rapports d'exploration (Antigravity CLI, juin 2026) ont établi :
- Les sources disponibles en open data à granularité communale
- Les indicateurs pertinents pour l'analyse politique-économique
- Les formats techniques et pièges d'intégration
- Le positionnement différenciant du projet (croisement élections × économie)

## Décisions

### D1 — Sources retenues

**Décision** : Trois sources INSEE en open data, toutes à granularité communale.

| Source | Indicateurs | Millésimes |
|---|---|---|
| INSEE Filosofi | Taux de pauvreté, niveau de vie médian | 2012→2022 (annuel) |
| INSEE Recensement de la Population (RP) | Taux de chômage déclaratif, part ouvriers/employés, niveau de diplôme | 2006→2022 (millésimes glissants 5 ans) |
| INSEE Sirene | Évolution emploi industriel (code APE NAF) | 2010→présent (stock annuel) |

**Rejetées** :
- Taux de chômage BIT INSEE → granularité zone d'emploi uniquement, pas commune
- France Travail → seuil 5 000 habitants, élimine la majorité des communes HdF
- PIB communal → n'existe pas en open data officiel
- Banque de France / DARES → granularité département/région uniquement

### D2 — Indicateurs retenus (5 indicateurs prioritaires)

**Décision** : 5 indicateurs pour le module v1, sélectionnés pour leur
pertinence électorale et leur disponibilité communale.

| Indicateur | Source | Colonne DB | Pertinence électorale |
|---|---|---|---|
| Taux de pauvreté | Filosofi | `taux_pauvrete` | Très forte — corrélé vote EXD/EXG |
| Niveau de vie médian | Filosofi | `niveau_vie_median` | Forte — polarisation électorale |
| Taux de chômage déclaratif | RP | `tx_chomage_dec` | Forte — seule granularité commune |
| Part ouvriers + employés | RP | `part_ouvriers_employes` | Très forte — tissu HdF |
| Part emploi industriel | Sirene | `part_emploi_industriel` | Forte — désindustrialisation |

**Non retenus en v1** : niveau de diplôme (pertinent mais redondant avec CSP),
PIB (pas de données communales), indicateurs France Travail (granularité insuffisante).

### D3 — Structure des tables DuckDB

**Décision** : Structure large (une colonne par indicateur) par cohérence
avec les tables électorales existantes (`resultats_participation`,
`resultats_candidats`). Deux tables séparées par source pour isoler
les logiques de chargement et les millésimes différents.

```sql
-- Table Filosofi (revenus/pauvreté)
CREATE TABLE economie_filosofi (
    code_commune        VARCHAR(5)  NOT NULL,
    annee               INTEGER     NOT NULL,
    taux_pauvrete       DOUBLE,     -- % ménages sous seuil 60% revenu médian national
    niveau_vie_median   DOUBLE,     -- niveau de vie médian en euros
    d1_niveau_vie       DOUBLE,     -- 1er décile
    d9_niveau_vie       DOUBLE,     -- 9e décile
    secret              BOOLEAN     DEFAULT FALSE,  -- TRUE si données masquées INSEE
    PRIMARY KEY (code_commune, annee)
);

-- Table Recensement de la Population (emploi/CSP)
CREATE TABLE economie_rp (
    code_commune            VARCHAR(5)  NOT NULL,
    annee_millesime         INTEGER     NOT NULL,  -- ex: 2020 = données 2016-2020
    tx_chomage_dec          DOUBLE,     -- taux chômage déclaratif recensement
    part_ouvriers_employes  DOUBLE,     -- % ouvriers + employés dans pop active
    part_emploi_industriel  DOUBLE,     -- % emplois dans secteur industriel (NAF C)
    pop_active              INTEGER,    -- population active totale
    secret                  BOOLEAN     DEFAULT FALSE,
    PRIMARY KEY (code_commune, annee_millesime)
);
```

**Justification structure large vs longue** :
- Cohérence avec `resultats_participation` et `resultats_candidats` (déjà large)
- Requêtes de croisement plus simples (JOIN direct sur `code_commune + annee`)
- Nombre d'indicateurs limité (5) — pas de risque d'explosion de colonnes

### D4 — Vues SQL de croisement

**Décision** : Trois vues pour l'UI Streamlit.

```sql
-- Vue 1 : indicateurs économiques par commune (toutes sources fusionnées)
CREATE VIEW v_economie_commune AS
SELECT
    f.code_commune,
    f.annee,
    f.taux_pauvrete,
    f.niveau_vie_median,
    r.tx_chomage_dec,
    r.part_ouvriers_employes,
    r.part_emploi_industriel,
    (f.secret OR COALESCE(r.secret, FALSE)) AS secret_partiel
FROM economie_filosofi f
LEFT JOIN economie_rp r
    ON f.code_commune = r.code_commune
    AND f.annee = r.annee_millesime;

-- Vue 2 : croisement économie × résultats électoraux (présidentielles)
CREATE VIEW v_croisement_eco_elections AS
SELECT
    e.code_commune,
    e.annee AS annee_election,
    e.bloc,
    e.pct_exprimes,
    eco.taux_pauvrete,
    eco.tx_chomage_dec,
    eco.part_ouvriers_employes
FROM v_scores_commune_pres e
LEFT JOIN v_economie_commune eco
    ON e.code_commune = eco.code_commune
    AND eco.annee = e.annee - 1;  -- données éco de l'année précédant l'élection

-- Vue 3 : évolution temporelle HdF agrégée
CREATE VIEW v_evolution_economie_hdf AS
SELECT
    f.annee,
    AVG(f.taux_pauvrete)        AS taux_pauvrete_moyen,
    MEDIAN(f.niveau_vie_median) AS niveau_vie_median_hdf,
    AVG(r.tx_chomage_dec)       AS tx_chomage_moyen
FROM economie_filosofi f
LEFT JOIN economie_rp r
    ON f.code_commune = r.code_commune
    AND f.annee = r.annee_millesime
GROUP BY f.annee
ORDER BY f.annee;
```

### D5 — Angle éditorial

**Décision** : 4 questions éditoriales structurent l'UI du module Économie.

1. "Les communes qui votent le plus RN sont-elles celles avec le taux de
   chômage le plus élevé ?"
2. "La désindustrialisation (perte emploi industriel 2000-2020) prédit-elle
   le vote extrême droite ?"
3. "La part d'ouvriers/employés détermine-t-elle la couleur politique
   des communes ?"
4. "Les communes les plus pauvres s'abstiennent-elles ou votent-elles
   contestataire ?"

### D6 — Pièges techniques (règles obligatoires pour tous les scripts ETL)

**Décision** : Ces règles s'appliquent à TOUS les scripts ETL du module Économie.

- `code_commune` toujours en `VARCHAR(5)`, jamais casté en `INTEGER`
- `nullstr=['s', 'nd']` obligatoire dans tout `read_csv`/`read_parquet` INSEE
- Filtre HdF pushdown AVANT chargement mémoire :
  `WHERE LEFT(code_commune, 2) IN ('02', '59', '60', '62', '80')`
- Encodage CSV : vérifier empiriquement (ne pas supposer UTF-8 — certains
  millésimes Filosofi/RP sont en latin-1)
- Sirene : filtrer IMPÉRATIVEMENT avant chargement (fichier national >2 Go)
- COG annuel : documenter le millésime de chaque table chargée dans les
  commentaires du loader ; les fusions de communes affectent les séries longues

## Alternatives considérées

| Alternative | Raison d'écarter |
|---|---|
| **Structure longue (indicateur/valeur)** | Incohérente avec les tables électorales existantes ; requêtes de croisement plus complexes ; pas de gain en nombre de colonnes avec 5 indicateurs |
| **Table unique fusionnant Filosofi + RP** | Millésimes différents (Filosofi annuel, RP millésimes 5 ans) ; logiques de chargement distinctes ; maintenabilité réduite |
| **Intégration France Travail** | Seuil 5 000 hab. incompatible avec la granularité communale cible pour HdF (majorité de communes sous ce seuil) |
| **Taux de chômage BIT (zone d'emploi)** | Granularité insuffisante — zone d'emploi ne permet pas le croisement commune par commune avec les élections |
| **PIB communal** | Inexistant en open data officiel ; les données privées modélisées ne sont pas sourçables |

## Conséquences

**Nouvelles tables** dans `data/ministere.duckdb` :
- `economie_filosofi` (code_commune, annee → taux_pauvrete, niveau_vie_median, d1, d9)
- `economie_rp` (code_commune, annee_millesime → tx_chomage_dec, part_ouvriers_employes, part_emploi_industriel)

**Nouvelles vues** :
- `v_economie_commune` — fusion Filosofi + RP par commune/an
- `v_croisement_eco_elections` — croisement avec `v_scores_commune_pres`
- `v_evolution_economie_hdf` — agrégation régionale temporelle

**Nouveaux fichiers** (Phase E) :
- `scripts/load_economie.py` — ETL INSEE → DuckDB
- `src/ministere_de_l_info/etl/schema_economie.py` — DDL des tables et vues
- `src/ministere_de_l_info/viz/economie_queries.py` — requêtes `@st.cache_data`
- `src/ministere_de_l_info/pages/economie.py` — module `render()`
- `pages/4_📊_Économie.py` — page Streamlit (remplace le stub actuel)
- `tests/test_economie.py` — tests d'intégration

**Décision NOT NULL** : `code_commune` et `annee`/`annee_millesime` sont `NOT NULL`
(clé primaire). Tous les indicateurs économiques acceptent `NULL` (secret statistique,
données manquantes) — jamais de valeur sentinelle (0, -1) à la place d'un `NULL`.
