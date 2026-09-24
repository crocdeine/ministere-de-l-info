---
name: economie-tokens
description: Règles d'usage sobre du contexte pour le directeur et tous les agents de ministere-de-l-info (lecture ciblée, sorties filtrées, délégation, format de réponse et de rapport). À charger avant de lancer une vague d'agents ou de lire des rapports, gros fichiers ou sorties longues.
---

# Économie de tokens — règles communes

La sobriété ne dispense jamais d'une vérification : un chiffre, une table ou un classement
cité doit toujours être lu dans le code ou la source. On lit **moins**, pas **moins bien**.

## Lecture
- `CLAUDE.md` est déjà dans le contexte de chaque session et de chaque sous-agent : ne pas le relire.
- Chercher avant de lire : `Grep` (ou `grep -n`) pour localiser, puis `Read` avec `offset`/`limit`.
- Ne pas relire un fichier qu'on vient d'éditer ou de lire dans la même session.
- Rapports (`reports/`) : consulter d'abord `reports/README.md` (index), puis le résumé
  exécutif en tête du rapport (`head -n 20`). Lire la suite seulement pour la section utile.
- Ne jamais lire en entier : `uv.lock` (≈ 300 Ko ; `grep -n -A2 'name = "polars"' uv.lock`),
  les PDF de `docs/sources-officielles/` et `references/` (paramètre `pages`, quelques pages),
  les gros rapports (> 20 Ko : `audit-code`, `catalogue-sources`, `rd-feuille-de-route`,
  `ux`, `verification-nuances`), `data/` (jamais versionné).
- Résultats WebFetch volumineux : poser une question précise dans le `prompt` ; si la sortie
  est sauvegardée dans un fichier, la filtrer avec `grep`/`sed -n` plutôt que la relire.

## Commandes
- Tests : `uv run pytest <cible> -q` ; en cas d'échecs nombreux, `| tail -n 40`.
- Lint : `uv run ruff check <cible> --output-format concise`.
- Git : `git log --oneline -10`, `git diff --stat` avant tout `git diff` complet,
  `git show --stat <hash>`.
- Pas de `cat` sur un fichier long : `head`, `sed -n 'a,bp'`, `wc -l` d'abord.

## Délégation (directeur)
- Prompt d'agent précis : fichiers ou dossiers cibles, question, livrable attendu.
  Ne pas y recopier CLAUDE.md ni les règles déjà présentes dans la définition de l'agent.
- Lancer seulement les agents nécessaires ; un agent par sujet.
- Lire la réponse finale de l'agent ; n'ouvrir son rapport qu'en cas de doute ou de décision.

## Réponse finale d'un agent (≤ 15 lignes)
```
Statut : terminé | partiel | bloqué (raison)
Branche / commits : <branche> — <hash> <sujet>
Fichiers : <liste courte ou « voir rapport »>
Vérifications : <commande> → <résultat>
Décisions à soumettre : <questions fermées numérotées, ou « aucune »>
Rapport : reports/<fichier>.md
```

## Rapports
Chaque rapport commence par un **résumé exécutif de 10 lignes au plus** (constat, livrables,
décisions attendues), puis le détail. Ajouter une ligne à `reports/README.md`.

## Sessions (Mathias)
`/clear` entre deux tâches sans lien ; `/compact <consigne>` pour garder l'essentiel ;
`/context` pour voir ce qui occupe le contexte.
