# Architecture — ministere-de-l-info

Dernière mise à jour : 2026-10-06 (état du dépôt au commit `6d8512e` de `main`, après
l'audit du 2026-10-04, les jalons J1 à J5 et le design system v2). Chiffres de la base
mesurés le 2026-10-06 sur `data/ministere.duckdb` (base locale du Mac, lecture seule).

Cible de production retenue le 2026-10-06 : interface web emballée en application Mac
(Tauri), cœur de données conservé (`docs/orientations.md`). Ce document décrit
l'application Streamlit actuelle ; les prototypes sont sur les branches `poc/interface-web`
et `poc/tauri`, hors `main`.

## Vue d'ensemble

Ministère de l'Info est une application web locale de data-visualisation politique,
électorale et territoriale française. Elle s'adresse à un utilisateur unique sur sa
machine, sans accès concurrentiel ni besoin d'API REST publique. L'ensemble de la
persistance tient dans un fichier DuckDB unique (`data/ministere.duckdb`) alimenté
par des scripts ETL Python qui interrogent des sources officielles ou publiques.

Quatre modules de données + une page d'accueil :

| Module | Périmètre chargé | ETL | UI |
|--------|------------------|-----|----|
| Géographie | France | `scripts/etl_territoires.py` | `pages/1_📍_Géographie.py` (code dans la page) |
| Élections | Hauts-de-France ; France entière avec `--perimetre france` (vague B) | `scripts/init_elections_schema.py`, `scripts/load_elections_*.py`, `scripts/migrations/` | `pages/2_🗳️_Élections.py` → `src/.../pages/elections_*.py` |
| Législatif | France | `scripts/load_legislatif.py` | `pages/3_🏛️_Législatif.py` → `src/.../pages/legislatif.py` |
| Économie | Hauts-de-France (+ contexte régional/national Eurostat) | `scripts/load_economie.py` | `pages/4_📊_Économie.py` → `src/.../pages/economie.py` |

## Stack technique

| Composant | Technologie | Version min (`pyproject.toml`) | Rôle |
|-----------|-------------|-------------|------|
| Langage | Python | 3.12 | Typage strict, syntaxe moderne |
| Gestionnaire de paquets | uv | — | Lock file reproductible, CI rapide |
| Interface web | Streamlit | ≥ 1.57 | Pages interactives, navigation `st.navigation()` |
| Base analytique | DuckDB + spatial | ≥ 1.5.2 | SQL analytique + géométries in-process |
| Traitement tabulaire | Polars | ≥ 1.40 | Traitement colonnaire (Pandas en fallback : Folium, XLSX, TSV) |
| Cartographie | Folium · streamlit-folium | ≥ 0.20 · ≥ 0.27 | Rendu Leaflet interactif |
| Géométries (ETL) | GeoPandas | ≥ 1.1 (groupe `etl`) | Traitement des GeoJSON au chargement |
| Graphiques | Plotly Express | ≥ 6.7 | Graphiques interactifs web |
| HTTP | httpx | ≥ 0.28 | Téléchargement des sources |
| Configuration | pydantic-settings | ≥ 2.14 | Variables d'environnement typées |
| Lint / format | ruff | ≥ 0.15 | Lint + format, cible py312, longueur 100 |

Groupes de dépendances : `dev` (pytest, pytest-cov, pre-commit, ruff, requests), `etl`
(geopandas, openpyxl), `ai` (anthropic, sans usage dans le code à ce jour). Jinja2 est
déclaré mais la génération de rapports PDF (LaTeX/Tectonic) n'est pas implémentée ;
`src/ministere_de_l_info/rapports/` ne contient qu'un `.gitkeep`. Typage vérifié par
pyright 1.1.408 en mode `basic` (`[tool.pyright]` de `pyproject.toml`).

## Structure des modules

```
ministere-de-l-info/
│
├── app.py                          # Routeur : configure_logging(), set_page_config(),
│                                   #   inject_css(), puis st.navigation([5 × st.Page]).run()
├── pages/                          # Pages enregistrées par st.Page (plus de découverte automatique)
│   ├── 0_🏠_Accueil.py              # 4 tuiles st.page_link + tableau « Sources, licences et dates »
│   │                               #   + expander « Diagnostic technique »
│   ├── 1_📍_Géographie.py           # Carte choroplèthe multi-niveaux (logique dans la page)
│   ├── 2_🗳️_Élections.py            # st.tabs paresseux Présidentielles / Législatives / Municipales
│   ├── 3_🏛️_Législatif.py           # Wrapper : pages.legislatif.render()
│   └── 4_📊_Économie.py             # Wrapper : pages.economie.render()
│
├── src/ministere_de_l_info/
│   ├── config.py                   # get_settings() (pydantic-settings) : db_path, racine du projet
│   ├── sources.py                  # Registre SOURCES (producteur, licence, URL, tables) ;
│   ├── perimetre.py                # Départements des Hauts-de-France (définition unique du périmètre)
│   │                               #   mention() pour les légendes, tableau_sources() pour l'Accueil
│   ├── _sql.py                     # ligne_unique() : première ligne d'un agrégat, erreur si absente
│   ├── _theme.py                   # inject_css(), modèle Plotly « mdi », render_page_header(),
│   │                               #   render_overline(), render_donnees_indisponibles(),
│   │                               #   conserver_selections() / index_persiste() (onglets paresseux)
│   ├── _blocs_politiques.py        # BLOCS_ORDERED, COULEURS_BLOCS, LIBELLES_BLOCS (6 blocs),
│   │                               #   legende_classement_blocs(type, année) (ADR-0013)
│   ├── custom.css                  # Tokens du design system v2 (ADR-0014) + sélecteurs data-testid
│   ├── logging_config.py           # configure_logging() : LOG_LEVEL + LOG_FORMAT
│   ├── rapports/                   # Vide (.gitkeep) : rapports PDF non implémentés
│   │
│   ├── data_sources/               # Connecteurs bas niveau (géographie)
│   │   ├── geo.py                  # WFS IGN ADMIN-EXPRESS (régions, dpts, EPCI, communes…)
│   │   ├── circonscriptions.py     # data.gouv.fr — 559 circonscriptions législatives
│   │   └── insee_populations.py    # INSEE Mélodi DS_POPULATIONS_HISTORIQUES
│   │
│   ├── etl/
│   │   ├── _common.py              # open_connection(), upsert_metadata()
│   │   ├── schema.py               # Tables géographiques + _etl_metadata + _schema_version
│   │   ├── views.py                # v_population_{region,departement,epci,commune}
│   │   ├── schema_elections.py     # 6 tables électorales + 8 vues (présidentielles, législatives)
│   │   ├── schema_economie.py      # 5 tables + 6 vues Économie
│   │   ├── schema_legislatif.py    # 5 tables + 5 vues Législatif (ADR-0011)
│   │   ├── legislatif_groupes.py   # Référentiel groupe × législature → bloc (AN et Sénat,
│   │   │                           #   y compris groupes historiques du Sénat)
│   │   └── loaders/
│   │       ├── regions.py, departements.py, epci.py, communes.py,
│   │       │   arrondissements_municipaux.py, circonscriptions.py, populations.py
│   │       ├── communes_passage.py    # Communes fusionnées → commune actuelle (COG INSEE)
│   │       ├── elections_agregees.py  # Périmètre hdf/france, euro/regi/dpmt (vague B)
│   │       ├── _http_retry.py
│   │       ├── economie_filosofi.py    # Dataset OLAP data.gouv → economie_filosofi
│   │       ├── economie_rp.py          # Dataset OLAP data.gouv → economie_rp
│   │       ├── economie_cnaf.py        # CNAF RSA → economie_social
│   │       ├── economie_drees.py       # DREES APL → economie_social (upsert)
│   │       ├── economie_urssaf.py      # URSSAF → economie_emploi_urssaf
│   │       ├── economie_eurostat.py    # Eurostat SDMX → economie_contexte
│   │       ├── legislatif_senat.py     # data.senat.fr ODSEN_GENERAL → leg_elus + leg_mandats
│   │       ├── legislatif_datan.py     # Datan → leg_elus + leg_mandats + leg_activite
│   │       ├── legislatif_nuances_ni.py # Nuance préfectorale des députés non inscrits
│   │       │                           #   (Parquet élections + AMO30 de l'AN) → leg_mandats.nuance_*
│   │       └── legislatif_overrides.py # Corrections manuelles → leg_blocs_override
│   │
│   ├── pages/                      # render() appelés par les fichiers de pages/
│   │   ├── elections_presidentielles.py  # 2002-2022, zone circo 21 ou HdF, drill-down BV
│   │   ├── elections_legislatives.py     # 2002-2024, vue HdF ou circonscription, drill-down BV
│   │   ├── elections_municipales.py      # 2008-2026, bloc dominant, drill-down listes
│   │   ├── legislatif.py                 # Filtres sidebar + 4 onglets, fiche d'un député
│   │   └── economie.py                   # 4 onglets paresseux
│   │
│   └── viz/                        # Cartes et requêtes cachées
│       ├── maps.py                 # make_choropleth() + get_carte_cache() (@st.cache_resource)
│       ├── maps_elections.py       # Cartes électorales Folium
│       ├── elections_queries.py    # Requêtes présidentielles (+ DB_PATH)
│       ├── elections_legi_queries.py
│       ├── elections_muni_queries.py
│       ├── legislatif_queries.py   # 11 fonctions publiques de requêtes
│       ├── economie_queries.py     # Requêtes Économie, liste blanche d'indicateurs
│       ├── _config.py              # Constantes : tables, colonnes, géométries, filtres
│       ├── _display.py             # nouvelle_carte() (fond Plan IGN), palettes, BORNES_FIXES
│       │                           #   (classes fixes), classe « 0 », fmt_nd() (« n.d. »), légendes
│       └── _queries.py             # open_ro() (connexion lecture seule unique), builders SQL,
│                                   #   requêtes Géographie en @st.cache_data
│
├── scripts/
│   ├── etl_territoires.py          # ETL géographie + populations
│   ├── etl_regions.py              # Ancien ETL régions (toujours présent)
│   ├── init_elections_schema.py    # Schéma électoral + tables de référence
│   ├── load_communes_passage.py    # Table de passage COG (avant les loaders électoraux)
│   ├── load_elections_{presidentielles,legislatives,municipales,autres}.py  # --perimetre hdf|france
│   ├── migrations/                 # 0006 schéma municipales, 0007 vues municipales,
│   │                               #   0008 Législatif par législature, 0009 résultats sans clé primaire
│   ├── load_economie.py            # --source filosofi|rp|cnaf|urssaf|drees|social|eurostat|contexte|all
│   ├── load_legislatif.py          # --source senat|datan|nuances|overrides|all
│   ├── veille_groupes_senat.py     # Contrôle : sénateurs actifs sans groupe (lecture seule)
│   ├── export_sample_db.py         # Export de la base échantillon (Somme) pour les tests
│   ├── backup_db.sh, publish_db.sh, download_db.sh
│   └── com.crocdeine.ministere-info.backup.plist   # Modèle launchd utilisé par install-native.sh
│                                                   #   (tâche supprimée du Mac le 2026-10-06)
│
├── deploy/                         # Dockerfile de l'image GHCR, compose, install.sh, update.sh,
│                                   #   native/ (exécution native, ADR-0012), tests/ (tests shell)
├── Dockerfile, docker-compose.yml, docker-compose.prod.yml   # Build et compose locaux
├── LICENSE (MIT, code), LICENSE-DONNEES.md (ODbL, base)      # ADR-0013
├── .streamlit/config.toml          # Thème clair aligné sur le design system
├── tests/                          # Suite pytest (voir § Tests)
└── data/                           # ministere.duckdb + raw/ (caches) — non versionné
```

## Application web (ADR-0015, vague A)

Nouvelle interface, construite à côté de Streamlit (gelé) et appelée à le remplacer page par page :

```
base DuckDB (lecture seule)
  └─ scripts/export_web.py → src/ministere_de_l_info/export_web/  (agrégats SQL, tippecanoe)
       └─ web/public/data/  (non commité)
            manifest.json              contrat (schéma 2) : SHA256 des fichiers et du JSON brut, sources, licences
            communes.pmtiles           contours + état de chaque commune pour chaque tour (`s`)
            communes.json.gz           codes et noms (ordre de référence des colonnes)
            scrutins/<id>.json.gz      résultats par commune d'un tour (infobulle)
            departements/<dep>/{communes,bureaux}.json.gz   tous tours (fiche territoire, A3)
            methodologie.json.gz       registre des sources + correspondances → bloc (panneau Méthodologie, A5)
  └─ web/  Vite + React + TypeScript, MapLibre  →  web/src-tauri/  application Mac (Tauri v2)
```

- Carte : un caractère par tour dans la propriété `s` des tuiles (`a`-`f` blocs, `=` égalité,
  `n` non classé, `.` n.d., `x` aucun scrutin ; voir `docs/schema-elections.md`) ; changement de tour par un seul
  `setPaintProperty` ; fondu croisé de 220 ms entre deux couches (deux sources), supprimé si la
  recoloration dépasse 100 ms ou si `prefers-reduced-motion` (`--duration-map-fade`).
- L'interface ne calcule rien : participation et part du bloc en tête viennent de l'export.
- Méthodologie (A5) : texte source unique `docs/methodologie.md`, compilé au build
  (`web/src/markdown.ts`, sous-ensemble de Markdown, sans bibliothèque) et chargé à la demande ;
  panneau `<dialog>` ouvert par l'étiquette de méthode et les liens « Méthode » (`Legende.tsx`),
  sans quitter la page ; ancres listées dans `ANCRES` et vérifiées par `methodologie.test.ts`.
- Export publié atomiquement : écrit dans `.<sortie>.prepa/`, contrôlé (fichiers non vides,
  un fichier par tour, communes des tuiles), manifeste en dernier, puis substitué à la sortie.
- Chaque JSON lu par l'interface est vérifié contre `sha256_brut` (empreinte du JSON
  décompressé, valable même si le serveur décompresse en route) ; l'archive de tuiles lue en
  mémoire (Tauri) est vérifiée contre `sha256`.
