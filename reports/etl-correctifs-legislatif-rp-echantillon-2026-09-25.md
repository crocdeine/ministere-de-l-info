# ETL — correctifs Législatif (périmètre Sénat), RP 2015-2016, échantillon (2026-09-25)

## Résumé exécutif

1. Législatif : 16 sigles de groupes du Sénat disparus avant le renouvellement de 2002 (RPR, RI, UNR…) : les anciens sénateurs concernés sont écartés au chargement (INFO), sans bloc.
2. Élus au groupe vide : statut « sans groupe » (NULL, INFO), exclus du contrôle de complétude mais comptés.
3. `test_aucun_mandat_non_classe` ne porte plus que sur le périmètre ; tout groupe inconnu reste signalé.
4. RP 2015-2016 : bug du drapeau `secret` (clef chômage sans valeur pour tout le millésime → 100 % des communes secrètes).
5. Correctif : secret seulement si la clef est diffusée ailleurs dans le millésime ; WARNING de diagnostic des clefs.
6. UI : seuls les millésimes où l'indicateur a au moins une valeur sont proposés (requête modifiée, pages intactes).
7. Cause racine du chômage NULL (clef absente ou renommée dans la source) : non vérifiable hors ligne, le WARNING l'identifiera sur le Mac.
8. Échantillon : `leg_mandats` et `leg_groupes_blocs` ajoutés à l'export, dérivés par la migration 0008 à la reconstruction si absents.
9. Liste des groupes historiques issue de la connaissance générale (senat.fr inaccessible) : à confirmer.
10. `uv run pytest -q` : 218 réussis, 372 ignorés ; ruff OK.

## Sources

- ODSEN_GENERAL (data.senat.fr), Datan (data.gouv.fr) : inchangées.
- Parquet OLAP INSEE RP (cache `data/raw/economie/donnees-insee-olap-hdf.parquet`) : inchangé.

## Volumétrie attendue (Mac)

- Sénat : environ 569 mandats en moins (anciens groupes), à ajuster si des sigles ne sont pas dans la liste.
- AN : 3 mandats « sans groupe » (XVe législature), aucun actif.
- `economie_rp` : même nombre de lignes ; en 2015-2016, `secret` = 0 si la clef est absente, sinon quelques communes seulement.

## Commandes Mac

```bash
uv run python scripts/load_legislatif.py --source senat
uv run python scripts/load_economie.py --source rp --millesimes 2015,2016
uv run pytest tests/test_legislatif.py tests/test_economie.py -q
uv run python scripts/export_sample_db.py
```

## Requêtes de contrôle

```sql
-- Clefs chômage par millésime dans le cache (identifier une clef renommée)
SELECT annee, clef_json, COUNT(valeur) FROM read_parquet('data/raw/economie/donnees-insee-olap-hdf.parquet')
WHERE source = 'rp_actifs_emploi' AND (clef_json ILIKE '%chom%' OR clef_json ILIKE 'actifs_15_64%')
GROUP BY ALL ORDER BY ALL;
-- RP par millésime
SELECT annee_millesime, COUNT(*), COUNT(tx_chomage_dec), COUNT(*) FILTER (WHERE secret)
FROM economie_rp GROUP BY 1 ORDER BY 1;
-- Législatif : 0 ligne attendue
SELECT chambre, groupe_sigle, legislature, COUNT(*) FROM v_mandats_legislatif
WHERE bloc_groupe IS NULL AND groupe_sigle IS NOT NULL GROUP BY ALL ORDER BY 4 DESC;
```

## Questions fermées

1. Si le cache contient une autre clef de chômeurs pour 2015-2016 (par exemple `chomeurs_15_64_ans_c`), l'utiliser pour ces millésimes malgré le mélange d'exploitations principale/complémentaire ? — oui / non
2. Liste des groupes antérieurs à 2002 (addendum ADR-0011) validée en l'état, sous réserve de vérification sur senat.fr ? — oui / non
