# Pont de délégation Claude Code -> Antigravity (2026-10-09)

## Résumé exécutif
- Règle `.agents/rules/projet.md` corrigée (frontmatter `model_decision`) + `AGENTS.md` : agy les voit.
- Skills du projet (6) exposés par liens symboliques `.agents/skills/` : suivis par agy 1.3.2.
- `scripts/agy_deleguer.sh` + skill `deleguer-agy` : testés sur une mission réelle, journal écrit, shellcheck propre.
- `agy plugin import claude` : « No claude extensions found », rien importé, configuration inchangée.
- Sauvegarde : `/Volumes/le gros stockage/ministere-de-l-info-backups/antigravity-cli-2026-10-09/` (38 Mo).
- Aucun réglage de permissions d'agy modifié, aucune image générée, rien poussé.
- Quota Gemini restant : 21 % (reset 2026-10-11).

## Résultats (sorties d'agy)
1. Règle/AGENTS.md : `agy -p "Quelles règles et quel fichier AGENTS.md vois-tu ?"` cite `AGENTS.md`, la
   règle `user_global` et « `.agents/rules/projet.md` (règles détaillées du projet) », et la consigne
   « aucune génération d'image/vidéo sans validation de Mathias ».
2. Skills : liste renvoyée = agy-customizations, antigravity-guide, data-viz-politique, design-system-mi,
   economie-tokens, insee-duckdb-loader, projet-conventions, streamlit-duckdb-patterns. Pas de repli rsync.
3. Mission réelle (flash-low, 47 899 jetons, SUCCESS) : « où est calculé le SHA256 ? » -> `sha256_of()`
   `scripts/publish_db.sh:33-39`, appel `:90`. Vérifié par lecture (ligne 90 exacte). Journal :
   `2026-10-09T22:44:33;m.md;gemini-3.8-flash-low;47899;SUCCESS`.
4. Import : `agy plugin import claude` -> « No claude extensions found » ; `agy plugin list` -> « No
   imported plugins ». Jetons d'un « OK » avant/après : 13 743 / 13 738 (aucun surcoût). settings.json
   identique à la sauvegarde. Pas de désinstallation ni restauration nécessaires.

## Changements
AGENTS.md, .agents/rules/projet.md, .agents/skills/* (6 liens), scripts/agy_deleguer.sh,
.claude/skills/deleguer-agy/SKILL.md, renvoi dans economie-tokens, docs/outils.md, docs/lessons-learned.md.

## Procédure de test pour Mathias
`scripts/agy_deleguer.sh gemini-3.8-flash-low <mission.md>` puis `cat logs/agy-delegations.csv`.

## Risques et limites
- Surcoût fixe ~13,7 k jetons par appel (prompt système) ; `/usage` non lisible finement avant/après.
- `timeout` absent de macOS : délai par `perl alarm` (portable) ; `--sandbox` non éprouvé sur une mission écrivante.
- Liens symboliques : Docker/Windows peuvent les casser (hors usage actuel).
- design-system-mi est volumineux (tokens, reference) : coût de chargement côté Gemini si invoqué.
- Les constats d'agy restent à vérifier au fichier:ligne (règle du skill).
