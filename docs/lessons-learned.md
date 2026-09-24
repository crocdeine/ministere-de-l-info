# Leçons techniques — ministere-de-l-info

Consolidation des gotchas et leçons tirées de chaque phase. Mise à jour à chaque clôture de phase.

Dernière mise à jour : 2026-09-24 — consolidation des phases D (élections complètes),
E / E+ / E++ (Économie), F (Législatif) et du chantier design system, à partir des
rapports de `reports/` et du code. Les sections ajoutées indiquent leur phase d'origine.

---

## Données

### Sources IGN (WFS)

- Les coupures HTTP chunked sur les grandes collections (communes, ~35 000 entités) sont aléatoires. Le loader doit implémenter des retries + reprise depuis le cache disque (`data/raw/`).
- Les codes `codes_siren_des_epci` pour les 135 communes du Grand Paris sont multi-valeurs dans le WFS — parser le premier SIREN suffit pour la majorité des usages.
- Saint-Pierre-et-Miquelon retourne `code_departement = 'NR'` (COM hors ADMIN-EXPRESS) — à filtrer ou traiter à part.

### Sources INSEE

- L'API Mélodi (`DS_POPULATIONS_HISTORIQUES`) ne fournit pas `comptee_a_part` ni `totale` (PCAP absent). Stocker NULL est correct — ne pas chercher une autre source pour ces deux colonnes.
- Mayotte est absente de la source principale (données publiées séparément par l'INSEE).
- Les CSV INSEE sont encodés latin-1 avec séparateur `;` — toujours préciser à l'import.

### Données électorales Parquet (data.gouv.fr / Ministère de l'Intérieur)

- **Nommage inversé** : `general-results.parquet` = résultats candidats ; `candidats-results.parquet` = participation. Le nom des fichiers est trompeur — utiliser les noms de tables DuckDB comme référence.
- **Nuances NULL** : colonne `nuance` absente pour présidentielles 2017/2022 et européennes 2019. Pour les présidentielles, résoudre via table `candidats_presidentielle` (jointure sur `nom`). Pour les européennes 2019, à traiter en Phase D selon le besoin.
- **Codes nuances présidentielles 2002/2007/2012** : les nuances sont des abréviations de nom de candidat (`CHIR`, `JOSP`, `SARK`), pas des codes partisans comme dans les autres scrutins. La table `nuances_harmonisees` gère les deux conventions via la clé `(nuance, annee)`.
- **Évolution des nuances dans le temps** : `DVG` en 2002 ≠ `DVG` en 2022. Ne jamais joindre sur `nuance` seul sans filtrer sur `annee`.
- **Blocs officiels depuis 2023 seulement** : le regroupement officiel en 6 blocs de clivages n'existe que depuis la circulaire IOMA2322276J (sénatoriales 2023). Pour les scrutins antérieurs, reconstruction rétroactive selon la logique officielle datée — voir ADR-0005.
- **Classement "de l'époque"** : un parti est classé selon le bloc qui lui était attribué à la date du scrutin. Ne jamais appliquer une grille rétroactivement (ex. : LFI = GAU en 2017/2022, pas EXG — ce basculement n'arrive qu'en 2026 avec INTP2602966C).

### Géographie électorale

- **Codes INSEE de circonscriptions trouvés sur le web sont peu fiables** : les listes de communes par circonscription circulent sur Wikipédia et des sites tiers mais contiennent souvent des erreurs (communes déplacées lors de fusions, redécoupages non répercutés). Toujours valider par jointure spatiale `ST_Within` sur la table `geographies_circonscriptions`.
- **Format `id_election`** : `{YYYY}_{type}_t{N}` (ex. `2022_pres_t1`). Cohérent dans toutes les tables et vues du module électoral.

### Codes INSEE

- Code INSEE ≠ code postal. Paris commune = `75056` ; les arrondissements = `75101` à `75120`.
- Le zéro-padding est obligatoire : `"01001"` et non `1001`. Un stockage INTEGER fait silencieusement tomber les communes des départements 01-09.

### Législatives et municipales (Phase D)

- **`code_circonscription` est dans le fichier de participation**, pas dans celui des
  candidats : la circonscription d'un candidat s'obtient par jointure sur
  `(id_election, code_departement, code_commune, code_bv)`.
- **`code_circonscription` est un numéro relatif au département** (`"05"`) : reconstruire
  l'identifiant `dpt-NN` (`'59-05'`) pour joindre `geographies_circonscriptions`.
- **`code_circonscription` NULL pour 2002, 2007 et 2024** dans le Parquet : le code est
  reconstruit au chargement ; 2002/2007 relèvent de l'ancien découpage (13 communes
  coupées entre deux circonscriptions, documentées dans l'ADR-0005).
- **Vérifier une lacune dans le fichier brut avant de suspecter le code** : pour les
  municipales 2008, le Nord ne compte que 2 communes (Lille absente) ; confirmé par
  requête directe sur le Parquet sans filtre, puis documenté (ADR-0005, avertissement UI).
- **`no_panneau` NULL en 2008** : synthétisé par `ROW_NUMBER()` pour respecter la clé ; ce
  n'est pas un identifiant stable de liste.
- **Seuils de nuançage municipaux** : seules les listes des communes de 3 500 habitants et
  plus sont nuancées ; les codes `NC`, `LMAJ`, `LNC` ne sont pas rattachés à un bloc
  (communes « Non classé » dans l'UI).
- **Documenter l'absence de source** : les circulaires de nuançage des législatives
  2002-2017 ne sont pas publiées au JO ; le classement est reconstruit et tracé colonne
  `source_bloc`, sans prétendre à une source archivée.

### Données économiques (Phases E, E+, E++)

- **Un dataset OLAP unique vaut mieux que N fichiers** : Filosofi et le RP sont lus depuis
  un seul Parquet long (`code_com, annee, source, clef_json, valeur`) publié sur
  data.gouv.fr (1,73 Go national) ; lecture distante DuckDB `httpfs` avec filtre HdF
  poussé, puis cache local (~40 Mo) pour éviter de retélécharger.
- **Suffixe RP `_p` = effectif pondéré, pas un pourcentage** (vérifié sur Lille :
  `actifs_15_64_ans_p = 118 017`). Les taux se calculent à partir des effectifs.
- **Le secret statistique n'a pas la même forme selon la source** : INSEE = valeur NULL
  (drapeau `secret` en base, communes grises sur la carte) ; CNAF = arrondi au multiple
  de 5, sans NULL ni drapeau.
- **Jointure économie × élections sur l'année n-1** : avec Filosofi 2017-2021, seule la
  présidentielle 2022 trouve des données ; le `LEFT JOIN` renvoie NULL pour les autres —
  à expliquer dans l'UI plutôt qu'à masquer.
- **XLSX DREES** : 8 lignes de métadonnées à sauter, un onglet par millésime — détecter
  l'onglet le plus récent plutôt que coder son nom.
- **Deux sources dans une même table** (CNAF et DREES dans `economie_social`) : utiliser un
  upsert `ON CONFLICT DO UPDATE` pour qu'un chargement n'écrase pas les colonnes de l'autre.
- **URSSAF au format large** (une colonne par année) : détecter les colonnes annuelles par
  expression régulière puis passer au format long (Polars) ; 1,15 M lignes pour HdF.
- **Eurostat SDMX TSV** : valeurs suffixées de drapeaux (`8.8 u`), `:` pour manquant ;
  vérifier empiriquement les filtres de dimensions (`isced11`, `sex`, `age`, `unit`).
  Les datasets peuvent être dépréciés (`tgs00005` → `nama_10r_2gdp`).
- **API bloquées par des protections anti-robot** (INSEE BDM/IDBank) : prévoir une source
  alternative plutôt que de contourner la protection.
- **Noms de colonnes dynamiques dans le SQL** : valider contre une liste blanche
  (`frozenset`) avant interpolation ; les valeurs passent par `?`.

### Données parlementaires (Phase F)

- **Les API tierces peuvent disparaître** : NosDéputés.fr (métriques figées depuis juin
  2024) et CLAIR (HTTP 500) sont tombées pendant la phase. Préférer les fichiers publiés
  sur data.gouv.fr ou par les institutions (Datan, data.senat.fr), et garder une URL
  statique de secours à côté de la résolution par API.
- **CSV du Sénat** : encodage cp1252, 18 lignes de commentaires `%` en tête, anciens
  sénateurs inclus (circonscriptions historiques).
- **Le groupe parlementaire ne suffit pas toujours à classer un élu** : les non-inscrits
  masquent l'appartenance réelle (cas de sénateurs RN) → table d'overrides avec
  justification, appliquée à la lecture.
- **Une table de correspondance groupe → bloc sans dimension temporelle contredit le
  classement « de l'époque »** (ADR-0005) : constat ouvert, voir ADR-0007 § Points ouverts.
- **Charger national, filtrer en UI** quand l'unité d'analyse est nationale (composition
  d'une assemblée) : quelques milliers de lignes seulement.

---

## Infra

### Docker

- **Named volumes isolent du host** : un named volume Docker est opaque depuis le filesystem macOS. Les scripts ETL qui écrivent `data/ministere.duckdb` sur l'hôte ne sont pas visibles dans le container si celui-ci monte un named volume. Solution : bind mount `./data:/app/data:ro` en dev.
- **Dev vs prod** : le compose dev utilise un bind mount (DB locale instantanément visible) ; le compose prod utilise un named volume (DB copiée une fois, container autonome). Ne pas confondre les deux en déploiement.
- **Extension spatial DuckDB** : doit être pré-installée dans l'image Docker (`duckdb -c "INSTALL spatial"`), pas téléchargée au runtime. Sans ça, le container plante au premier `LOAD spatial` avec une erreur réseau ou "extension not found".
- **uv dans Dockerfile** : ne pas utiliser `uv:latest` — pinner la version (`uv 0.11.16`) pour garantir des builds reproductibles. Constat 2026-09-24 : appliqué dans le `Dockerfile` racine, pas dans `deploy/Dockerfile`, qui produit l'image publiée sur GHCR (`uv:latest`).
- **Un tag `v*` déclenche la publication de l'image** (`docker-publish.yml`) : les tags correctifs `v0.4.2-actions-fix` et `v0.4.3-fix-spatial` existent sans release GitHub associée. Distinguer tag technique et release annoncée.
- **pages/ dans l'image** : les pages Streamlit (`pages/`) doivent être COPY-ées explicitement dans le Dockerfile. Sans ça, l'app conteneurisée n'affiche que la page d'accueil.

### Backup

- Le script `backup_db.sh` copie depuis le named volume Docker via `docker cp` — il ne fonctionne pas en dev avec bind mount (la DB est directement dans `data/`). Adapter si le workflow de backup change.
- Le plist launchd est planifié à 3h quotidien ; vérifier `data/backups/backup.log` le lendemain après activation.

---

## Workflow Claude Code

### Pre-commit

- **Ruff reformate les fichiers** : quand un commit échoue parce que `ruff-format` a reformaté un fichier, les fichiers modifiés ne sont pas encore stagés. Il faut les `git add` à nouveau avant de relancer le commit. `--amend` seul ne suffit pas, et n'est de toute façon pas recommandé — créer un nouveau commit.
- **C401 (set comprehension)** : ruff refuse `set(x for x in ...)` et exige `{x for x in ...}`. Corrigeable avant commit pour éviter le cycle add → fail → re-add.

### CI après push (Phase D)

- **Identifier le run du commit poussé** : comparer `headSha` du run à `git rev-parse HEAD`.
  En D3.3, le run 27265331430 a été surveillé à la place du run du commit `7f21346` ; un
  échec CI est passé inaperçu pendant deux commits.
- La CI ne se déclenche que sur `main` et sur les PR vers `main` : un push sur une autre
  branche ne lance rien.

### Rapports cités

- Plusieurs rapports cités dans la documentation ou les docstrings n'existent pas dans le
  dépôt (ex. `reports/exploration-elections.md`, `reports/verification-sources-phase-e-plus.md`,
  rapports d'exploration Économie produits par des sous-agents). Commiter un rapport au
  moment où on le cite, ou ne pas le citer.

### DuckDB en test

- Les tests d'intégration ouvrent la vraie DB en `read_only=True` — jamais d'écriture dans les tests. Si la DB est absente, `pytest.skip()` proprement plutôt que `pytest.fail()` : l'absence de DB est un état normal en CI sans ETL préalable.
- Les tests `@pytest.mark.slow` (Streamlit headless) sont exclus du run par défaut pour éviter les 30s de démarrage en CI. Lancer explicitement avec `pytest -m slow`.

### Nomenclature des rapports

- Convention : `reports/session-YYYY-MM-DD_phase-X-recap.md`
- Convention : `reports/audit-phase-X.md` pour les audits techniques ponctuels

---

## Architecture / code

### Vues calculées vs tables matérialisées

- **Choix : vues calculées** (CREATE OR REPLACE VIEW). Conséquence : un changement de classement politique = une ligne dans une table de référence, pas un rechargement de données. Changement de bloc d'un parti = UPDATE dans `nuances_harmonisees` ou `candidats_presidentielle`, la vue reflète le changement immédiatement.
- Inconvénient accepté : les vues complexes avec multiples jointures peuvent être lentes sur des volumes non filtrés. Mitiger avec des filtres `WHERE` explicites dans les requêtes Streamlit.

### Streamlit

- `@st.cache_data` pour les DataFrames et GeoDataFrames (sérialisables). `@st.cache_resource` pour les connexions DuckDB (non sérialisables). Mélanger les deux décorateurs cause des erreurs obscures à l'exécution.
- Streamlit relance tout le script à chaque interaction — ne jamais mettre de logique lourde hors des fonctions cachées.
- GeoJSON complet France entière = trop lourd pour Folium. `gdf.simplify(0.001)` en amont, ou pré-simplifier au chargement DuckDB (`geometry_simplified_*`).
- **Clic sur carte** : `st_folium` ne renvoie pas les propriétés de l'entité cliquée dans la version utilisée (Phase D2) → drill-down par liste déroulante.
- **Hachures Folium** non rendues : les communes « Non classé » sont en gris uni, la légende l'explique.
- **Pattern de connexion réel** : Géographie utilise une connexion `@st.cache_resource` ; les modules `viz/*_queries.py` ouvrent une connexion `read_only` par appel et mettent le résultat en `@st.cache_data`. Les deux coexistent.

### Design system et navigation (août 2026)

- **Le thème natif Streamlit prime sur le CSS injecté** pour les composants qui lisent le thème interne (dataframe `glide-data-grid`, Plotly avec `theme="streamlit"`, widgets natifs). `.streamlit/config.toml` avec `base = "dark"` rendait ces composants sombres malgré le CSS clair : corriger `config.toml` (`base = "light"`), pas empiler des `!important`. Un changement de `[theme]` exige un redémarrage du processus Streamlit.
- **Vérifier les `data-testid` dans le DOM réel** de la version installée : des sélecteurs proposés par un outil externe (`stVerticalBlockBorderWrapper`, `baseButton-secondary`, `stAppViewBlockContainer`) n'existent pas en 1.57.0.
- **Cibler le bon niveau du DOM** : la troncature des libellés `st.metric` vient du `<p>` interne de `stMetricLabel`, pas du conteneur — un premier correctif sur le conteneur était inopérant.
- **Polices** : charger Google Fonts par une balise `<link>` ; un `@import` dans un bloc CSS injecté par `st.markdown` ne se charge pas de façon fiable.
- **Icônes de navigation** : la découverte automatique de `pages/` ne permet que l'emoji du nom de fichier ; une icône Material dans la sidebar impose `st.navigation()` / `st.Page(icon=...)` (ADR-0009). Avec le routeur, `set_page_config` et l'injection CSS se font une seule fois dans `app.py`.
- **Constantes dupliquées = divergence** : `legislatif.py` et `economie.py` avaient chacun leur palette de blocs, différente des tokens `--nuance-*`. Regrouper dans un module partagé (`_blocs_politiques.py`) ; les couleurs restent toutefois recopiées à trois endroits (CSS, module Python, table `blocs_politiques`).
