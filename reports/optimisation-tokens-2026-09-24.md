# Optimisation de la consommation de tokens — Claude Code

**Date** : 2026-09-24 — **Agent** : outilleur-claude (session cloud, worktree isolé)
**Périmètre** : `.claude/`, `reports/README.md`, propositions pour CLAUDE.md (non modifié)
**Base** : `513e26d` (branche `claude/exciting-dirac-8mogwe`)

## Résumé exécutif

1. Contexte fixe d'une session (CLAUDE.md + liste des skills) : **20,5 Ko → 18,6 Ko appliqué** (≈ 5 900 → 5 300 tokens), **→ 7,0 Ko** (≈ 2 000 tokens, −66 %) une fois la proposition CLAUDE.md appliquée.
2. Skills tiers (canvas-design, frontend-design, skill-creator, code-review-excellence) : `disable-model-invocation: true` ; leur description sort du contexte ; ils restent invocables à la main (`/nom`).
3. code-review-excellence : 15 guides de langages absents (React, Vue, Rust, Go, Java, Kotlin…) et README/CONTRIBUTING supprimés (−11 000 lignes) ; guides Python, CSS et transverses conservés.
4. Descriptions des skills projet raccourcies et mises entre guillemets (4 frontmatters étaient du YAML invalide en lecture stricte : « : » non protégé).
5. Agents : `model: sonnet` pour documentaliste, developpeur-ui, ingenieur-infra, outilleur-claude ; modèle hérité conservé pour verificateur-code, chercheur-donnees, ingenieur-etl, architecte-restructuration.
6. Tous les agents : bloc « Sobriété » (pas de relecture de CLAUDE.md, lecture ciblée, sorties filtrées) et réponse finale normalisée ≤ 15 lignes ; verificateur-code ne relit plus CLAUDE.md (≈ 4 800 tokens par lancement).
7. Nouveau skill `economie-tokens` ; index `reports/README.md` avec convention « résumé exécutif de 10 lignes ».
8. `settings.json` : allow `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` ; ask sur `--fix`, `--add-noqa`, `--basetemp`. Hook SessionStart vérifié silencieux.
9. Proposition CLAUDE.md : `reports/claude-md-allege-propose.md` (16,8 Ko → 5,2 Ko, gotchas vers `.claude/rules/` à portée de chemin).
10. Décisions à soumettre : D1 à D5 (§ 8).

## 1. Mécanismes vérifiés dans la documentation officielle

Pages consultées le 2026-09-24 : `code.claude.com/docs/en/` *sub-agents*, *skills*, *costs*,
*memory*, *settings*, *permissions*.

| Fait | Source |
|---|---|
| CLAUDE.md est chargé au démarrage de chaque session **et de chaque sous-agent** (sauf Explore/Plan), sauf `omitClaudeMd: true` | sub-agents |
| `skills:` dans un agent injecte **le contenu complet** du skill au démarrage | sub-agents |
| Champ `model` : `sonnet`, `opus`, `haiku`, ID complet ou `inherit` ; aussi `effort`, `maxTurns` | sub-agents |
| Description d'un skill toujours en contexte ; corps chargé à l'invocation, puis conservé ; `disable-model-invocation: true` retire la description du contexte | skills |
| Description + `when_to_use` tronquées à 1 536 caractères ; `SKILL.md` < 500 lignes recommandé ; fichiers de référence chargés à la demande | skills |
| CLAUDE.md : viser < 200 lignes ; les imports `@path` sont chargés au démarrage (aucun gain) ; `.claude/rules/` avec `paths` chargés seulement à la lecture de fichiers correspondants ; commentaires HTML de bloc retirés avant injection | memory |
| « Sonnet handles most coding tasks well and costs less than Opus » ; `model: haiku` conseillé pour les tâches simples de sous-agent | costs |
| Règles évaluées dans l'ordre deny → ask → allow ; `*` couvre tout texte ; commandes composées découpées ; `git status/log/diff`, `ls`, `grep`, `cat`, `head`… déjà en lecture seule sans invite | permissions |
| `Read(...)` en deny bloque aussi Edit/Write sur le chemin ; ne s'applique pas aux sous-processus | permissions |

Non vérifié : le paramètre `model` à l'appel de l'outil Agent par le directeur (surcharge
ponctuelle) ; le ratio de prix exact Sonnet/Opus. Non affirmés ici.

## 2. Estimation du contexte fixe (avant / après)

Hypothèse : ≈ 3,5 octets par token pour du français (UTF-8 accentué), incertitude ± 20 %.

