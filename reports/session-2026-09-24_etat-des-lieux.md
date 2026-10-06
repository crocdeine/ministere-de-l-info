# État des lieux complet — ministere-de-l-info

**Date** : 2026-09-24
**Contexte** : première session cloud (conteneur éphémère, sans base DuckDB locale, réseau restreint)
**Branche** : `claude/exciting-dirac-8mogwe` (identique à `main` au démarrage, commit `d382354`)
**Nature** : audit en lecture seule — aucune modification de code, aucune décision prise

---

## 1. Périmètre de la lecture

| Catégorie | Contenu lu |
|---|---|
| Mémoire projet | `CLAUDE.md`, `README.md` |
| Documentation | `docs/architecture.md`, `schema-elections.md`, `data-sources.md`, `deployment.md`, `lessons-learned.md`, `guide-utilisateur.md` |
| Décisions | ADR 0001 à 0006 + index `docs/adr/README.md` |
| Sources officielles | `docs/sources-officielles/nuances/index.md`, décisions CE n°437675 (2020) et n°512694 (2026), annexe 3 de la circulaire INTP2602966C (PDF) |
| Rapports | les 20 fichiers de `reports/` (récaps de session, explorations, mappings de nuances, brainstorm UI/UX, santé ETL, nettoyage) |
| Skills projet | `projet-conventions`, `data-viz-politique`, `streamlit-duckdb-patterns`, `insee-duckdb-loader`, `latex-rapport-fr` |
| Configuration | `pyproject.toml`, `.github/workflows/*`, `.pre-commit-config.yaml`, `.streamlit/config.toml`, `.env.example`, `Dockerfile`, `deploy/*`, `docker-compose*.yml`, `scripts/*.sh` |
| Historique | `git log` (clone superficiel : 50 derniers commits visibles), releases et runs CI GitHub |

Vérifications exécutées :

- `uv run ruff check .` → propre ; `uv run ruff format --check .` → 88 fichiers conformes.
- `uv run pytest` → 13 passés, 342 ignorés (base absente), 26 échecs/erreurs **tous dus au réseau du conteneur** (proxy 403 sur IGN/INSEE/data.gouv, téléchargement de l'extension DuckDB `spatial` refusé). Aucun échec imputable au code.
- CI GitHub : run 32278797563 **vert** sur `d382354` (HEAD de `main`).

---

## 2. Synthèse du projet

Application web locale (Streamlit + DuckDB, Python 3.12, uv) de data-visualisation politique, électorale et territoriale. Une base analytique unique (`data/ministere.duckdb`, ~900 Mo, ~635 Mo compressée) alimentée par des scripts ETL à partir de sources publiques officielles.

| Module | Contenu | Périmètre | Statut |
|---|---|---|---|
| Géographie | 6 niveaux (régions → circonscriptions), populations 2013/2018/2023 | France | ✅ v0.2 |
| Élections | Présidentielles 2002-2022, législatives 2002-2024, municipales 2008-2026, drill-down bureau de vote ; 30 scrutins, 216 mappings nuance→bloc | Hauts-de-France | ✅ v0.4 |
| Économie | Filosofi, RP (chômage, CSP, logements sociaux), CNAF RSA, DREES APL/déserts médicaux, URSSAF 2006-2025, Eurostat (HdF vs France) ; croisement économie × présidentielles | Hauts-de-France | ✅ v0.5 |
| Législatif | 4 065 élus AN + Sénat depuis 2002 (Datan + data.senat.fr), scores d'activité AN | France (filtre HdF en UI) | ✅ v0.5 |
| Design system | Tokens CSS (Bleu France, Marianne), navigation `st.navigation()`, Accueil hub, icônes Material | — | ✅ (non publié en release) |

### Chronologie

| Période | Phase | Jalon |
|---|---|---|
| 18-21 mai | Géographie | 34 877 communes, 3 millésimes population — tag `v0.2` |
| 21-27 mai | A — Qualité | Décomposition des gros fichiers, CI, logging, pre-commit, ADR 0001-0004 |
| 27 mai | B — Docker | Image, compose dev/prod, backups launchd — release `db-2026-05` |
| 27 mai-1er juin | C — Présidentielles | 6 blocs officiels (ADR-0005) — tag `v0.3-elections-pres` |
| 1er-10 juin | D — Législatives + municipales | Drill-down BV — release `v0.4-elections-complet` |
| 11 juin | Déploiement Mac | `install.sh`/`update.sh`, image GHCR — release `v0.4.1-deploy-init` |
| 11-18 juin | E, E+, E++ — Économie | ADR-0006, 7 puis 11+ indicateurs |
| 19-25 juin | F — Législatif | Pivot national, Datan — release `v0.5-economie-legislatif` (avec DB) |
| 1er-19 août | Design system | Tokens, config thème clair, navigation, couleurs réconciliées |

### Principe méthodologique central (ADR-0005)

Classement dans les 6 blocs officiels du ministère de l'Intérieur (EXG, GAU, DIV, CENT, DTE, EXD), selon la grille **en vigueur à la date du scrutin** (« classement de l'époque »), avec une justification par ligne (`source_bloc`). Exemple de référence : LFI = GAU jusqu'en 2024, EXG à partir des municipales 2026 (INTP2602966C, validée par CE 27/02/2026 n°512694).

