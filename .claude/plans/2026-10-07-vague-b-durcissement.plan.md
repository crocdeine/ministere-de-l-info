# Mission : vague B — durcissement avant application à la base réelle

**Agent** : ingenieur-etl · **Branche** : feat/elections-france-entiere · **Base** : c7e6867
**Décision d'origine** : relectures `ecc:python-reviewer` et `ecc:silent-failure-hunter` du 2026-10-07
**Complexité** : S

## Objectif
Supprimer les échecs silencieux trouvés par les relecteurs, pour que la base réelle ne puisse pas
recevoir de chiffres faux sans alerte.

## Hors périmètre
Le rattachement des communes fusionnées aux communes actuelles (table de passage COG) : décision de
Mathias en attente, ne pas le coder.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Contrôle bloquant | `verifier_unicite_resultats` (vague B) | requête de contrôle → `RuntimeError` explicite |
| Journalisation | `logging.getLogger(__name__)` des loaders | `logger.warning` chiffré par scrutin |
| Périmètre HdF | `_HDF_DEPTS_SQL` (modules viz) | une seule définition réutilisée |

## Tâches
### 1. Migration 0009 sûre
- **Action** : `COUNT(*)` avant la copie et après le `RENAME`, `RuntimeError` avant `COMMIT` si écart ;
  recréer en fin de migration les vues dépendantes (`create_elections_views` et les vues municipales
  de la migration 0007 — déplacer leur définition dans `schema_elections` si c'est le plus simple).
- **Valider** : test qui applique 0009 sur une base en mémoire contenant un département hors HdF puis
  interroge `v_evolution_blocs_hdf_legi` et `v_evolution_blocs_hdf_muni` (totaux = HdF seuls).

### 2. Communes écartées signalées
- **Action** : dans les 4 loaders, compter par scrutin les lignes et exprimés non rattachés à
  `geographies_communes` (en distinguant étranger `ZZ`, Pacifique `98`, et reste) ;
  `logger.warning` avec chiffres ; erreur si le « reste » dépasse 3 % des exprimés d'un scrutin.
  Écrire ces chiffres dans une table `elections_ecarts_chargement` (id_election, categorie,
  nb_communes, exprimes) pour pouvoir l'afficher plus tard.
- **Valider** : test sur fixture avec une commune absente du COG.

### 3. Contrôle somme des voix = exprimés
- **Action** : hors municipales, compter les bureaux où `sum(voix) <> exprimes` ; `logger.warning`
  avec les 5 pires écarts ; documenter le cas 2009_euro (no_panneau NULL) dans le rapport.
- **Valider** : test sur fixture.

### 4. Périmètre HdF centralisé
- **Action** : une seule constante (module commun) réutilisée par `economie_queries.py`,
  `schema_elections.py`, viz.
- **Valider** : `grep -rn "'02', *'59'" src scripts` ne renvoie que la définition.

### 5. Documentation
- **Action** : `docs/schema-elections.md` : nuance NULL des municipales 2026 (49 637 lignes,
  « non classé »), communes écartées (table de contrôle), contrôle voix/exprimés ; rapport mis à jour.

## Contraintes du projet
- Base : copie `/Volumes/le gros stockage/outils/tmp/ministere-vagueB.duckdb` uniquement.
- `UV_CACHE_DIR` et `TMPDIR` sur le disque externe.
- Commits tôt et souvent ; ne jamais pousser.
- Réflexe documentation (table de `CLAUDE.md`).

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest -m "not slow and not network"
MINISTERE_DB_PATH="/Volumes/le gros stockage/outils/tmp/ministere-vagueB.duckdb" uv run pytest -q
```
Puis rejouer la séquence complète de chargement sur la copie et donner les chiffres d'écarts par scrutin.

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Seuil de 3 % bloquant un scrutin ancien légitime | moyenne | chiffres mesurés dans le rapport ; seuil ajustable par constante |
| Vues municipales oubliées après déplacement | faible | test de la tâche 1 |

## Acceptation
- [ ] Tâches 1 à 5 faites, validation verte
- [ ] Tableau des écarts par scrutin (communes, exprimés, %) dans le rapport
- [ ] Commandes de la base réelle mises à jour (§ 7 du rapport)