| Élément (chargé à chaque tour) | Avant | Après (appliqué) | Après proposition CLAUDE.md |
|---|---:|---:|---:|
| CLAUDE.md | 16 771 o (≈ 4 800 t) | 16 771 o | 5 215 o (≈ 1 500 t) |
| Liste des descriptions de skills | 3 778 o (≈ 1 100 t) | 1 803 o (≈ 500 t) | 1 803 o |
| **Total session (directeur)** | **20,5 Ko ≈ 5 900 t** | **18,6 Ko ≈ 5 300 t** | **7,0 Ko ≈ 2 000 t** |
| Règles `.claude/rules/` (conditionnelles) | — | — | 0 à ≈ 2,2 Ko selon les fichiers lus |

Par sous-agent : même CLAUDE.md (+ son prompt ≈ 2,5-3 Ko, +≈ 600 o de bloc Sobriété).
Skills préchargés inchangés : ingenieur-etl 18,7 Ko (projet-conventions + insee-duckdb-loader),
developpeur-ui 8,1 Ko.

Ordres de grandeur pour une vague « directeur + 8 agents » :
- CLAUDE.md allégé : 9 × ≈ 3 300 t ≈ **30 000 tokens de contexte initial en moins**, relus
  (au tarif cache) à chaque tour de chaque agent.
- verificateur-code : −≈ 4 800 t par lancement (plus de relecture explicite de CLAUDE.md,
  déjà injecté), et −(taille du dernier rapport) si celui-ci n'est pas cité.
