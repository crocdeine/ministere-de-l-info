# Audit état global — 2026-08-19

Contexte : audit post-clôture chantier design system (dernier commit local/pushé : `d382354`, "feat(ui): clôture chantier design system — filtres, couleurs, icônes sidebar"). Audit uniquement — aucune correction, aucun commit, aucun push effectué.

**Limitation méthodologique** : l'outil Bash du sandbox était indisponible (`VM_DISK_SPACE_INSUFFICIENT`, même symptôme que la session précédente). `uv run pytest`, `uv run ruff check/format` n'ont pas pu être exécutés. Audit réalisé par inspection statique (Read/Glob/Grep) + API/pages web GitHub publiques (repo public, sans auth).

---

## 1. Statut CI du dernier push

Vérification stricte du SHA (règle CLAUDE.md — leçon D3.3) :

| Élément | Valeur |
|---|---|
| HEAD local (`.git/refs/heads/main`) | `d3823547239522fd0dcaa861c20895099e90bb25` |
| HEAD distant (`.git/refs/remotes/origin/main`) | `d3823547239522fd0dcaa861c20895099e90bb25` — identique |
| Run CI déclenché | `CI #62`, run id `32278797563`, workflow `ci.yml` |
| Commit associé au run | `d382354` — **correspond exactement au HEAD** |
| Statut | **Success** |
| Durée | 1m 11s (job `Lint & Format` 14s + job `Tests & Coverage` 1m 9s) |
| Artefact | `coverage-report` (152 KB) produit |

Confirmation supplémentaire : `raw.githubusercontent.com/.../main/CLAUDE.md` et `.../main/pyproject.toml` renvoient un contenu identique à la copie locale committée (hors la modification non commitée décrite en section 4) — le push a bien atteint `main`.

**Verdict : CI verte, sur le bon commit.** Pas de faux positif à la D3.3.

---

## 2. Tests

`uv run pytest` non exécutable (Bash indisponible). Le job CI "Tests & Coverage" du run #62 est passé (1m 9s), ce qui constitue une preuve indirecte fiable — même run, même SHA que le HEAD local.

Inspection statique complémentaire :

- `tests/test_streamlit_smoke.py` référence `app.py` (racine) et `pages/2_🗳️_Élections.py` — chemins cohérents avec la structure post-migration `st.navigation()`. Les tests `AppTest.from_file()` chargent directement les fichiers de `pages/`, qui ne contiennent plus de `st.set_page_config()` (déplacé dans `app.py`) — pas de conflit.
- `tests/test_pages_geographie.py`, `test_pages_legislatives.py`, `test_pages_municipales.py` testent la logique métier via `sys.path.insert(0, src)`, indépendamment du routeur — non affectés par la migration.
- Aucune référence cassée trouvée à un ancien chemin de page (`pages/*.py` avant renommage, `st.set_page_config` dupliqué, etc.).

Comptage brut (`def test_` dans `tests/*.py`, tous fichiers, y compris méthodes de classe) : **351 fonctions de test** réparties sur 19 fichiers, + 13 décorateurs `@pytest.mark.parametrize` (qui multiplient le nombre de cas réellement collectés par pytest). Compte exact non vérifiable sans `pytest --collect-only`.

---

## 3. Lint (ruff)

`uv run ruff check .` / `ruff format --check .` non exécutables. Le job CI "Lint & Format" du run #62 est passé — preuve indirecte que le repo est lint-clean sur le commit HEAD (le workflow CI exécute vraisemblablement `ruff check` + `ruff format --check` sur l'ensemble du repo, scripts d'exploration compris, sauf s'ils sont exclus par config ou par `.gitignore` — voir section 4).

Inspection manuelle ciblée (fichiers touchés par le chantier design system : `app.py`, `pages/*.py`, `_theme.py`, `_blocs_politiques.py`) :

- Un seul `st.set_page_config()` dans tout le repo (`app.py:20`), un seul appel à `inject_css()` (`app.py:25`) — pas de duplication après migration.
- Pas d'import cassé, pas d'`import *`, pas d'`except:` nu, pas d'argument mutable par défaut détecté dans `src/`.
- `_blocs_politiques.py` (source unique couleurs/blocs) bien référencé par les 4 modules consommateurs (`legislatif.py`, `economie.py`, `elections_legislatives.py`, `elections_presidentielles.py`) — la réconciliation des palettes annoncée dans CLAUDE.md est vérifiée dans le code, pas seulement déclarée.
- Un seul `print()` en dehors des scripts CLI/ETL et hors périmètre "chantier séparé" : `src/ministere_de_l_info/etl/loaders/communes.py:34` (message de progression avant un chargement long). Pré-existant, non lié à cette session, non bloquant. Note : la règle ruff `T20` (interdiction `print`) n'est pas activée dans `[tool.ruff.lint].select` — ce n'est donc pas une violation lint outillée, juste un écart à la convention CLAUDE.md « pas de print() en code prod ».

