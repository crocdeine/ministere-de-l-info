# Audit optimisation performance — 2026-08-19

Périmètre : lecture de code uniquement (Read/Grep/Glob), aucune exécution, aucune modification.
Fichiers couverts : `src/ministere_de_l_info/viz/*.py`, `src/ministere_de_l_info/pages/*.py`,
`pages/*.py` (racine), `src/ministere_de_l_info/etl/schema*.py`, `docker-compose*.yml`.

---

## 1. Géographie

**Bon pattern** — `pages/1_📍_Géographie.py:83` (`_get_con()`) est la seule connexion DuckDB
de tout le repo correctement déclarée en `@st.cache_resource`. Une seule connexion partagée,
réutilisée à chaque rerun Streamlit. C'est le modèle à généraliser (voir §6).

**Géométries** — bien géré. `etl/loaders/{regions,departements,epci,communes,
arrondissements_municipaux,circonscriptions}.py` pré-calculent `ST_Simplify()` en base à
plusieurs tolérances (national 0.01/0.005, régional/départemental 0.001-0.005, communal/EPCI/
circo 0.0005) dans des colonnes dédiées (`geometry_simplified_national`,
`_regional`, `_departemental`, `_epci`, `_communal`, `_circo`). `viz/_config.py` +
`viz/_queries.py::_get_geometry_column()` sélectionnent dynamiquement la bonne colonne selon
le zoom (national vs filtré). `viz/maps.py:69-73` interdit explicitement `niveau='commune'`
sans `filtre_departement` (~35 000 communes saturent le navigateur) — garde-fou correct et
documenté dans le message d'erreur lui-même.

**Requêtes inline non cachées** — `pages/1_📍_Géographie.py` exécute plusieurs `con.execute()`
directement dans le corps de page (liste des années dispo l.111-116, liste des départements
l.152-154, liste des régions l.175-177, tableau de données l.265-315) sans `@st.cache_data`.
Impact limité car la connexion est déjà partagée et ce sont des requêtes courtes
(`SELECT DISTINCT`, jointures avec `LIMIT 200`), mais elles se ré-exécutent à **chaque**
interaction sidebar (changement de niveau, dépt, année…). Quick win à faible enjeu : wrapper
les 3 listes de sélecteurs (années, départements, régions — invariantes tant que l'ETL ne
tourne pas) dans des fonctions `@st.cache_data(ttl=3600)`.

---

## 2. Élections

**Connexion DuckDB — pas de `@st.cache_resource`.** `viz/elections_queries.py:20-23` définit
`_open_ro()` qui fait `duckdb.connect(str(DB_PATH), read_only=True)` + `LOAD spatial` à
**chaque appel**, à l'intérieur même des fonctions décorées `@st.cache_data`. Le cache Streamlit
mémorise le résultat (DataFrame), mais le corps de la fonction — donc l'ouverture de connexion —
s'exécute à chaque cache miss (nouveau couple de paramètres, ou expiration du TTL). Concrètement :
- `is_data_loaded()` (ttl=60) rouvre une connexion + recharge l'extension spatiale toutes les
  60 secondes tant que la page reste ouverte.
- Chaque nouvelle combinaison `(annee, tour, zone|code_commune)` sélectionnée par l'utilisateur
  (présidentielles, législatives circo par circo, municipales commune par commune) déclenche une
  connexion DuckDB neuve.

`viz/elections_legi_queries.py` et `viz/elections_muni_queries.py` importent et réutilisent le
même `_open_ro()` (`from ministere_de_l_info.viz.elections_queries import DB_PATH, _open_ro`),
donc le problème est partagé par les 3 modules électoraux (30 scrutins, drill-down BV).

**Conversion résultat → Polars par boucle Python manuelle.** Systématique dans
`elections_queries.py`, `elections_legi_queries.py`, `elections_muni_queries.py` : chaque fonction
fait `con.execute(sql).fetchall()` puis reconstruit un `pl.DataFrame` colonne par colonne avec des
compréhensions Python (`[float(r[i]) if r[i] is not None else None for r in rows]`). DuckDB expose
nativement `.pl()` sur le résultat d'une requête (conversion via Arrow, quasi zero-copy, pas de
boucle Python élément par élément). Sur les tables fines (résultats BV, ~600 BV/commune ×
plusieurs milliers de communes cumulées sur 30 scrutins), le coût de cette boucle Python de
cast/None-handling est mesurable comparé à `.pl()`.

**BV et géométries correctement scopés.** Bon point : `get_bv_details_pres/legi`,
`get_metrics_commune_*` filtrent toujours sur `code_commune = ?` — jamais de scan BV national.
`get_communes_geo(zone='hdf')` se limite à `code_region = '32'` (~3 800 communes HdF), cohérent
avec la contrainte HdF documentée. Pas de risque de payload Folium démesuré ici.

**Vues empilées (view-on-view) non matérialisées** — `etl/schema_elections.py:795-799`
(`v_scores_circo21_pres AS SELECT * FROM v_scores_commune_pres WHERE ...`) empile une vue sur une
autre. DuckDB inline les vues au moment de la planification (pas d'exécution répétée séparée comme
sur un moteur OLTP à vues matérialisées), donc l'impact réel est faible — à surveiller seulement si
de nouvelles vues s'empilent encore davantage.