- MapLibre est servi depuis ses fichiers ESM d'origine (`public/vendor/`, copiés par
  `vite.config.ts`) pour ne pas dupliquer son code commun dans le worker.
- Commandes : `web/README.md`.

## Navigation et thème

`app.py` est le seul script exécuté par Streamlit à chaque interaction. Il configure la
page (`page_title`, favicon Material `flag`, `layout="wide"`), injecte le CSS une fois,
puis déclare les pages :

| Page | Icône | URL |
|------|-------|-----|
| Accueil (défaut) | `:material/home:` | `/accueil` |
| Géographie | `:material/map:` | `/geographie` |
| Élections | `:material/how_to_vote:` | `/elections` |
| Législatif | `:material/account_balance:` | `/legislatif` |
| Économie | `:material/bar_chart:` | `/economie` |

Les fichiers de `pages/` n'appellent ni `set_page_config` ni `inject_css`. Les titres
sont rendus par `render_page_header()`. Filtres : sidebar pour les filtres qui
s'appliquent à toute la page (Géographie, Législatif), inline pour les sélecteurs
propres à un onglet (Élections, Économie). Les onglets d'Élections et d'Économie sont
« paresseux » (`st.tabs(..., on_change="rerun")`) : seul l'onglet ouvert est calculé, et
`conserver_selections()` garde les choix des onglets fermés. Décisions :
[ADR-0009](adr/0009-design-system-et-navigation.md) (routeur, tokens), révisé par
l'[ADR-0014](adr/0014-design-system-direction-editoriale.md) (design system v2
« direction éditoriale », skill `.claude/skills/design-system-mi`).

