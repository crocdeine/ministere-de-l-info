# Leçons techniques — ministere-de-l-info

Consolidation des gotchas et leçons tirées de chaque phase. Mise à jour à chaque clôture de phase.

Dernière mise à jour : Phase C (2026-06-01, tag v0.3-elections-pres).

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

---

## Infra

### Docker

- **Named volumes isolent du host** : un named volume Docker est opaque depuis le filesystem macOS. Les scripts ETL qui écrivent `data/ministere.duckdb` sur l'hôte ne sont pas visibles dans le container si celui-ci monte un named volume. Solution : bind mount `./data:/app/data:ro` en dev.
- **Dev vs prod** : le compose dev utilise un bind mount (DB locale instantanément visible) ; le compose prod utilise un named volume (DB copiée une fois, container autonome). Ne pas confondre les deux en déploiement.
- **Extension spatial DuckDB** : doit être pré-installée dans l'image Docker (`duckdb -c "INSTALL spatial"`), pas téléchargée au runtime. Sans ça, le container plante au premier `LOAD spatial` avec une erreur réseau ou "extension not found".
- **uv dans Dockerfile** : ne pas utiliser `uv:latest` — pinner la version (`uv 0.11.16`) pour garantir des builds reproductibles.
- **pages/ dans l'image** : les pages Streamlit (`pages/`) doivent être COPY-ées explicitement dans le Dockerfile. Sans ça, l'app conteneurisée n'affiche que la page d'accueil.

### Backup

- Le script `backup_db.sh` copie depuis le named volume Docker via `docker cp` — il ne fonctionne pas en dev avec bind mount (la DB est directement dans `data/`). Adapter si le workflow de backup change.
- Le plist launchd est planifié à 3h quotidien ; vérifier `data/backups/backup.log` le lendemain après activation.

---

## Workflow Claude Code

### Pre-commit

- **Ruff reformate les fichiers** : quand un commit échoue parce que `ruff-format` a reformaté un fichier, les fichiers modifiés ne sont pas encore stagés. Il faut les `git add` à nouveau avant de relancer le commit. `--amend` seul ne suffit pas, et n'est de toute façon pas recommandé — créer un nouveau commit.
- **C401 (set comprehension)** : ruff refuse `set(x for x in ...)` et exige `{x for x in ...}`. Corrigeable avant commit pour éviter le cycle add → fail → re-add.

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
