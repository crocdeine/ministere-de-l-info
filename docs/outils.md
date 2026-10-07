# Outils de l'équipe d'agents

État vérifié le 2026-10-04 sur le Mac mini. Tous installés **globalement** (pas à l'échelle du projet) :
c'était déjà le cas avant cette session, rien n'a été réinstallé.

| Outil | Source retenue | Version | État | À quoi il sert | Quand l'utiliser |
|---|---|---|---|---|---|
| **agent-skills** | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT) — 24 skills dans `~/.agents/skills`, liées dans `~/.claude/skills` | lock `~/.agents/.skill-lock.json` | Installé, fonctionnel | Méthodes de développement : spec, plan, TDD, revue de code, ADR, sécurité, débogage | Début de tâche (`using-agent-skills`), avant fusion (`code-review-and-quality`), ADR (`documentation-and-adrs`) |
| **ponytail** | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (MIT) | 4.10.0 (commit e3ba2aa, 2026-09-14) | Installé, actif à chaque session (hook) | Discipline « le moins de code possible » : réutiliser l'existant, pas d'abstraction inutile | En permanence ; `ponytail-review` / `ponytail-debt` pour l'audit de dette |
| **graphify** | [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) (paquet PyPI `graphifyy`) | 0.9.72 | Installé, fonctionnel. Graphe du code construit le 2026-10-04 dans `graphify-out/` (636 nœuds, 1361 liens, 32 communautés) | Carte du code : qui appelle quoi, modules centraux | Avant toute modification : `graphify query "<question>"` ; après modification : `graphify update .` (local, gratuit) |
| **omniroute** | [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) (MIT, npm `omniroute`) | 3.8.51 | Installé, serveur **en marche** (port 20128). Configuration des fournisseurs : non vérifiée (relève du compte de Mathias) | Passerelle vers d'autres modèles d'IA quand l'abonnement Claude est limité | Uniquement tâches non critiques (voir `docs/modeles.md`) |

## Points d'attention

- **graphify** : la sortie est dans `graphify-out/`, exclue par `.gitignore` et `.dockerignore`
  (vérifié le 2026-10-07). Le libellé des communautés (`cluster-only`) a consommé ~52 000
  jetons d'un modèle : utiliser `graphify update .` (sans modèle) pour les mises à jour courantes.
- **omniroute** :
  - le serveur écoute sur **toutes les interfaces réseau** (`*:20128`), donc visible des autres appareils du
    réseau local. À restreindre à `127.0.0.1` ou à protéger par mot de passe (action de Mathias, voir ci-dessous).
  - Claude Code ne peut pas « basculer tout seul » vers omniroute en cours de session : il faut relancer
    Claude Code en le pointant vers omniroute (`omniroute run claude --model <modèle>`).
  - Les fournisseurs gratuits reçoivent le code et les prompts envoyés : ne jamais leur confier de secrets
    ni de tâches critiques (architecture, neutralité, conformité juridique, validation des données).
  - Faire transiter un abonnement Claude par un routeur tiers peut contrevenir aux conditions d'utilisation
    d'Anthropic : préférer des clés API ou des fournisseurs explicitement autorisés.

### Étapes pour Mathias (omniroute)

1. Ouvrir le tableau de bord : `http://localhost:20128` ; définir un mot de passe s'il n'y en a pas.
2. Y connecter les fournisseurs souhaités (comptes et clés : à faire soi-même, jamais par Claude).
3. Pour travailler via omniroute : `omniroute run claude --model <modèle>` dans le dossier du projet.

### Antigravity (repli utilisé le 2026-10-04)

- Antigravity CLI 1.1.10 (Google), compte de Mathias, modèle Gemini 3.1 Pro. Utilisé quand
  omniroute n'a pas fonctionné. Il lit `CLAUDE.md` et `docs/reprise.md`.
- Constat : il a déclaré une relecture « validée » sans exécuter de tests. **Ne pas lui confier de
  validation** ; le limiter à la documentation et au rangement (règles de `docs/reprise.md`).

## Outils projet déjà présents

- Skills projet (`.claude/skills/`, relevé du 2026-10-07) : `canvas-design`, `code-review-excellence`,
  `data-viz-politique`, `design-system-mi` (design system v2, ADR-0014), `economie-tokens`,
  `frontend-design`, `insee-duckdb-loader`, `latex-rapport-fr`, `projet-conventions`, `skill-creator`,
  `streamlit-duckdb-patterns`.
- Commande projet (`.claude/commands/`) : `verifier-nuances-2008-2014`. Hook : `.claude/hooks/session-start.sh`.
- Agents projet (`.claude/agents/`) : voir `docs/equipe.md`.
- Autres plugins actifs sur la machine : caveman (réponses concises), ruflo/claude-flow (non utilisé ici).

## Outils ajoutés

| Date | Outil | Source | Raison |
|---|---|---|---|
| — | aucun ajout en Phase 0 | — | — |
| 2026-10-04 (J1) | **gitleaks** (hook pre-commit) + `detect-private-key` | `.pre-commit-config.yaml` | Détection de secrets, exigée par les contraintes |
| 2026-10-06 | **pyright 1.1.408** (`uvx`, job CI bloquant) | `.github/workflows/ci.yml`, `[tool.pyright]` | Typage vérifié, 0 erreur |
| 2026-10-07 (A1) | **tippecanoe 2.79.0** (felt, licence BSD-2) | compilé depuis les sources (`make`, ≈ 1 min, sqlite3 et zlib du système) dans `/Volumes/le gros stockage/outils/tippecanoe-src` ; en CI : commit `68ab8dcc` compilé puis mis en cache | Tuiles vectorielles PMTiles des communes (`scripts/export_web.py`, ADR-0015, prototype A0) |
| 2026-10-07 (A1) | **Playwright** (`playwright-core` 1.63, WebKit 26.6) | dépendance de développement de `web/` ; navigateurs dans `/Volumes/le gros stockage/outils/playwright-navigateurs` (`PLAYWRIGHT_BROWSERS_PATH`) | Test de fumée et mesures de performance (`web/perf/mesure.mjs`) |