## Flux ETL

```
Sources                                   ETL                               DuckDB
───────                                   ───                               ──────
data.geopf.fr (WFS IGN) ─┐
data.gouv.fr (circos)   ─┼─ data_sources/* ─ etl/loaders/* ─ etl_territoires.py ─► geographies_*, populations, v_population_*
INSEE Mélodi            ─┘

data.gouv.fr (Parquet élections) ─ load_elections_*.py ─────────────────────► resultats_*, nuances_harmonisees, v_* électorales

data.gouv.fr (OLAP Filosofi + RP) ─┐
data.caf.fr (CNAF)                 ├─ loaders/economie_* ─ load_economie.py ──► economie_*, v_* économie
DREES, open.urssaf.fr, Eurostat    ─┘

data.senat.fr, Datan (data.gouv.fr)          ─┐
AN (AMO30), Parquet élections (non-inscrits) ─┴─ loaders/legislatif_* ─ load_legislatif.py ► leg_*, v_elus_actuels, v_mandats_legislatif, v_activite_par_bloc

                                           ▼
                                   ministere.duckdb ──► viz/*_queries.py (@st.cache_data) ──► pages ──► navigateur
```

Les caches bruts sont stockés sous `data/raw/` (ex. `data/raw/economie/`) ; l'option
`--force` des scripts les retélécharge.

