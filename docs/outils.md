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

- **graphify** : la sortie est dans `graphify-out/` (exclue localement via `.git/info/exclude`). À ajouter à
  `.gitignore` et `.dockerignore` en Phase 1. Le libellé des communautés (`cluster-only`) a consommé ~52 000
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

## Outils projet déjà présents

- Skills projet (`.claude/skills/`) : `data-viz-politique`, `economie-tokens`, `insee-duckdb-loader`,
  `latex-rapport-fr`, `projet-conventions`, `streamlit-duckdb-patterns`, `verifier-nuances-2008-2014`.
- Agents projet (`.claude/agents/`) : voir `docs/equipe.md`.
- Autres plugins actifs sur la machine : caveman (réponses concises), ruflo/claude-flow (non utilisé ici).

## Outils ajoutés

| Date | Outil | Source | Raison |
|---|---|---|---|
| — | aucun ajout en Phase 0 | — | — |

Proposé pour Phase 1 (dans les critères, sans compte ni paiement) : **gitleaks** via pre-commit
(détection de secrets, exigée par les contraintes).
