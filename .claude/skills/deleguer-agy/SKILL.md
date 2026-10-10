---
name: deleguer-agy
description: Délègue une mission bornée à Google Antigravity (agy) pour économiser les jetons Claude. À charger avant de lancer scripts/agy_deleguer.sh ou de décider si une tâche se délègue (relecture, recherche de code, analyse de sources, brouillons de doc).
---

# Déléguer à Antigravity (agy)

Principe : agy produit des brouillons et des constats, jamais un verdict. Matrice complète :
`reports/brainstorm-antigravity-2026-10-07.md` § 2.

## Quand déléguer
- Oui : relecture de diff en 2e avis, recherche de code, analyse de sources (schéma, licence), brouillon de doc.
- Sous conditions (worktree + relecture complète) : tests pytest, correctif borné.
- **Non** : classement politique, base DuckDB / `data/`, git (commit, push, tags), CI, ADR / CLAUDE.md, secrets.
- Si la vérification coûte plus de 50 % d'une exécution directe, ne pas déléguer.

## Lancer
```bash
scripts/agy_deleguer.sh <modele> <fichier-mission.md>
```
Le script impose `--mode plan --sandbox --output-format json`, un délai de 900 s, une sortie bornée et
journalise dans `logs/agy-delegations.csv` (date ; mission ; modèle ; jetons ; statut). Jamais
`--dangerously-skip-permissions`. Lancer depuis un worktree, pas de commit ni d'écriture hors worktree.

## Gabarit de mission
Objet précis (1 phrase) · fichiers ou dossiers concernés · livrable attendu (format, longueur) ·
« Lecture seule. Cite `fichier:ligne` pour chaque constat. Liste les commandes exécutées et leur
résultat ; n'écris jamais « validé » sans exécution. Ne tranche aucun classement : pose une question fermée. »

## Modèle
- Recherche de code, reformulation : `gemini-3.8-flash-low` (ou medium).
- Sources, documentation : `gemini-3.8-flash-high`.
- Relecture, tests : `gemini-3.1-pro-high` (quota limité : réserver aux cas qui le justifient).
Lister les identifiants valides : `agy models`.

## Vérification par le directeur (obligatoire)
1. `status=SUCCESS`, sinon relancer ou abandonner.
2. Chaque affirmation est vérifiée au `fichier:ligne` cité (`sed -n`, `git show`) avant d'être reprise.
3. Pour du code : `uv run ruff check` et `uv run pytest -q` exécutés par le directeur.
4. Une absence de constat ne vaut pas validation.