## Schéma de la base DuckDB

### Géographie

| Table | Lignes | Clé | Géométries |
|-------|--------|-----|------------|
| `geographies_regions` | 18 | `code_insee` | `geometry`, `geometry_simplified_national`, `geometry_simplified_regional` |
| `geographies_departements` | 101 | `code_insee` | `geometry`, `geometry_simplified_national`, `geometry_simplified_departemental` |
| `geographies_epci` | 1 265 | `code_siren` | `geometry`, `geometry_simplified_epci` |
| `geographies_communes` | 34 877 | `code_insee` | `geometry`, `geometry_simplified_communal` |
| `geographies_arrondissements_municipaux` | 45 | `code_insee` | `geometry`, `geometry_simplified_communal` |
| `geographies_circonscriptions` | 559 | `code` | `geometry`, `geometry_simplified_circo` |
| `populations` | 34 858 × 3 millésimes | `(code_insee_commune, annee)` | — |

Millésimes de population : 2013, 2018, 2023. Colonne fiable : `population_municipale`
(`comptee_a_part` et `totale` NULL). Vues : `v_population_region`,
`v_population_departement`, `v_population_epci`, `v_population_commune`.

Tables méta : `_etl_metadata` (horodatage, version de source, `row_count` par table),
`_schema_version`.

