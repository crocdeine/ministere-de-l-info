# Mission : rattacher les résultats des communes fusionnées aux communes actuelles

**Agent** : ingenieur-etl · **Branche** : feat/elections-france-entiere (après la fiche « durcissement »)
**Décision d'origine** : Mathias, 2026-10-07 (« ok continue » sur la proposition du directeur)
**Complexité** : M

## Objectif
Les résultats d'une commune disparue par fusion (ex. Annecy-le-Vieux 2012) sont aujourd'hui écartés
au chargement (jusqu'à 2,4 % des exprimés France en 2012, 0,77 % en HdF 2002). Les rattacher à la
commune actuelle qui l'a absorbée, selon la source officielle INSEE, pour que les séries
communales soient complètes et les totaux justes.

## Hors périmètre
- Scissions de communes (rétablissements) : les signaler et les compter, ne pas répartir de voix.
- Interface : seule une colonne/mention de traçabilité en base ; l'affichage viendra en vague A.

## Source
INSEE, Code officiel géographique : « table de passage » ou fichier des **mouvements des
communes** (`mvtcommune`) du millésime correspondant à `geographies_communes`. Licence Ouverte 2.0.
Vérifier l'URL et la licence sur la page officielle ; ajouter la source à
`src/ministere_de_l_info/sources.py`, `docs/sources.md`, `docs/data-sources.md`.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Téléchargement contrôlé | `legislatif_senat._download_cache` | fichier temporaire, contrôle du contenu, puis remplacement |
| Contrôle bloquant | `verifier_unicite_resultats` | `RuntimeError` explicite |
| Écarts | table `elections_ecarts_chargement` (fiche durcissement) | catégories chiffrées |

## Tâches
### 1. Table de correspondance
- **Action** : table `communes_passage (code_ancien, code_actuel, date_effet, type_evenement)`
  construite depuis la source ; chaînes de fusions successives résolues jusqu'au code actuel.
- **Valider** : test sur fixture avec une fusion en deux étapes.

### 2. Chargement
- **Action** : dans les loaders, remplacer le code commune absent du COG courant par son
  `code_actuel` avant agrégation ; conserver le code d'origine dans une colonne
  `code_commune_origine` (NULL si inchangé). Les bureaux gardent leur code BV d'origine
  préfixé si collision.
- **Valider** : après rechargement de la copie, la catégorie « reste » de
  `elections_ecarts_chargement` tombe à ≈ 0 (hors étranger et Pacifique) ; total des exprimés
  France = total de la source à ± 0,01 %.

### 3. Documentation
- **Action** : `docs/schema-elections.md` (méthode, limites : géographie actuelle, scissions),
  ADR court ou addendum si le directeur le juge structurant (proposer, ne pas trancher).

## Contraintes du projet
Identiques à la fiche « durcissement » (copie de la base, disque externe, commits fréquents, ne pas pousser).

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest -m "not slow and not network"
MINISTERE_DB_PATH="/Volumes/le gros stockage/outils/tmp/ministere-vagueB.duckdb" uv run pytest -q
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Collision de numéros de bureau après fusion | moyenne | préfixe du code d'origine |
| Commune rétablie (scission) | faible | comptée à part, non répartie |
| Totaux HdF modifiés (hausse attendue de 0,06 à 0,77 %) | certaine | chiffres avant/après dans le rapport |

## Acceptation
- [ ] Écarts « reste » ≈ 0, tableau avant/après par scrutin dans le rapport
- [ ] Source enregistrée avec licence vérifiée
- [ ] Tests et documentation à jour
