# Mission : vague B — correctifs issus des relectures (ECC + Antigravity)

**Agent** : ingenieur-etl · **Branche** : feat/elections-france-entiere · **Complexité** : S
**Origine** : relecture `ecc:silent-failure-hunter` et Antigravity du 2026-10-07, constats vérifiés
par le directeur.

## Tâches
### 1. Chargements atomiques (moyenne)
- **Action** : dans `elections_agregees.py` et les 3 `scripts/load_elections_*.py`, un seul
  `BEGIN` autour de DELETE + INSERT + contrôles (`verifier_unicite_resultats`, seuil 3 %, voix/exprimés),
  `ROLLBACK` sur exception, `COMMIT` sinon. Un contrôle qui échoue laisse la base dans son état antérieur.
- **Valider** : test qui provoque un doublon et vérifie que les anciennes lignes sont intactes.

### 2. Seuil contournable (moyenne)
- **Action** : erreur bloquante si `communes_passage` est vide (ou absente) lors d'un chargement
  `--perimetre france` ; borner aussi la catégorie `etranger` + `outremer_hors_referentiel`
  par un seuil large documenté (ex. 5 %) ; ne plus journaliser `rattachee` comme « écartée »
  (niveau info, libellé « rattachée à la commune actuelle »).
- **Valider** : test avec table de passage vide → erreur.

### 3. Listes municipales des communes absorbées (moyenne)
- **Action** : `v_listes_commune_muni` expose `code_commune_origine` (et le nom de la commune
  d'origine si disponible) ; `pct_exprimes` calculé sur les exprimés **de la commune d'origine**
  (CTE des exprimés groupée aussi par `code_commune_origine`, jointure `IS NOT DISTINCT FROM`) ;
  `get_listes_commune_muni` (`viz/elections_muni_queries.py`) et l'affichage du détail municipal
  indiquent la commune d'origine quand elle diffère (« liste de l'ancienne commune X »).
- **Valider** : pour chaque (commune, origine) la somme des `pct_exprimes` des listes ≈ 100 %
  (hors plurinominal) ; test sur fixture.

### 4. Commune rattachée hors région (faible)
- **Action** : documenter dans `docs/schema-elections.md` le cas 02344 → 51171 (circonscription
  du scrutin conservée, département de la commune actuelle) ; aucune correction de données.

## Hors périmètre
Faux positifs écartés par le directeur : DROP TABLE avec vues dépendantes (DuckDB l'accepte),
colonne `bloc` de `candidats_presidentielle` (existe).

## Contraintes
Copie `/Volumes/le gros stockage/outils/tmp/ministere-vagueB.duckdb` uniquement ; disque externe ;
commits fréquents ; ne pas pousser ; réflexe documentation.

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest -m "not slow and not network"
MINISTERE_DB_PATH="/Volumes/le gros stockage/outils/tmp/ministere-vagueB.duckdb" uv run pytest -q
```
Rejouer le chargement complet sur la copie ; donner taille, durée, tests.

## Acceptation
- [ ] 4 tâches faites, validation verte, rapport mis à jour (§ 7 commandes à jour)