### Élections

Détail complet : [schema-elections.md](schema-elections.md). Tables `elections`,
`resultats_participation`, `resultats_candidats`, `blocs_politiques`,
`nuances_harmonisees`, `candidats_presidentielle`. Onze vues : 8 créées par
`schema_elections.py` (`v_resultats_candidats_avec_bloc`, `v_scores_circo21_pres`,
`v_evolution_blocs_circo21`, `v_scores_commune_pres`, `v_participation_commune_pres`,
`v_scores_circo_legi`, `v_participation_circo_legi`, `v_evolution_blocs_hdf_legi`) et 3
par la migration `0007` (`v_scores_commune_muni`, `v_evolution_blocs_hdf_muni`,
`v_listes_commune_muni`). Volumes mesurés le 2026-10-06 : 56 scrutins au référentiel
`elections`, dont 30 avec des résultats chargés (10 présidentielles, 12 législatives,
8 municipales) ; 162 469 lignes de participation, 1 093 836 lignes candidats,
229 correspondances `(nuance, année) → bloc` (117 codes distincts), 23 candidats
présidentiels 2017/2022.

### Économie

Définie dans `etl/schema_economie.py` (ADR-0006 et ADR-0008). Filtre HdF au chargement.

| Table | Clé | Contenu | Lignes (mesure du 2026-10-06) |
|-------|-----|---------|--------|
| `economie_filosofi` | `(code_commune, annee)` | Taux de pauvreté, niveau de vie médian, D1, D9, `secret` | 17 582 (2017-2021) |
| `economie_rp` | `(code_commune, annee_millesime)` | Chômage déclaratif, part ouvriers/employés, part emploi industriel, logements sociaux, `pop_active`, `secret` | 26 538 (2015-2021) |
| `economie_social` | `(code_commune, annee)` | Foyers RSA, taux RSA, APL médecins, `desert_medical` | 17 696 lignes : RSA 17 381 (2020-2024) ; APL 3 788 (2023), dont 943 `desert_medical` |
| `economie_emploi_urssaf` | `(code_commune, annee, code_ape)` | Salariés et établissements par grand secteur et APE | 1 157 338 (2006-2025) |
| `economie_contexte` | `(code_geo, annee, indicateur)` | Chômage BIT (1999-2025), PIB/hab (2000-2024), `FRE` et `FR` | 104 |

Vues : `v_economie_commune`, `v_croisement_eco_elections` (économie de l'année n-1 ×
présidentielles), `v_evolution_economie_hdf`, `v_economie_sociale_commune`,
`v_desindustrialisation_commune`, `v_contexte_hdf_vs_france`.

### Législatif

Défini dans `etl/schema_legislatif.py` (ADR-0007, ADR-0011). Chargé pour la France entière.
Classement des groupes : référentiel `etl/legislatif_groupes.py` → `leg_groupes_blocs`.

| Table | Clé | Contenu | Lignes (mesure du 2026-10-06) |
|-------|-----|---------|--------|
| `leg_elus` | `(id, chambre)` | Identité, département, groupe, `bloc_politique`, `est_actif`, profession, source | 3 323 (2 120 AN + 1 203 Sénat) ; 925 actifs (577 AN + 348 Sénat) |
| `leg_activite` | `(elu_id, chambre, date_extraction)` | Compteurs et scores Datan (AN uniquement) | 1 653 |
| `leg_blocs_override` | `(elu_id, chambre)` | Bloc forcé + justification | 2 |
| `leg_mandats` | logique `(elu_id, chambre, legislature, groupe_sigle, date_debut)` | Mandat × groupe ; `granularite` (`derniere_legislature` Datan, `groupe_actuel_ou_dernier` Sénat) | 3 323 (1 par élu) ; nuance préfectorale renseignée pour 96 des 100 mandats AN non inscrits |
| `leg_groupes_blocs` | `(chambre, groupe, [legislature_debut, legislature_fin])` | Groupe × période → bloc + `source_bloc` | 56 |

