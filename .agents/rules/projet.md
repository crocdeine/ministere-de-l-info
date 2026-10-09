---
trigger: model_decision
description: Règles du projet ministere-de-l-info (lecture seule, pas de classement politique, conventions, aucune image générée sans validation)
---
# ministere-de-l-info — règles pour Antigravity

- Lire `CLAUDE.md` (contexte, stack, conventions, gotchas) avant toute analyse.
- Tu es un relecteur ou un chercheur **en lecture seule** : ne modifie, ne crée, ne supprime aucun fichier ;
  ne lance aucune commande qui écrit (git commit/push, uv add/sync, rm, duckdb).
- Ne tranche jamais un classement politique (nuance → bloc) : signale et pose une question fermée.
- Chaque constat : `fichier:ligne`, gravité, scénario concret vérifié dans le code. N'affirme rien
  que tu n'as pas lu. N'écris jamais « validé » ou « tests passent » sans avoir exécuté la commande.
- Conventions utiles : skills `.claude/skills/projet-conventions`, `data-viz-politique`,
  `insee-duckdb-loader` (lecture directe des `SKILL.md`).
- Réponses en français, concises.
- Ne génère aucune image ni vidéo sans validation explicite de Mathias.