**Verdict : pas de régression lint détectée sur le périmètre du chantier UI.**

---

## 4. Hygiène git

Bash indisponible → pas de `git status` direct. Reconstruction par diff manuel local vs `raw.githubusercontent.com/main` (= état committé exact du HEAD).

### Modification non commitée confirmée

`pyproject.toml` local contient un bloc absent du dépôt distant :

```toml
[tool.uv.workspace]
members = ["scratch/playwright_test"]
```

**Point d'attention réel** : `scratch/playwright_test` **n'existe pas sur le disque** (`Glob scratch/**` → aucun résultat). Une déclaration de workspace member pointant vers un chemin inexistant peut faire échouer `uv sync` / `uv run` selon la version d'uv (comportement à vérifier). À corriger ou nettoyer avant que ça ne bloque un `uv sync` sur une autre machine.

### Fichiers non trackés confirmés

- Scripts d'exploration à la racine : `analyze_senators.py`, `explore_apis.py`, `explore_senat.py`, `scratch_fetch.py` — tous présents sur disque, tous absents du dépôt distant. Chantier séparé connu, hors périmètre de cet audit.
- `scripts/_explore_elections.py`, `scripts/covers/generate_covers.py` — idem.
- `data/` : `ministere.duckdb`, `ministere.duckdb.gz`, `ministere.duckdb.gz.sha256`, `ministere.duckdb.safe`, `.DS_Store` — déjà couverts par les patterns `.gitignore` (`*.duckdb`, `*.duckdb.gz`, `*.duckdb.gz.sha256`, `.DS_Store`). Correctement ignorés, rien à corriger.
- `reports/*.md` : 37 fichiers présents dans `reports/`, tous des comptes-rendus de sessions/explorations légitimes selon la convention du projet (`reports/session-*.md`, `reports/exploration-*.md`, etc.) — ces fichiers ne sont normalement PAS destinés à `.gitignore` (ce sont des livrables de mémoire projet, cf. section "Discipline de mémoire" du CLAUDE.md). S'ils apparaissent comme non trackés, c'est probablement qu'ils n'ont simplement pas encore été commités (oubli de `git add`), pas un problème de `.gitignore`.

### `.gitignore`

Structure correcte et couvre bien : Python build artefacts, `.venv`, secrets, `data/{raw,interim,processed,external,backups}` + extensions DB/parquet, cache tests/lint, macOS/IDE, LaTeX build. **Absent** : aucune règle pour les scripts d'exploration à la racine (`analyze_senators.py` etc.) — cohérent avec le fait qu'ils sont un chantier connu et volontairement non traité ici, mais si l'intention est de les garder hors dépôt durablement, un pattern dédié (ou un déplacement vers un dossier `scratch/` déjà ignoré) simplifierait le `git status`.

---

## 5. Cohérence de la documentation (chiffres de tests)

| Module (CLAUDE.md) | Chiffre annoncé | Vérification |
|---|---|---|
| Législatif | "381 tests, 75.34% coverage" | Non vérifiable exactement (pas de `pytest --collect-only`). Ordre de grandeur plausible : 351 `def test_` bruts + 13 `parametrize` sur l'ensemble de la suite (tous modules confondus, pas seulement Législatif) — le chiffre de CLAUDE.md semble être un total cumulatif de la suite au moment de la clôture de la Phase F, pas un compte isolé du module. Cohérence globale plausible, précision non garantie. |
| Économie | "348 tests" | Idem — `test_economie.py` contient 20 `def test_` bruts ; le chiffre CLAUDE.md est vraisemblablement le total de suite à la clôture Phase E++, antérieur à l'ajout des tests Législatif/UI. |

Autre écart mineur repéré : la table "Pointeurs vers la documentation" du CLAUDE.md indique `docs/adr/` → "5 ADR", alors que **6 ADR existent** sur disque (`0001` à `0006`, `0006` = module Économie). Écart de comptage à corriger dans CLAUDE.md (mineur, cosmétique).

---

## 6. Revue du code des pages Streamlit (régression post-migration `st.navigation()`)