Vues : `v_elus_actuels` (élus actifs France entière, `bloc_final` = override sinon bloc du
groupe pour la législature ; `v_elus_hdf_actuels` en est un alias déprécié),
`v_mandats_legislatif`, `v_composition_legislature`, `v_activite_par_bloc`. Groupe non
classé : `bloc_final` NULL (« Non classé » en UI), jamais DIV. Député non inscrit : bloc
de la nuance préfectorale de son élection (ou de celle de son titulaire s'il est
remplaçant), convertie par `nuances_harmonisees` ; DIV si la nuance n'est pas publiée
(élections partielles). Colonnes `leg_mandats.nuance_election`, `nuance_annee`,
`nuance_source`. `date_naissance` a été supprimée de `leg_elus` le 2026-10-04 (ADR-0013).

Écart avec les rapports antérieurs : la Phase F annonçait 4 065 élus (1 945 sénateurs).
Depuis l'addendum de l'ADR-0011 (2026-09-25), les anciens sénateurs dont le dernier
groupe a disparu avant 2002 sont écartés au chargement ; la base du 2026-10-06 compte
1 203 sénateurs.

### Anomalies connues

- **Mayotte** : absente de `v_population_*` (source INSEE séparée).
- **Saint-Pierre-et-Miquelon** : 2 communes avec `code_departement = 'NR'`.
- **Grand Paris** : 135 communes avec `code_epci` multi-valeur ; 11 EPT sans `code_departement_principal`.
- **Municipales 2008** : Nord quasi absent du fichier source (2 communes).
- **Législatif** : `region_nom` NULL pour les 2 120 députés ; les sénateurs des circonscriptions
  historiques (code `XX`) sont écartés au chargement (aucun dans la base du 2026-10-06).

## Patterns transverses

### Accès à la base depuis l'UI

- Connexions DuckDB en lecture seule, ouvertes par une fonction unique
  `viz/_queries.open_ro(db_path, spatial=...)` puis fermées par l'appelant. Chaque
  fonction de requête met son résultat en `@st.cache_data` (TTL de 3 600 s le plus
  souvent). Plus aucune connexion permanente : Géographie n'utilise plus de connexion
  `@st.cache_resource` depuis J4 (2026-10-06), ce qui bloquait les rechargements ETL.
  Seule la carte Folium de Géographie est partagée en `@st.cache_resource`
  (`viz/maps.get_carte_cache`, 32 entrées).
- Valeur absente : affichée « n.d. » (`_display.fmt_nd`, `na_rep="n.d."`), jamais 0 ;
  sur les cartes, case grise « n.d. » dans la légende.
- Cartes : fond Plan IGN atténué (`_display.nouvelle_carte`), classes fixes par
  indicateur (`BORNES_FIXES`), identiques pour toutes les années ; classe « 0 » distincte
  pour les logements sociaux, l'emploi industriel et le RSA ; score d'un bloc sur une
  échelle fixe de 0 à 100 % ; évolution démographique en palette orange-violet (sans
  rouge-vert, lisible par les daltoniens). Décisions : `docs/orientations.md` (J3).
- Mentions de sources : `sources.mention(cle)` dans les légendes ; légende de l'origine
  du classement des blocs par scrutin : `_blocs_politiques.legende_classement_blocs()`.
- Paramètres SQL passés par `?` ; les noms de colonnes dynamiques sont validés contre
  une liste blanche (`frozenset`) avant interpolation (Économie, Législatif).
- Chaque page vérifie la présence des données et affiche la commande ETL à lancer si
  elles manquent.

### Logging

Centralisé dans `logging_config.configure_logging()`, appelé par `app.py` et par
chaque script ETL.

| Variable | Valeurs | Défaut |
|----------|---------|--------|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `LOG_FORMAT` | `text`, `json` | `text` |

Chaque module déclare `logger = logging.getLogger(__name__)`.

### Configuration

Les secrets et paramètres d'environnement sont lus depuis `.env` (gitignored) ;
`.env.example` documente les variables attendues. Aucune clé API n'est hardcodée.

`ministere_de_l_info.config` (pydantic-settings) centralise les paramètres :
`get_settings().db_path` donne le chemin de la base, lu depuis `MINISTERE_DB_PATH`
(environnement puis `.env`), par défaut `<racine du projet>/data/ministere.duckdb`.
La racine est trouvée en remontant jusqu'au `pyproject.toml` du projet (pas de
dépendance à une installation éditable). ETL, requêtes, pages et scripts l'utilisent.

### Tests

- Framework : `pytest` + `pytest-cov`, seuil `--cov-fail-under=60` dans `pyproject.toml`
  (relevé de 38 à 60 % le 2026-10-06, jalon J4).
- 694 tests collectés le 2026-10-06, dont 13 marqués `slow` (Streamlit headless et
  AppTest) et 16 marqués `network`, exclus par défaut : `uv run pytest` en sélectionne
  665 ; `uv run pytest -m slow` lance les tests `slow`. 14 tests portent le marqueur
  `spatial`.