---

## 3. Constats — par ordre de gravité

### 3.1 Classements municipaux contraires à la grille officielle (CRITIQUE — données affichées)

Source vérifiée : annexe 3 de `docs/sources-officielles/nuances/2026-municipales_INTP2602966C.pdf` (regroupement des nuances de listes par bloc). Code concerné : `scripts/load_elections_municipales.py`.

| Code | Années | Classement projet | Grille officielle 2026 | Remarque |
|---|---|---|---|---|
| `LCOM` (PCF) | 2008, 2014, 2020, 2026 | EXG | **GAU** | Incohérent avec le reste du projet : `COM` = GAU en législatives/présidentielles, GDR/CRCE-K = GAU dans Législatif, skill `data-viz-politique` = GAU |
| `LUDI` (UDI) | 2014, 2020, 2026 | DIV (« Union Divers ») | **CENT** | Code vraisemblablement mal décodé |
| `LUD` (Union de la droite) | 2014, 2020 | CENT (« Union Démocratique / UDI ») | **DTE** | Code vraisemblablement inversé avec LUDI |
| `LECO` | 2026 | GAU | **DIV** | Pour 2020, à vérifier dans INTA1931378J |

Pour 2026, ce sont des contradictions directes avec la source que le projet revendique. Pour 2014/2020, les grilles d'époque doivent être vérifiées, mais la lecture des codes LUD/LUDI paraît erronée. `LUD` 2026 n'est pas mappé (à vérifier s'il apparaît dans les données HdF). Impact : cartes « bloc dominant », évolution des blocs et drill-down municipaux.

### 3.2 Législatif : classement rétroactif du groupe FI (IMPORTANT)

`src/ministere_de_l_info/etl/loaders/legislatif_datan.py` mappe le groupe `FI` → EXG sans distinction de législature. Les députés LFI de la XVe législature (2017-2022) sont donc classés EXG, alors que l'ADR-0005 impose GAU pour 2017. L'onglet « Évolution historique » est incohérent avec le module Élections. À noter : pour les élus actuels (grille 2026), EXG est conforme.

### 3.3 Déploiement : contrôle d'intégrité de la base probablement cassé (IMPORTANT)

- `scripts/publish_db.sh` calcule le SHA256 du fichier **compressé** (`ministere.duckdb.gz`).
- `deploy/update.sh` compare ce SHA256 à celui de la base locale **décompressée**.
- `deploy/README-deploy.md` documente une troisième variante (hash du fichier décompressé nommé `.gz.sha256`).

Si la release a été publiée avec `publish_db.sh`, les empreintes ne correspondent jamais → retéléchargement de 635 Mo à chaque mise à jour. Non confirmé (fichier `.sha256` de la release illisible depuis ce conteneur). `update.sh` n'a jamais été testé en réel (TODO de CLAUDE.md).

### 3.4 Deux Dockerfiles divergents (MOYEN)

| Fichier | Usage | Caractéristiques |
|---|---|---|
| `Dockerfile` (racine) | Compose local dev/prod | Multi-stage, `uv` 0.11.16 figé, utilisateur non-root, Tectonic |
| `deploy/Dockerfile` | **Image publiée sur GHCR** (utilisateurs finaux) | `uv:latest` non figé, exécution root, pas de Tectonic |

L'image réellement distribuée contredit la leçon « pinner uv » (`lessons-learned.md`). La dernière image publiée date de v0.5 (25 juin) : le chantier design system n'est pas dans l'image.

### 3.5 Documentation en retard ou contradictoire (MOYEN)

| Document | Écart |
|---|---|
| `README.md` | Tableau modules figé à la phase C (Législatif « Phase D », Économie « à cadrer ») ; arborescence Géographie seule |
| `docs/architecture.md` | Pages Législatif/Économie décrites comme stubs, `4_💶_Économie.py`, 331 tests, pas de `_theme.py` ni `st.navigation` |
| `docs/adr/README.md` | Index sans l'ADR-0006 |
| `docs/lessons-learned.md` | Dernière mise à jour phase C |
| `docs/guide-utilisateur.md` | Couvre uniquement Géographie |
| `docs/data-sources.md` | Aucune source économie ni législatif ; référence `scripts/load_elections.py` et `reports/exploration-elections.md` inexistants |
| `docs/schema-elections.md` | « 5 vues », 149 nuances ; extension municipale et tables économie/législatif partiellement documentées |
| `docs/sources-officielles/nuances/index.md` | INTA1931378J signalé « PDF à télécharger manuellement » alors que le PDF est archivé |
| `CLAUDE.md` | Déploiement « v0.4.3 » inexistant (releases : v0.4.1, v0.5) ; « 75.34 % » de coverage recopié à l'identique pour Économie et Législatif ; pointeurs « 5 ADR » ; règle « branche par feature, PR squash-merge » jamais appliquée (aucune PR, tout sur `main`) |
| Skill `projet-conventions` | Noms de tables faux (`communes`, `nuances_blocs`), feuille de route Économie déjà réalisée, « branche `main` uniquement » en contradiction avec CLAUDE.md |
| ADR-0006 | Prévoit Sirene pour `part_emploi_industriel` ; réalisé via le RP. Filosofi annoncé 2012-2022, chargé 2017-2021 |
| Rapports cités mais absents | `audit-phase-a.md`, `audit-phase-b.md`, `exploration-elections.md`, `exploration-elections-municipales.md`, 8 rapports `exploration-economie-*` / `brainstorm-*` / `sweep-*` / `verification-*` |

### 3.6 Décisions structurantes sans ADR (MOYEN)

Contraire à la règle CLAUDE.md « toute décision non triviale → ADR » :

1. Module Législatif : pivot HdF → national, abandon NosDéputés/CLAIR, adoption Datan + Sénat CSV, table de correspondance groupes → blocs.
2. Sources Économie E+/E++ : CNAF, DREES, URSSAF, Eurostat (hors du périmètre de l'ADR-0006).
3. Design system et migration `st.navigation()` / `st.Page()` (changement d'architecture de navigation).

### 3.7 Dette technique mineure

- **CI** : déclenchée uniquement sur `main` et sur PR vers `main` — un push sur une branche de travail ne déclenche rien.
- **Tests non hermétiques** : plusieurs tests appellent les API réelles (IGN, INSEE Mélodi, data.gouv) — dépendance à la disponibilité des services externes.
- **Couverture** : ~60 % en CI (pages et requêtes dépendantes de la base exclues du calcul) ; les chiffres ~75 % sont mesurés avec la base locale.
- **Code mort** : `legislatif_nosdeputes.py`, `legislatif_clair.py` (conservés « pour traçabilité ») ; `scripts/etl_regions.py` + `tests/test_etl_regions.py` + alias `fetch_regions_geojson` (suppression en attente depuis mai).
- **Conventions** : `print()` dans `etl/loaders/communes.py` ; pandas dans `economie_drees.py` et `economie_eurostat.py` (probablement justifié : XLSX/TSV).
- **`pyproject.toml`** : version `0.1.0`, description « Add your description here » ; dépendances Jinja2/Tectonic/`anthropic` sans fonctionnalité associée (génération de rapports PDF non implémentée).
- **Historique** : clone superficiel (50 commits) — les commits des phases Géographie/A/B ne sont pas visibles depuis ce conteneur.

### 3.8 Limites de données connues (acceptées, documentées)

- Mayotte sans population (source INSEE séparée).
- 135 communes du Grand Paris à EPCI multiple, 11 EPT sans département ; Saint-Pierre-et-Miquelon codé `NR`.
- `comptee_a_part` et `totale` NULL (PCAP absent de la source).
- Circonscriptions : source communautaire (non officielle AN) ; `code_circo` reconstruit pour 2002/2007/2024.
- Municipales 2008 : Nord quasi absent du fichier officiel (2 communes).
- `no_panneau` synthétique pour les municipales 2008.
- Législatif : pas de scores Sénat, pas de votes nominatifs, évolution historique approximative (législature de référence = dernière législature Datan).
- Hachures Folium non rendues ; pas de clic carte → drill-down (dropdown uniquement).

---

## 4. Contraintes de l'environnement cloud

| Contrainte | Conséquence |
|---|---|
| Pas de `data/` ni de base DuckDB | Pas de lancement réel de l'app, 342 tests ignorés, ETL impossible |
| Proxy réseau restrictif | API IGN/INSEE/data.gouv, extension DuckDB `spatial` et téléchargement des releases GitHub bloqués |
| Pas de `gh` CLI | Vérification CI via les outils GitHub (même principe : comparer `head_sha` au HEAD) |
| Pas de Docker/OrbStack | Pas de test de déploiement |
| Conteneur éphémère | Tout travail doit être commité et poussé avant la fin de session |

---

## 5. Pistes proposées (aucune engagée — validation requise)

| Priorité | Action | Nature |
|---|---|---|
| 1 | Corriger `LCOM`, `LUDI`, `LUD`, `LECO` après vérification des grilles 2008/2014/2020 ; tracer dans `source_bloc` et ADR-0005 | Décision méthodologique |
| 2 | Rendre le mapping des groupes Législatif dépendant de la législature (FI 2017-2024 → GAU) | Décision méthodologique |
| 3 | Aligner `publish_db.sh`, `update.sh` et `README-deploy.md` sur une seule convention de checksum | Correctif technique |
| 4 | Unifier les Dockerfiles (un seul, figé, non-root) ; publier une release incluant le design system | Décision infra |
| 5 | Rattrapage documentaire (README, architecture, index ADR, lessons-learned, data-sources, guide utilisateur, skill `projet-conventions`, CLAUDE.md) | Documentation |
| 6 | ADR manquants : Législatif (sources + pivot national), sources Économie E+/E++, navigation/design system | Documentation |
| 7 | Nettoyage : code mort, `print()`, métadonnées `pyproject.toml`, workflow Git (PR ou non) | Dette |