Fichiers lus intégralement : `app.py`, `pages/0_🏠_Accueil.py`, `pages/1_📍_Géographie.py`, `pages/2_🗳️_Élections.py`, `pages/3_🏛️_Législatif.py`, `pages/4_📊_Économie.py`, `src/ministere_de_l_info/_theme.py`.

- `app.py` : routeur unique propre. `st.set_page_config()` + `inject_css()` appelés une seule fois avant `st.navigation([...]).run()`. Les 5 entrées déclarent `title`, `icon` (Material Symbols), `url_path` ; `Accueil` marqué `default=True`. Structure conforme à la description CLAUDE.md.
- `pages/0_🏠_Accueil.py` : hub de navigation à 4 tuiles (`st.page_link` vers les 4 modules), diagnostic technique en bas de page. Pas de `set_page_config`, pas de `inject_css` — correct.
- `pages/1_📍_Géographie.py` : le plus long/complexe des 5, aucun problème structurel détecté ; utilise `@st.cache_resource` pour la connexion DuckDB (conforme au gotcha #2 du CLAUDE.md).
- `pages/2_🗳️_Élections.py`, `3_🏛️_Législatif.py`, `4_📊_Économie.py` : délèguent à des fonctions `render()` dans `src/ministere_de_l_info/pages/*.py` — pattern cohérent, imports valides.
- `_theme.py` : `inject_css()` documente explicitement (docstring) le nouveau contrat post-migration ("un seul appel dans app.py … les fichiers pages/*.py n'ont plus besoin de l'appeler individuellement") — la doc inline est à jour avec le code.

**Aucune régression évidente détectée** (pas de double `set_page_config`, pas d'import cassé, pas de référence à un ancien chemin de fichier).

---

## Verdict global

Le chantier design system a été pushé proprement : CI verte sur le bon SHA, structure `st.navigation()` cohérente de bout en bout (code + tests + doc inline), palette de blocs politiques effectivement unifiée dans le code (pas juste documentée). Rien d'alarmant détecté dans le périmètre de ce chantier.

Les points d'attention identifiés sont tous **antérieurs ou périphériques** au chantier UI : hygiène git de fin de session (staging oublié), une référence `pyproject.toml` vers un chemin inexistant, deux petits écarts cosmétiques dans CLAUDE.md.

### À traiter (même mineur)

1. **`pyproject.toml`** : `[tool.uv.workspace] members = ["scratch/playwright_test"]` pointe vers un chemin inexistant sur le disque. Soit créer le dossier, soit retirer la ligne — risque de casser `uv sync`/`uv run` sur une machine propre (clone frais).
2. **Commit ou stash** de la modification `pyproject.toml` ci-dessus — actuellement en attente indéfiniment, contraire à la discipline "toujours `git status` avant `git add .`".
3. **`reports/*.md`** : vérifier si les rapports listés comme non trackés (dont potentiellement `session-2026-08-19_design-system-cloture.md`, cité par CLAUDE.md comme "dernier rapport") sont bien commités — sinon la mémoire de session documentée dans CLAUDE.md n'est pas réellement versionnée.
4. **CLAUDE.md** : corriger "5 ADR" → "6 ADR" dans le tableau des pointeurs de documentation (cosmétique).

### À surveiller (pas d'action immédiate)

5. Scripts d'exploration à la racine (`analyze_senators.py`, `explore_apis.py`, `explore_senat.py`, `scratch_fetch.py`, `scripts/_explore_elections.py`, `scripts/covers/generate_covers.py`) — chantier séparé déjà identifié comme tel, à ranger (déplacement vers un dossier ignoré, ou suppression) quand ce chantier sera traité.
6. Chiffres "381 tests" (Législatif) / "348 tests" (Économie) dans CLAUDE.md — probablement des totaux de suite historiques à la clôture de chaque phase plutôt que des comptes par module ; à re-fiabiliser avec un vrai `pytest --collect-only -q | tail -1` lors d'une prochaine session avec Bash disponible.
7. `src/ministere_de_l_info/etl/loaders/communes.py:34` — `print()` isolé en code prod ETL, non couvert par la règle ruff `T20` (non activée). Cosmétique, pré-existant.
8. Refaire cet audit avec Bash disponible pour obtenir les chiffres exacts (`pytest --collect-only`, `ruff check .`, couverture réelle) — l'indisponibilité du sandbox (`VM_DISK_SPACE_INSUFFICIENT`) s'est reproduite deux sessions de suite, ça mérite un signalement séparé si ça persiste.