- Les tests d'intégration ouvrent `data/ministere.duckdb` en lecture seule et sont
  ignorés (`pytest.skip`) si la base est absente — c'est le cas en CI.
- Les tests qui appellent des API réelles (IGN, INSEE Mélodi, data.gouv.fr) portent le
  marqueur `network` et sont exclus par défaut (`-m "not slow and not network"`) ;
  `uv run pytest -m network --no-cov` les lance.
- Les tests qui exigent l'extension DuckDB `spatial` portent le marqueur `spatial` et
  sont ignorés proprement si elle n'est pas installée (`tests/conftest.py`).
- Base échantillon : `scripts/export_sample_db.py` (sur le Mac) exporte la Somme (80)
  en Parquet dans `tests/fixtures/sample/` (versionné) ; `tests/fixtures/sample_db.py`
  reconstruit une base avec les fonctions de schéma du projet (fixtures `echantillon_con`,
  `echantillon_db_path`). Sans Parquet, les tests concernés sont ignorés.
- Exclus de la couverture (`[tool.coverage.run] omit`) : loaders ETL, `schema.py`,
  `schema_economie.py`, `schema_legislatif.py`, `views.py`, `_common.py`, les modules
  de pages Élections/Économie/Législatif et `elections_muni_queries.py`,
  `economie_queries.py`, `legislatif_queries.py`.
- Couverture sans base (conditions de la CI) : 66,23 % mesurés le 2026-10-06 dans un
  worktree sans `data/` (302 réussis, 363 ignorés, 29 désélectionnés) ; le commentaire de
  `pyproject.toml` indique 64,2 % en CI. Avec la base locale : 77,95 % (652 tests,
  journal du 2026-10-06, J4), valeur non remesurée ici.

| Fichier | Périmètre |
|---------|-----------|
| `test_etl_territoires.py`, `test_etl_smoke.py`, `test_etl_regions.py`, `test_fetch_admin_express.py` | ETL géographie, intégrité de la base |
| `test_insee_populations.py`, `test_circonscriptions.py` | Connecteurs INSEE et circonscriptions |
| `test_viz_maps.py`, `test_pages_geographie.py`, `test_cache_geographie.py` | Carte Géographie et cache des requêtes |
| `test_elections_*.py`, `test_pages_legislatives.py`, `test_pages_municipales.py` | Données, vues, requêtes et classements électoraux (dont ADR-0010) |
| `test_economie.py`, `test_economie_rp_memoire.py` | Module Économie |
| `test_legislatif.py`, `test_legislatif_memoire.py`, `test_legislatif_nuances_ni.py`, `test_veille_senat.py` | Module Législatif, non-inscrits, veille Sénat |
| `test_conformite.py` | Licences, registre des sources, absence de `date_naissance` |
| `test_valeurs_manquantes.py`, `test_lisibilite_j3.py`, `test_theme.py`, `test_ui_fixes_2026_09_25.py`, `test_ui_quick_wins.py` | Affichage « n.d. », classes fixes, thème, correctifs d'interface |
| `test_streamlit_smoke.py` | Démarrage de `app.py` (santé HTTP) + AppTest sur la page Élections (`slow`) |
| `test_config.py`, `test_sample_db.py` | Configuration centralisée, base échantillon et son export |

Tests shell de l'infrastructure : `deploy/tests/` (`test_native.sh`, `test_backup_db.sh`,
`test_db_checksum.sh`), lancés à la main (55/55 réussis selon le journal du 2026-10-06).

### CI (GitHub Actions)

`ci.yml` — déclenché sur push vers `main` et `claude/**` et sur pull request vers
`main` ; un seul run actif par ref (`concurrency`, annulation du précédent) :

| Job | Étapes |
|-----|--------|
| **Lint & Format** | `ruff check .` + `ruff format --check .` |
| **Tests & Coverage** | `uv sync --frozen --group etl`, extension `spatial` installée (cache `~/.duckdb/extensions`), `pytest` (seuil de couverture 60 %, bloquant) avec rapport de couverture en artefact |
| **Typage (pyright basic)** | `uvx pyright@1.1.408` en mode `basic`, bloquant (0 erreur depuis le 2026-10-06) |
| **Application web** | tippecanoe compilé (mis en cache), export de l'échantillon, `npm ci`, `tsc --noEmit`, `vitest run`, `vite build`, budget du JS initial (`perf/budget.mjs`, < 450 Ko gzip, bloquant), `npm audit --audit-level=high`, test de fumée et mesures WebKit (`perf/mesure.mjs`, temps indicatifs ; avec et sans mouvement réduit) |

