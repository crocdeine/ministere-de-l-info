# Mission : pont de délégation Claude Code → Antigravity

**Agent** : ingenieur-infra · **Branche** : chore/pont-antigravity · **Base** : origin/main
**Décision d'origine** : Mathias, 2026-10-09 (« oui à tout » sur `reports/recherche-ruflo-antigravity-2026-10-09.md` § 7) :
pas de Ruflo ; script + skill ; règle agy corrigée, `AGENTS.md`, skills partagés ; test d'import avec
sauvegarde ; aucune image générée sans validation. Abonnement Google AI Pro.
**Complexité** : S

## Tâches (plan du rapport, § 7, étapes 1 à 4)
### 1. Règle et AGENTS.md
- Frontmatter `trigger: model_decision` + `description` en tête de `.agents/rules/projet.md` ; ajouter
  à cette règle : « aucune image générée sans validation de Mathias ». `AGENTS.md` (≤ 15 lignes) à la
  racine : renvoi vers `CLAUDE.md`, `.claude/skills/`, règles de lecture seule et de neutralité.
- **Valider** : `agy -p "Quelles règles et quel fichier AGENTS.md vois-tu ? Réponds en 5 lignes" --model gemini-3.8-flash-low --mode plan` cite la règle.
### 2. Skills partagés
- Liens `.agents/skills/<s> → ../../.claude/skills/<s>` pour projet-conventions, data-viz-politique,
  economie-tokens, insee-duckdb-loader, streamlit-duckdb-patterns, design-system-mi.
- **Valider** : `agy -p "Liste tes skills (noms seulement), sans appeler d'outil" --mode plan --model gemini-3.8-flash-low`.
  Si les liens ne sont pas suivis : `scripts/sync-skills-agy.sh` (rsync) et le documenter.
### 3. Script et skill de délégation
- `scripts/agy_deleguer.sh <modele> <fichier-mission>` : `agy -p` en `--mode plan --sandbox
  --output-format json --print-timeout 600s`, délai maximal, sortie bornée, journal
  `logs/agy-delegations.csv` (date ; mission ; modèle ; jetons ; statut) ignoré par git.
  **Jamais** `--dangerously-skip-permissions`.
- Skill `.claude/skills/deleguer-agy/SKILL.md` (≈ 40 lignes) : quand déléguer (matrice de
  `reports/brainstorm-antigravity-2026-10-07.md`), gabarit de mission, choix du modèle, règle « chaque
  affirmation vérifiée au fichier:ligne par le directeur », pas de commit ni d'écriture hors worktree.
- **Valider** : `shellcheck` (via `uvx --from shellcheck-py shellcheck`) ; une mission triviale réelle.
### 4. Test d'import des plugins Claude
- Sauvegarder `~/.gemini/antigravity-cli/` (`cp -R` vers
  `/Volumes/le gros stockage/ministere-de-l-info-backups/antigravity-cli-2026-10-09/`), lancer
  `agy plugin import claude`, `agy plugin list` ; noter ce qui est importé et le coût (taille du
  contexte : `agy -p "/usage"` avant/après si lisible). Si l'import est bruyant (ECC entier…) :
  `agy plugin uninstall` et restaurer la sauvegarde. Consigner le résultat.
### 5. Documentation
- `docs/outils.md` (section Antigravity), skill `economie-tokens` (renvoi vers `deleguer-agy`),
  `docs/lessons-learned.md` (règle ignorée sans frontmatter).

## Hors périmètre
Aucun serveur MCP ; aucune modification des réglages de permissions d'agy (liste minimale du
2026-10-07) sauf ajout strictement nécessaire, justifié dans le rapport ; aucune image générée.

## Contraintes
Disque externe (`TMPDIR`, `UV_CACHE_DIR`) ; contrôle d'espace disque ; commits atomiques ; ne pousse pas.

## Acceptation
- [ ] agy voit la règle, AGENTS.md et les skills (sorties citées dans le rapport)
- [ ] Script et skill testés sur une mission réelle, journal écrit
- [ ] Résultat du test d'import consigné, configuration propre
- [ ] Rapport `reports/infra-pont-antigravity-2026-10-09.md` (résumé ≤ 10 lignes)