- Réponses finales ≤ 15 lignes : le directeur lit ≈ 1 Ko par agent au lieu de comptes rendus
  de plusieurs Ko ; lecture des rapports via index + résumé exécutif (les 5 plus gros rapports
  font 31 à 48 Ko, soit 9 000 à 14 000 tokens chacun s'ils sont lus en entier).
- Sonnet sur 4 agents d'exécution : coût unitaire inférieur (non chiffré, cf. § 1).

## 3. Fichiers créés ou modifiés

| Fichier | Changement |
|---|---|
| `.claude/skills/{canvas-design,frontend-design,skill-creator}/SKILL.md` | `disable-model-invocation: true` |
| `.claude/skills/code-review-excellence/SKILL.md` | description courte en français, `disable-model-invocation: true`, tableau réduit à Python et CSS |
| `.claude/skills/code-review-excellence/` | supprimés : `reference/{react,vue,angular,svelte,rust,typescript,django,java,csharp,go,kotlin,nestjs,c,cpp,qt}.md`, `README.md`, `CONTRIBUTING.md` (LICENSE conservée) |
| `.claude/skills/{projet-conventions,insee-duckdb-loader,streamlit-duckdb-patterns,latex-rapport-fr}/SKILL.md` | description raccourcie, entre guillemets ; corps inchangé |
| `.claude/skills/data-viz-politique/SKILL.md` | **non modifié** (consigne : classements) |
| `.claude/skills/economie-tokens/SKILL.md` | **nouveau** (54 lignes) |
| `.claude/agents/*.md` (8) | bloc Sobriété + format de réponse ; `model: sonnet` sur 4 agents ; verificateur-code : étape « Lis CLAUDE.md » remplacée |
| `.claude/settings.json` | `permissions.allow` / `permissions.ask` |
| `reports/README.md` | **nouveau** : index + convention de rapport |
| `reports/claude-md-allege-propose.md` | **nouveau** : proposition CLAUDE.md, diff commenté, règles `.claude/rules/` |

## 4. Choix de modèle par agent

| Agent | Modèle | Justification |
|---|---|---|
| verificateur-code | hérité | Détection de bugs de données (jointures, codes INSEE, SQL) : un faux négatif coûte plus cher que les tokens. |
| chercheur-donnees | hérité | Traçabilité juridique (NOR, extraits mot pour mot), classements politiques. |
| ingenieur-etl | hérité | Schémas, idempotence, classements nuance → bloc. |
| architecte-restructuration | hérité | Plans de refactor transverses, raisonnement multi-fichiers. |
| documentaliste | sonnet | Rédaction et vérification de chiffres dans le code ; méthode déjà très cadrée par le prompt. |
| developpeur-ui | sonnet | Code Streamlit/Plotly courant ; la validation visuelle reste à Mathias. |
| ingenieur-infra | sonnet | Scripts, CI, Dockerfiles ; changements structurants déjà soumis à décision. |
| outilleur-claude | sonnet | Fichiers de configuration, vérifiés par la doc officielle. |

Haiku n'est affecté à aucun agent : aucun rôle actuel n'est purement mécanique (tous
vérifient des faits dans le code). Le directeur peut revenir à `inherit` en une ligne.

## 5. Permissions

Ajoutées (lecture/vérification, sans effet de bord hors `.pytest_cache`/`.ruff_cache`) :
`Bash(uv run pytest[ *])`, `Bash(uv run ruff check[ *])`, `Bash(uv run ruff format --check[ *])`.
Garde-fous `ask` (priment sur `allow`) : `ruff check … --fix`, `… --add-noqa` (écrivent dans
les sources), `pytest … --basetemp` (vide le dossier cible). Non ajoutées car déjà en lecture
seule par défaut : `git status/log/diff/show`, `ls`, `grep`, `cat`, `head`, `wc`.
Note doc : les règles `allow` d'un `settings.json` de projet ne s'appliquent qu'après
confiance accordée au dossier.

## 6. Tests effectués

| Test | Résultat |
|---|---|
| `python3 -m json.tool .claude/settings.json` | OK |
| `bash -n .claude/hooks/session-start.sh` | OK |
| Hook avec `CLAUDE_CODE_REMOTE=false` | rc 0, aucune sortie |
| Hook avec `CLAUDE_CODE_REMOTE=true` | rc 0, aucune sortie (silencieux, idempotent) |
| Frontmatter YAML des 8 agents et 10 skills (`yaml.safe_load`) | OK après mise entre guillemets (4 échecs avant, préexistants) |
| Liens `reference/*.md` de code-review-excellence | tous présents |
| Comptage agents | 44 à 56 lignes (≤ 60) |

Non testable ici : chargement effectif par Claude Code (à voir avec `/context` et `/agents`
dans la prochaine session : descriptions des skills tiers absentes, agents avec modèle).

## 7. Fichiers volumineux

| Fichier | Taille | Risque | Mécanisme proposé |
|---|---:|---|---|
| `uv.lock` | 302 Ko (≈ 80 000 t) | lecture entière par erreur | consigne `economie-tokens` (grep) ; option D3 : deny `Read(./uv.lock)` |
| PDF `docs/sources-officielles/nuances/*.pdf`, `references/**/*.pdf` | 0,7 à 5 Mo | lecture de nombreuses pages | l'outil Read exige `pages` au-delà de 10 pages ; consigne dans le skill. Pas de deny : `chercheur-donnees` doit pouvoir citer ces textes. |
| Rapports > 20 Ko (`rd-feuille-de-route` 48 Ko, `catalogue-sources` 47 Ko, `audit-code` 37 Ko, `ux` 33 Ko, `verification-nuances` 31 Ko) | 31-48 Ko | relecture complète par le directeur | index + résumé exécutif ; ajouter a posteriori un résumé en tête de ces 5 rapports (tâche du documentaliste). |
| `.claude/skills/canvas-design/` | 5,5 Mo (polices TTF) | aucun token (jamais lu), poids du dépôt | D1 |

Un deny `Read` bloque aussi Edit/Write sur le chemin et ne couvre ni les sous-processus ni
`grep -r` sans nom de fichier (doc *permissions*) : il n'a pas été appliqué.

## 8. Décisions à soumettre (questions fermées)

- **D1** — Supprimer les skills tiers `canvas-design` (5,5 Mo de polices), `frontend-design`
  (orienté React/HTML, risque de conflit avec le design system) et `skill-creator` ? (oui / non /
  garder seulement skill-creator). Leur coût en tokens est déjà nul après ce commit.
- **D2** — `omitClaudeMd: true` pour `chercheur-donnees` (et éventuellement `verificateur-code`)
  en recopiant dans leur prompt les 5-6 règles utiles : ≈ 4 800 t (ou ≈ 1 500 t après
  allègement) économisés par lancement, au prix d'un risque d'oubli de règle. (oui / non)
- **D3** — Deny `Read(./uv.lock)` dans `settings.json` ? (oui / non ; recommandation : non,
  la consigne suffit)
- **D4** — Précharger `insee-duckdb-loader` dans `ingenieur-etl` seulement pour les tâches
  économie (retrait du préchargement, invocation à la demande : −6,8 Ko par lancement ETL
  hors économie) ? (oui / non)
- **D5** — Appliquer la proposition CLAUDE.md (`reports/claude-md-allege-propose.md`),
  y compris Q1 (gotcha `cache_resource` contraire au code) et Q2 (tableau des modules).

## 9. Mode d'emploi

- Directeur : charger `economie-tokens` avant une vague ; lire les réponses finales d'agent,
  puis `reports/README.md` et les résumés exécutifs ; demander un rapport complet seulement
  pour instruire une décision.
- Mathias : `/context` pour voir la répartition du contexte, `/usage` pour la consommation,
  `/clear` entre deux tâches sans lien.
- Skills tiers : `/code-review-excellence`, `/skill-creator`, `/frontend-design`,
  `/canvas-design` restent disponibles en invocation manuelle.
