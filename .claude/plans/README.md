# Fiches de mission

Avant de lancer un agent qui **modifie du code ou la base** (hors correctif d'une ligne), le directeur
écrit ici une fiche `AAAA-MM-JJ-nom.plan.md` et la commite. L'agent la lit en premier ; le prompt de
lancement se limite à « exécute `.claude/plans/<fiche>` ». Une mission interrompue (limite d'usage,
coupure) reprend depuis la fiche, sans dépendre de la conversation.

Format repris de `/ecc:plan` (plugin ECC) et complété par les règles du projet (décision du
2026-10-07, voir `docs/orientations.md`).

## Modèle

```markdown
# Mission : {nom}

**Agent** : {type} · **Branche** : {branche} · **Base** : origin/main {sha}
**Décision d'origine** : {lien orientations.md / rapport} · **Complexité** : S | M | L

## Objectif
{2-3 phrases : quoi et pourquoi, pour l'utilisateur final}

## Hors périmètre
{ce que l'agent ne doit pas faire}

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Nommage | `chemin:ligne` | … |
| Erreurs / journalisation | `chemin:ligne` | … |
| Accès aux données | `chemin:ligne` | … |
| Tests | `chemin:ligne` | … |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|

## Tâches
### 1. {nom}
- **Action** : …
- **Valider** : {commande qui prouve le résultat}

## Contraintes du projet
- Base : copie dans `/Volumes/le gros stockage/outils/tmp/`, jamais la base réelle.
- Disque interne : caches et fichiers temporaires sur le disque externe.
- Commits tôt et souvent (WIP accepté) ; ne jamais pousser.
- Aucune décision structurante ou de classement politique : questions fermées.
- Réflexe documentation (table de `CLAUDE.md`).

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check .
uvx pyright@1.1.408
uv run pytest -m "not slow and not network"
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|

## Acceptation
- [ ] Tâches faites, validation verte
- [ ] Motifs reproduits, pas réinventés
- [ ] Documentation à jour
- [ ] Questions fermées listées pour Mathias
- [ ] Rapport `reports/…` (résumé ≤ 10 lignes)
```