---

## 3. Législatif

**Même pattern de connexion non partagée** — `viz/legislatif_queries.py:40-41` redéfinit son
propre `_open_ro()` (dupliqué, pas importé des modules élections). Mêmes conséquences que le §2 :
connexion DuckDB neuve à chaque cache miss, y compris `is_data_loaded()` toutes les 60s.

**Boucle `fetchall()` + reconstruction Polars manuelle** — même pattern que les modules élections,
sur 10 fonctions (`get_elus_actuels`, `get_composition_politique`, `get_activite_elu`,
`get_classement_activite`, `get_activite_par_bloc`, etc.). Volumétrie modérée (4 065 élus, pas de
BV), donc impact réel plus faible qu'en Élections/Économie — à traiter en accompagnement du
refactor commun plutôt qu'en priorité isolée.

**Bon point** — filtres département (`_dept_clause()`) et indicateur d'activité
(`_INDICATEURS_ACTIVITE_VALIDES`) systématiquement paramétrés/validés côté serveur (pas
d'injection SQL via f-string non contrôlé), requêtes agrégées en SQL (`GROUP BY`, `AVG`, `COUNT`)
plutôt qu'en Python — pas de N+1 identifié dans ce module.

---

## 4. Économie

**Même absence de `@st.cache_resource`** — `viz/economie_queries.py:50-53` a son propre
`_open_ro()` dupliqué une 3e fois (copié-collé quasi identique à celui d'`elections_queries.py`).

**`LIKE '%Industrie%'` répété sur une table à ~1.15M lignes.** `get_desindustrialisation_commune()`
(l.446-471) et `get_communes_industrie_hdf()` (l.516-527) filtrent directement
`economie_emploi_urssaf` avec `WHERE secteur_gs LIKE '%Industrie%'` — un wildcard en tête de motif
empêche toute utilisation d'égalité/index, DuckDB doit évaluer le pattern sur chaque ligne de la
colonne. La vue `v_desindustrialisation_commune` (`schema_economie.py:209-210`) applique déjà
exactement le même filtre `LIKE '%Industrie%'` — les deux fonctions Python dupliquent la logique
au lieu de s'appuyer sur cette vue, avec un double risque : divergence future du filtre si la vue
évolue, et re-scan du filtre string à chaque appel plutôt qu'une seule fois en vue. Piste : ajouter
une colonne booléenne `is_industrie` calculée une fois à l'ETL (`etl/loaders/economie_urssaf.py`),
utilisée ensuite par la vue et par les deux fonctions de requête.

**Boucle `fetchall()` + reconstruction Polars manuelle** — même pattern que §2/§3, sur 13 fonctions.
Ici l'enjeu est plus net : `get_croisement_eco_elections()` et `get_desindustrialisation_commune()`
peuvent remonter plusieurs milliers de lignes (communes HdF × années URSSAF 2006-2025), avec cast
Python ligne par ligne à chaque cache miss.

**Bon point** — les conversions `pl.DataFrame → .to_pandas()` dans `pages/economie.py` (et de même
dans `pages/legislatif.py`, `pages/elections_*.py`) n'interviennent qu'à l'étape finale d'affichage
(`st.dataframe`, `.style.format()`, Plotly), sur des données déjà agrégées et petites. Ce n'est pas
une perte de l'avantage colonnaire de Polars — c'est le bon endroit pour un tel passage,
Plotly/`st.dataframe.style` exigeant du pandas. Pas un problème.

---

## 5. Folium / cartes

Aucune carte identifiée qui charge l'intégralité des ~35 000 communes ou l'ensemble des bureaux
de vote sans filtrage préalable :
- `maps.py` interdit `niveau='commune'` sans département (garde-fou explicite, §1).
- Les cartes électorales (`maps_elections.py`) consomment des `pl.DataFrame` déjà filtrés en
  amont par les fonctions `viz/elections*_queries.py` (HdF ~3 800 communes, ou circo/commune
  unique pour le drill-down BV) — pas de sur-fetch avant construction du GeoJSON.
- Les boucles Python dans `maps_elections.py` (`dominant_map`, `top3`) trient deux fois le même
  `scores_df` (`sort("voix", descending=True)` appelé deux fois, l.53 et l.60, puis l.129/l.135)
  pour calculer respectivement le bloc dominant et le top 3 — c'est redondant (un seul tri suffirait
  pour dériver les deux), mais le volume concerné (scores par commune HdF, quelques milliers de
  lignes) rend le surcoût négligeable. Mentionné pour mémoire, pas prioritaire.

---

## 6. Docker / ressources

- `docker-compose.prod.yml:32-37` : limite mémoire 2 Go (reservation 512 Mo), **aucune limite
  CPU**. Avec DuckDB + spatial + Streamlit + plusieurs `@st.cache_data` en mémoire (TTL jusqu'à
  24h sur certaines géométries/bounds), 2 Go est correct pour un usage mono-utilisateur mais reste
  à surveiller si plusieurs onglets/niveaux de cache s'accumulent en session longue (pas de moyen
  de le vérifier sans exécution — à mesurer en usage réel).