Les actions GitHub sont épinglées par SHA de commit ; permissions du workflow limitées à
`contents: read`.

`docker-publish.yml` — construit et publie l'image multi-architecture sur GHCR à chaque
tag `v*` (ou à la demande, `workflow_dispatch`), à partir de `deploy/Dockerfile`. Les
releases de base utilisent des tags `db-AAAA-MM-JJ`, hors `v*`, qui ne déclenchent pas
ce workflow.

### Pre-commit

Hooks : `gitleaks` (détection de secrets), `ruff` (`--fix`), `ruff-format`,
`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`,
`check-merge-conflict`, `detect-private-key`, `check-added-large-files` (1 000 Ko ;
PDF et Parquet de `tests/fixtures/sample/` exclus). Le dossier `.claude/` est exclu des
hooks de formatage.

## Décisions structurantes

| ADR | Décision |
|-----|----------|
| [0001](adr/0001-duckdb-vs-postgres.md) | DuckDB plutôt que PostgreSQL |
| [0002](adr/0002-streamlit-vs-fastapi.md) | Streamlit plutôt que FastAPI + frontend JS |
| [0003](adr/0003-uv-vs-pip-poetry.md) | uv plutôt que pip / poetry |
| [0004](adr/0004-polars-vs-pandas.md) | Polars prioritaire, Pandas en fallback |
| [0005](adr/0005-nuances-et-blocs-officiels.md) | Nomenclature officielle Ministère — 6 blocs de clivages |
| [0006](adr/0006-module-economie-sources-et-schema.md) | Module Économie — sources, indicateurs, schéma |
| [0007](adr/0007-module-legislatif-perimetre-et-sources.md) | Module Législatif — périmètre national, Datan + data.senat.fr |
| [0008](adr/0008-economie-sources-complementaires.md) | Économie — sources complémentaires CNAF, DREES, URSSAF, Eurostat |
| [0009](adr/0009-design-system-et-navigation.md) | Design system et navigation `st.navigation()` |
| [0010](adr/0010-revision-nuances-et-blocs.md) | Révision des classements nuances → blocs (grilles 2020, 2023, 2026) |
| [0011](adr/0011-legislatif-groupes-par-legislature.md) | Législatif — classement des groupes par législature, mandats |
| [0012](adr/0012-execution-native-mac.md) | Exécution native sur le Mac (uv + LaunchAgent), Docker en repli |
| [0013](adr/0013-licences-et-mentions-des-sources.md) | Licences (code MIT, base ODbL) et mentions des sources |
| [0014](adr/0014-design-system-direction-editoriale.md) | Design system v2 « direction éditoriale » (révise 0009) |

Index et statuts : [adr/README.md](adr/README.md).

## Déploiement

L'app est distribuée sous forme d'image Docker publiée sur GitHub Container Registry
(`ghcr.io/crocdeine/ministere-de-l-info`), construite par `docker-publish.yml` à partir
de `deploy/Dockerfile` à chaque tag `v*`, multi-architecture (arm64 + amd64).
La base est distribuée séparément, en asset de release GitHub (`ministere.duckdb.gz`
+ `.sha256`, empreinte obligatoire au téléchargement). Dernière release applicative :
`v0.5-economie-legislatif` (2026-06-28) ; dernière release de base : `db-2026-10-04`
(ODbL, sans dates de naissance). Les deux sont antérieures au design system v2.

Mode d'exécution sur le Mac (orientations du 2026-10-06) : l'exécution native
(`deploy/native/`, ADR-0012) est la cible recommandée, mais son installation est
reportée ; Docker est conservé pour une éventuelle distribution, sans maintenance
active. Ports publiés sur `127.0.0.1` uniquement.

Deux Dockerfiles coexistent : `Dockerfile` à la racine (compose local dev/prod) et
`deploy/Dockerfile` (image publiée) ; ils ne sont pas identiques. Tous deux figent
l'image Python par digest et uv en version 0.11.16.

Installation Docker pour un tiers (macOS 13+, OrbStack) :
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/main/deploy/install.sh)
```

Guides : `deploy/README-deploy.md` (mainteneur, installation, mise à jour) et
[deployment.md](deployment.md) (natif, Docker, sauvegardes, dépannage).

## Pour aller plus loin

- [data-sources.md](data-sources.md) — sources de données (URLs, formats, limitations)
- [sources.md](sources.md) — licences et mentions obligatoires
- [guide-utilisateur.md](guide-utilisateur.md) — utilisation de l'application
- [lessons-learned.md](lessons-learned.md) — leçons techniques
- [README.md](../README.md) — installation, premier lancement
