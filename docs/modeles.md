# Modèles et quotas

| Usage | Modèle | Exemples |
|---|---|---|
| Architecture, arbitrages, relecture critique, neutralité, conformité juridique, validation finale des données | **Claude Opus** (le plus puissant) | directeur, audit de neutralité, audit des licences |
| Implémentation courante | **Claude Sonnet** | `developpeur-ui`, `ingenieur-infra`, `documentaliste`, `outilleur-claude`, `verificateur-code` |
| Tâches répétitives (recherches simples, reformatage, inventaires) | **Claude Haiku** | balayages de fichiers |
| Repli hors Claude via omniroute | selon fournisseurs connectés | uniquement tâches non critiques ; jamais de secrets |

Règles :
- Tâches critiques (architecture, neutralité, conformité, validation des données) : jamais confiées à un
  modèle plus faible ou non vérifié. Si seul un tel modèle est disponible, elles sont **mises en attente**.
- Lectures volumineuses déléguées à des sous-agents ; `/compact` entre les grosses tâches.
- Aucun secret transmis à un modèle ou service tiers. Aucun compte créé, aucune option payante activée.
- Limite pratique : Claude Code ne change pas de fournisseur en cours de session. La bascule vers omniroute
  consiste à relancer Claude Code via `omniroute run claude` (voir `docs/outils.md`).

## Journal des bascules

| Date | De → vers | Raison |
|---|---|---|
| — | aucune | — |