- `deploy/docker-compose.yml` (utilisé par `install.sh`, donc la configuration réellement
  déployée chez l'utilisateur final) — **aucune limite de ressources du tout** (ni mémoire ni
  CPU). Incohérent avec `docker-compose.prod.yml` qui, lui, en définit. À harmoniser : soit
  documenter que c'est volontaire (poste utilisateur dédié, pas de contention), soit aligner les
  deux fichiers.

---

## Synthèse transverse — quick wins vs investissements lourds

### Quick wins (faible effort, gain clair)

1. **Centraliser la connexion DuckDB en `@st.cache_resource`.** Actuellement 3 définitions
   quasi identiques de `_open_ro()` (`elections_queries.py`, `economie_queries.py`,
   `legislatif_queries.py`) qui rouvrent une connexion + `LOAD spatial` à chaque cache miss.
   Remplacer par un module partagé (ex. `viz/_connection.py`) exposant une fonction
   `@st.cache_resource def get_connection() -> duckdb.DuckDBPyConnection` réutilisée par les 5
   fichiers de requêtes, sur le modèle déjà correct de `pages/1_📍_Géographie.py::_get_con()`.
   Impact : élimine les réouvertures répétées de connexion + rechargement d'extension spatiale
   sur l'ensemble des modules Élections/Économie/Législatif (la majorité du trafic requêtes de
   l'app).

2. **`con.execute(sql, params).pl()` au lieu de `fetchall()` + reconstruction manuelle.**
   Remplace des dizaines de blocs de compréhensions Python (cast `float()`/`int()`/`None`
   ligne par ligne) par la conversion native DuckDB→Arrow→Polars. Mécanique, sans changement de
   logique métier, gain net sur les requêtes à plusieurs milliers de lignes (croisement éco ×
   élections, désindustrialisation URSSAF, résultats BV cumulés).

3. **Cacher les listes de sélecteurs de `pages/1_📍_Géographie.py`** (années dispo, départements,
   régions — l.111-184) avec `@st.cache_data(ttl=3600)` : invariantes hors ETL, actuellement
   ré-exécutées à chaque interaction sidebar.

4. **Remplacer `LIKE '%Industrie%'` par une colonne booléenne pré-calculée** dans
   `economie_emploi_urssaf` (ETL `economie_urssaf.py`), réutilisée par la vue
   `v_desindustrialisation_commune` et par `get_desindustrialisation_commune()` /
   `get_communes_industrie_hdf()` — élimine la duplication du filtre et le scan de motif sur
   1.15M lignes.

5. **Harmoniser les limites de ressources Docker** entre `docker-compose.prod.yml` (2G mémoire,
   pas de CPU) et `deploy/docker-compose.yml` (aucune limite) — décision éditoriale à trancher
   avec Mathias plutôt que technique pure.

### Investissements plus lourds (refactoring, à cadrer avant d'engager)

1. **Uniformiser les 5 modules `viz/*_queries.py`** (elections, elections_legi, elections_muni,
   economie, legislatif) sur un helper commun de requête (connexion partagée + `.pl()` +
   gestion du schéma vide) — actuellement chaque fichier réimplémente sa propre variante du même
   pattern (`_open_ro`, `try/finally con.close()`, DataFrame vide en cas de `rows` vide). Un
   helper générique `_query_pl(sql, params, empty_schema) -> pl.DataFrame` réduirait la
   duplication et rendrait le quick win n°2 systématique plutôt que module par module.

2. **Décision explicite sur le TTL des caches** (60s pour `is_data_loaded()`, 3600s pour la
   plupart des requêtes, 86400s pour les géométries/bounds) — cohérent avec la nature statique
   des données (ETL ponctuel, pas de mise à jour live), mais aucun mécanisme de purge du cache
   après un ETL manuel n'a été identifié dans le code audité. À vérifier : un ETL relancé pendant
   qu'une session Streamlit tourne peut servir des données obsolètes jusqu'à expiration du TTL
   (jusqu'à 24h pour les géométries). Sujet structurant, pas un simple fix de code.

3. **Mesure réelle mémoire/CPU en usage** — l'audit ne peut pas quantifier le coût réel des caches
   `@st.cache_data` cumulés (TTL longs, plusieurs onglets) sans exécution. Avant de statuer sur les
   limites Docker (§6), un profilage en conditions réelles (session longue, navigation entre les 4
   modules) donnerait une base chiffrée plutôt qu'une estimation.

---

## Périmètre non couvert

- Pas d'exécution de requêtes ni de mesure de temps réel (contrainte de mission : lecture de code
  uniquement).
- `etl/loaders/*.py` non audités en détail pour la performance (hors ETL, exécuté une fois, hors
  scope "requêtes répétées à chaque rerun Streamlit").
- Tests (`tests/`) non audités — l'audit porte sur le code applicatif, pas la suite de tests.
