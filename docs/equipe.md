# Équipe d'agents

Le directeur de projet (Claude Code, session principale) joue le rôle de **chef de produit** : il traduit
les demandes de Mathias en tâches, évalue leur faisabilité, répartit le travail et valide les résultats.
Mathias fixe les orientations et tranche les décisions structurantes (voir `CLAUDE.md`, section Gouvernance).

## Rôles → agents

Les rôles demandés sont tenus par les agents déjà définis dans `.claude/agents/` (pas de doublon créé).

| Rôle | Agent | Modifie des fichiers ? |
|---|---|---|
| Chef de produit, arbitrages, synthèse | directeur (session principale) | oui, après relecture |
| Architecte | `architecte-restructuration` | oui, en worktree isolé |
| Ingénieur données (pipelines, sources) | `ingenieur-etl` (code) + `chercheur-donnees` (sources) | ETL : oui en worktree ; recherche : rapports seulement |
| Spécialiste Streamlit / UI / design system | `developpeur-ui` | oui, en worktree isolé |
| QA / tests | `verificateur-code` (lecture seule, exécute ruff/pytest) | non |
| Responsable conformité (licences, RGPD, neutralité) | `chercheur-donnees` (licences) + relecteur de neutralité (agent généraliste, modèle le plus puissant) | non |
| Relecteur de code | `verificateur-code` ou skill `code-review-and-quality` | non |
| Documentaliste | `documentaliste` | docs seulement |
| Infrastructure (Docker, CI, installeur) | `ingenieur-infra` | oui, en worktree isolé |
| Outillage Claude Code | `outilleur-claude` | `.claude/` seulement |

## Circulation du travail

1. Le directeur écrit une consigne fermée (objectif, périmètre, fichiers, critères de réussite).
2. L'agent exécutant travaille **en worktree isolé**, ne pousse jamais, rend un rapport court.
3. **Aucun agent ne valide son propre travail** : un second agent (en général `verificateur-code`) relit le
   diff, relance ruff et pytest, et rapporte les constats.
4. Le directeur relit, vérifie lui-même les points incertains (commande ou `fichier:ligne`), fusionne dans
   la branche de travail. Fusion dans `main`, push et publication : seulement avec l'accord de Mathias.
5. Les questions de fond (classement politique, périmètre, source, architecture) remontent à Mathias sous
   forme de questions fermées, regroupées.
6. Chaque vague se termine par un rapport dans `reports/` et une entrée dans `docs/journal.md`.
