# ETL — Élections France entière, européennes, régionales, départementales (vague B)

Date : 2026-10-06 (exécution 2026-10-07) — branche `feat/elections-france-entiere` — agent `ingenieur-etl`.

## Résumé exécutif (mis à jour le 2026-10-07, après les décisions de Mathias)

1. Mathias a validé toutes les propositions le 2026-10-07 (Q1 à Q11) ; les cas ambigus sont tranchés (§ 5 bis) ; addendum ADR-0010 rédigé.
2. Clés primaires retirées des tables de résultats (migration 0009) ; unicité contrôlée par les loaders (erreur si doublon).
3. Rejeu sur la copie : base **1 266 Mo compactée** (1 460 Mo avant compactage), **728 Mo en gzip** (contre 2,1 Go / 861 Mo avec clés primaires).
4. Voix non classées : 0 % sur tous les scrutins euro/regi/dpmt, sauf les européennes 2009 (11 voix : résidus LPC/LDD/LDV).
5. Temps : migration 0009 20 s, puis init 5 s, présidentielles 7 s, législatives 14 s, municipales 13 s, euro/regi/dpmt 14 s.
6. Tests : ruff OK ; 319 réussis en hermétique (363 ignorés faute de base) ; 681 réussis sur la copie France. pyright non exécuté (PyPI injoignable).

### Résumé initial (2026-10-06)


1. **Étude d'impact** : la France entière au bureau de vote (48 scrutins) = 2,87 M BV × scrutin et 26,0 M lignes candidats ; base 2,1 Go (921 Mo aujourd'hui), **0,86 Go compressée** (limite GitHub 2 Go : respectée). Le niveau commune hors HdF ne réduit le volume que de ~15 % : **recommandation BV partout** (à valider, Q1).
2. **Implémenté** : paramètre `--perimetre hdf|france` sur les 3 loaders existants (défaut `hdf`, comportement inchangé) + `scripts/load_elections_autres.py` (euro 1999-2024, régionales 2004-2021, départementales 2015-2021). Chargement complet ≈ 80 s.
3. **Non-régression HdF** : chargement France puis comparaison des agrégats HdF (participation, voix, blocs, vues d'évolution, croisement économie) : identiques, sauf le correctif ci-dessous.
4. **Correctif** (bug existant) : circonscription reconstruite (législatives 2002/2007/2024) cherchée dans le département de la commune. 3 communes HdF changent de circonscription (Coyolles, Haramont : de l'Oise vers 02-05 ; Forest-sur-Marque : sans circo → 59-02).
5. **Nuances** : 149 codes nuance × année + 32 listes européennes 2019 proposés selon l'ADR-0010 (grille 2020, ou 2023 pour les européennes 2024), avec `source_bloc`. **9 cas ambigus non classés** (bloc NULL), soumis en questions fermées (Q3-Q9).
6. **Interface** : vues et requêtes « HdF » bornées explicitement aux 5 départements ; 665 tests verts sur la base France (copie), 317 en hermétique ; ruff OK ; pyright non exécuté (pas de réseau, à lancer sur le Mac).
7. **Base réelle non modifiée** : commandes d'application en § 7 (copie de travail : `/Volumes/le gros stockage/outils/tmp/ministere-vagueB.duckdb`).

## 1. Étude d'impact

Mesures réelles sur les Parquet de `data/exploration/` (bases jetables, supprimées depuis).

| Variante (56 scrutins de la source) | Participation | Candidats | Taille sans clé primaire | Avec clé primaire | gzip |
|---|---|---|---|---|---|
| HdF, BV | 0,30 M | 2,53 M | 50 Mo | — | — |
| France, BV | 3,16 M | 27,5 M | 424 Mo | **1 558 Mo** | 139 Mo / **308 Mo** |
| Hors HdF au niveau commune (fraction communale de circo/canton) | 1,48 M | 11,8 M | 360 Mo | — | — |

Constats :
- Le passage à la commune ne réduit le stockage que de 15 % (beaucoup de communes n'ont qu'un BV) et impose une pseudo-clé « fraction communale de circonscription/canton » (communes coupées entre circonscriptions ou cantons). Gain trop faible pour la perte du drill-down : **non implémenté** (YAGNI), réintroductible si besoin.
- L'index de clé primaire (ART) des deux tables de résultats pèse ~1,1 Go non compressé (×3,7 sur ces tables). Le supprimer est une décision de schéma (Q2).
- **Résultat réel** (48 scrutins chargés : pres, legi, muni, euro, regi, dpmt, sans cantonales) : base 2 129 Mo (2 039 Mo après compactage `COPY FROM DATABASE`, gain négligeable), **861 Mo en gzip** (aujourd'hui 632 Mo). Publication GitHub (asset ≤ 2 Go) : OK, marge ~1,1 Go.
- Temps de chargement : présidentielles 16 s, législatives 25 s (jointure spatiale nationale incluse), municipales 12 s, euro/regi/dpmt 27 s.
- Disque : la base décompressée passe à ~2,1 Go chez l'utilisateur (bind mount `data/`), à prévoir dans `install.sh`/`download_db.sh` (aucun contrôle d'espace aujourd'hui).
- Requêtes de l'interface : aucune ne bornait explicitement le périmètre pour les vues d'ensemble HdF ; corrigées (§ 4). Les requêtes par commune ou par circonscription ne changent pas. Temps des tests d'interface sur la base France : 18,8 s (contre ~15 s attendus en HdF ; non mesuré finement).

| Type | Scrutins | BV × scrutin | Lignes candidats |
|---|---|---|---|
| pres | 10 | 655 098 | 4 635 390 |
| legi | 12 | 759 135 | 5 246 106 |
| muni | 8 | 298 732 | 1 665 091 |
| euro | 6 | 391 653 | 10 484 765 |
| regi | 8 | 517 207 | 3 171 052 |
| dpmt | 4 | 250 743 | 789 201 |
| **Total** | **48** | **2 872 568** | **25 991 605** |

## 2. Ce qui a été fait

| Fichier | Changement |
|---|---|
| `src/ministere_de_l_info/etl/loaders/elections_agregees.py` (nouveau) | `filtre_perimetre()`, `code_departement_sql()` (Z* → 97x), `load_scrutins_listes()` (euro/regi/dpmt) |
| `scripts/load_elections_{presidentielles,legislatives,municipales}.py` | `--perimetre hdf|france` ; législatives : reconstruction circo nationale + correctif département |
| `scripts/load_elections_autres.py` (nouveau) | `--perimetre`, `--types euro regi dpmt` ; nuances vague B ; `_etl_metadata` |
| `src/ministere_de_l_info/etl/schema_elections.py` | `_NUANCES_EURO_REGI_DPMT` (149), `_LISTES_EURO_2019` (32), `_CODES_VAGUE_B_NON_CLASSES`, `populate_nuances_vague_b()`, garde-fou d'années étendu, `v_evolution_blocs_hdf_legi` bornée HdF |
| `scripts/migrations/0007_add_municipales_views.py` | `v_evolution_blocs_hdf_muni` bornée HdF |
| `src/ministere_de_l_info/etl/schema_economie.py` | `v_croisement_eco_elections` bornée HdF |
| `viz/elections_queries.py`, `elections_legi_queries.py`, `elections_muni_queries.py`, `economie_queries.py` | filtre HdF explicite sur les vues d'ensemble |
| `tests/test_elections_france_vague_b.py` (nouveau, 14 tests hermétiques) | périmètre, Z*, panneau NULL, binôme, euro 2019, codes ambigus, vues HdF, idempotence |
| 7 fichiers de tests existants | contrats de données (volumes, 50 circos…) bornés aux HdF ; format circo `2A`/`2B` |
| `docs/schema-elections.md`, `docs/data-sources.md`, `docs/architecture.md` | réflexe documentation |

Choix techniques notables :
- Départementales : le binôme (`binome` dans la source) est stocké dans `nom` (pas de nouvelle colonne).
- Européennes 2019 : `nom` = `nom_tete_liste` de la source (« BARDELLA Jordan ») et classement par `candidats_presidentielle`, comme les présidentielles 2017/2022 (gotcha n° 9). La table garde son nom ; voir Q8.
- Européennes 2004 et 2009 : `no_panneau` NULL → numéro synthétique par BV, comme les municipales 2008.
- La clé `(nuance, annee)` (sans `type_scrutin`) ne pose pas de conflit : euro 2014 réutilise les codes des municipales 2014 (même nomenclature de listes), euro/regi 2004 partagent leurs codes, euro 2024 (codes `L*`) ne recoupe pas les législatives 2024. Garde-fou testé : aucune clé partagée avec pres/legi/muni, aucune année municipale.

## 3. Nuances proposées (doctrine ADR-0010, règle 2 sauf mention)

Grille de référence : **INTA1931378J (2020), annexe 3 p. 10** pour 1999-2021 (seule grille ou grille antérieure la plus proche) ; **IOMA2322276J (2023), annexes 1-2 p. 6-7** pour les européennes 2024 et `BC-UXD` 2021 (absent de 2020, grille suivante). Chaque `source_bloc` cite la grille, « ADR-0010 règle 2 » et « vague B, proposition ». Détail ligne à ligne : `_NUANCES_EURO_REGI_DPMT` dans `schema_elections.py`.

| Bloc | Codes (année) |
|---|---|
| EXG | EXG 1999 ; LXG 2004 ; LEXG 2009, 2010, 2015, 2021, 2024 ; BC-EXG 2015, 2021 |
| GAU | GAU, VEC, COM 1999 ; LPS, LVE, LPC, LDG, LGA* 2004 ; LSOC, LVEC, LCOP, LDVG 2009 ; LUG, LSOC, LVEC, LDVG, LCOP 2010 ; LUG, LDVG, LVEC, LVEG*, LFG, LCOM, LSOC, LRDG 2015 ; LUGE*, LUG, LDVG, LFI, LSOC, LCOM 2021 ; BC-SOC, BC-UG, BC-DVG, BC-FG, BC-VEC, BC-COM, BC-RDG, BC-PG 2015 ; BC-UGE*, BC-DVG, BC-UG, BC-SOC, BC-COM, BC-FI, BC-RDG 2021 ; LUG, LFI, LVEC, LCOM, LDVG 2024 |
| DIV | DIV, ECO, REG, CPNT† 1999 ; LDV, LEC, LRG, LCP† 2004 ; LAUT, LREG 2009, 2010 ; LREG, LDIV, LECO 2015 ; LREG, LDIV 2021 ; BC-DIV 2015 ; BC-DIV, BC-REG, BC-GJ 2021 ; LDIV, LECO 2024 |
| CENT | UDF 1999 ; LUDF 2004 ; LCMD 2009, 2010 ; LMDM, LUDI 2015 ; LUC, LDVC, LREM, LMDM, LUDI 2021 ; BC-UDI, BC-MDM, BC-UC 2015 ; BC-DVC, BC-UC, BC-REM, BC-UDI, BC-MDM 2021 ; LENS 2024 |
| DTE | DTE, DVD 1999 ; LUMP, LDD 2004 ; LMAJ, LDVD 2009 ; LMAJ, LDVD 2010 ; LUD, LDLF, LDVD, LLR 2015 ; LUD, LLR, LDVD, LDSV 2021 ; BC-UD, BC-UMP, BC-DVD, BC-DLF 2015 ; BC-DVD, BC-UD, BC-LR, BC-DSV 2021 ; LLR, LDVD 2024 |
| EXD | FRN, MNA 1999 ; LFN, LXD 2004 ; LFN, LEXD 2009, 2010 ; LFN, LEXD 2015 ; LRN, LEXD 2021 ; BC-FN, BC-EXD 2015 ; BC-RN, BC-EXD, BC-UXD 2021 ; LRN, LREC, LEXD 2024 |

\* règle de composition (Q3). † CPNT autonome, cohérence avec CPNT 2002/2007 (règle 3, Q9).
Européennes 2014 : couvertes par les 17 codes des municipales 2014 (le `source_bloc` cite les archives MN2014).
Résidus européennes 2009 `LPC`, `LDD`, `LDV` (11 voix au total) : non classés.

**Européennes 2019** (32 listes, `candidats_presidentielle`, grille 2020) : EXD Bardella, Camus (LEXD aux européennes 2014) ; CENT Loiseau, Lagarde ; GAU Jadot, Aubry, Glucksmann, Hamon, Brossat ; DTE Bellamy, Dupont-Aignan, de Prévoisin (LDVD en 2014) ; EXG Arthaud, Sanchez (LEXG en 2024) ; DIV 18 listes (parti animaliste, Urgence écologie, Décroissance [ECO → AUT], Asselineau [LDIV en 2024], Lalanne et Chalençon [gilets jaunes, LGJ → AUT], 12 listes sans rattachement [LDIV → AUT]). Non classés : Philippot, Vauclin.

Part des voix non classées (France) : régionales 2004 t1 33,7 % (LDR), 2021 t1 14,7 % ; départementales 2021 t1 12,1 % ; européennes 2019 0,7 % ; tous les autres scrutins vague B : 0 %.

## 4. Vues et requêtes de l'interface

Bornées aux 5 départements : `v_evolution_blocs_hdf_legi`, `v_evolution_blocs_hdf_muni`, `v_croisement_eco_elections`, et dans `viz/` : `get_scores_communes`/`get_participation_communes`/`get_evolution_blocs` (zone `hdf`), `get_circos_hdf_legi`, `get_scores_hdf_legi`, `get_participation_hdf_legi`, `get_scores_communes_muni`, `get_croisement_eco_elections`. Vues génériques (`v_scores_commune_pres`, `v_scores_circo_legi`, `v_resultats_candidats_avec_bloc`…) laissées nationales pour la future interface web. Aucune page n'affiche encore euro/regi/dpmt (vague A).

## 5. Questions fermées pour Mathias

- **Q1** Niveau de détail : bureau de vote pour toute la France (base 2,1 Go, 0,86 Go compressée) ? (oui / non, commune hors HdF)
- **Q2** Garder les clés primaires des tables de résultats (≈ 1,1 Go d'index non compressé) ? (oui / non, remplacer par un contrôle d'unicité au chargement)
- **Q3** Règle de composition : un code d'union absent des grilles dont toutes les composantes sont du même bloc prend ce bloc (LGA 2004, LVEG 2015, LUGE et BC-UGE 2021 → GAU) ? (oui / non)
- **Q4** `LDR` régionales 2004 (16,7 M voix ; listes UMP-UDF et listes UDF autonomes : Santini, Bayrou, Arthuis) : (a) DTE / (b) non classé / (c) classement par tête de liste
- **Q5** `LUCD` et `BC-UCD` 2021 (union du centre et de la droite : Rottner, Morançais ; 5,1 M voix) : CENT ou DTE ?
- **Q6** `BC-UCG` 2021 (union du centre et de la gauche, 142 k voix) : CENT, GAU ou DIV (comme LGC 2008) ?
- **Q7** `LECO` et `BC-ECO` 2021 (aucun code VEC en 2021 : les listes EELV Bayou, Grebert, Thierry y figurent) : GAU (sens de l'époque, comme ECO législatives 2017/2022) ou DIV (grille) ?
- **Q8** Européennes 2019 : Philippot (Les Patriotes) EXD ou DTE ? Vauclin EXD ou DIV ? Et garder ces listes dans `candidats_presidentielle` (oui) plutôt qu'une table dédiée (non) ?
- **Q9** Valider CPNT autonome 1999/2004 → DIV et Asselineau 2019 → DIV (nuance LDIV attribuée par le ministère en 2024) ? (oui / non)
- **Q10** Charger les cantonales 2001-2011 (8 scrutins, ~66 codes à classer) dans une vague ultérieure ? (oui / non)
- **Q11** Législatives 2002/2007/2024 en France entière : une commune coupée entre circonscriptions est affectée à une seule (2024 : 529 circos sur 559 représentées). Accepter la limitation (oui) ou reconstruire au BV par une table de passage BV → circo (non, vague ultérieure) ?

Après décision : addendum à l'ADR-0010 (classement des scrutins euro/regi/dpmt) et retrait de la mention « proposition » des `source_bloc`.

## 5 bis. Décisions de Mathias (2026-10-07)

Q1 bureau de vote partout ; Q2 suppression des clés primaires (contrôle d'unicité au chargement) ; Q3 unions 100 % gauche → GAU ; Q4 LDR 2004 → DTE (mélange UDF mentionné) ; Q5 LUCD/BC-UCD 2021 → DTE ; Q6 BC-UCG 2021 → DIV ; Q7 LECO/BC-ECO 2021 → GAU ; Q8 Philippot → EXD, Vauclin → DIV, listes 2019 conservées dans `candidats_presidentielle` ; Q9 CPNT 1999/2004 et Asselineau 2019 → DIV ; Q10 cantonales plus tard ; Q11 limite des communes coupées acceptée et documentée (`docs/schema-elections.md` ; l'avertissement de l'interface ne couvre que 2002/2007, à étendre à 2024 en vague A). Le tableau complet des classements est dans l'addendum de l'ADR-0010. `nuances_harmonisees` : 384 entrées ; `candidats_presidentielle` : 57.

## 6. Limites et anomalies relevées

- Lignes écartées (commune absente du référentiel géographique COG actuel) : ~2 000 BV par scrutin avant 2017 (communes fusionnées), ~900 ensuite (Français de l'étranger, Pacifique). Comportement historique conservé ; une table de passage COG serait nécessaire pour les récupérer.
- Saint-Pierre-et-Miquelon : `geographies_communes.code_departement = 'NR'` (référentiel), les résultats portent `975`.
- Municipales 2026 t1, commune 49367 : `pct_exprimes` = 100,04 % (anomalie de la source).
- pyright non exécuté dans cette session (PyPI injoignable) : `uvx pyright@1.1.408` à lancer avant fusion.

## 7. Application à la base réelle (directeur, après sauvegarde)

```bash
cd "/Volumes/le gros stockage/ministere-de-l-info"   # après fusion de la branche
cp data/ministere.duckdb "../ministere-de-l-info-backups/ministere-avant-vagueB-$(date +%F).duckdb"
uv run python scripts/migrations/0009_resultats_sans_cle_primaire.py
uv run python scripts/init_elections_schema.py
uv run python scripts/migrations/0007_add_municipales_views.py
uv run python scripts/load_elections_presidentielles.py --perimetre france
uv run python scripts/load_elections_legislatives.py --perimetre france
uv run python scripts/load_elections_municipales.py --perimetre france
uv run python scripts/load_elections_autres.py --perimetre france
uv run python -c "from ministere_de_l_info.etl._common import open_connection; \
from ministere_de_l_info.etl.schema_economie import create_economie_views; \
c = open_connection(); create_economie_views(c); c.execute('CHECKPOINT'); c.close()"
# Compactage (récupère ~200 Mo de blocs libérés), puis remplacement du fichier
uv run python -c "import duckdb; c = duckdb.connect(); c.execute('LOAD spatial'); \
c.execute(\"ATTACH 'data/ministere.duckdb' AS s (READ_ONLY)\"); \
c.execute(\"ATTACH 'data/ministere-compact.duckdb' AS d\"); c.execute('COPY FROM DATABASE s TO d')"
mv data/ministere-compact.duckdb data/ministere.duckdb
uv run pytest -q        # 681 tests attendus verts sur la base France
```

Retour arrière : restaurer la sauvegarde.

## 8. Requêtes de contrôle

```sql
-- Volumes par type
SELECT e.type_scrutin, COUNT(DISTINCT rp.id_election), COUNT(*), COUNT(DISTINCT rp.code_commune)
FROM resultats_participation rp JOIN elections e USING (id_election) GROUP BY 1 ORDER BY 1;
-- Part des voix sans bloc (attendu : 0, sauf 11 voix aux européennes 2009)
SELECT id_election, ROUND(100.0 * SUM(voix) FILTER (WHERE bloc IS NULL) / SUM(voix), 2)
FROM v_resultats_candidats_avec_bloc WHERE type_scrutin IN ('euro','regi','dpmt') GROUP BY 1 ORDER BY 1;
-- Non-régression HdF : 50 circonscriptions, vues d'évolution inchangées
SELECT COUNT(DISTINCT code_circo) FROM v_scores_circo_legi
WHERE annee = 2022 AND tour = 1 AND split_part(code_circo, '-', 1) IN ('02','59','60','62','80');
-- Aucun code département « Z* » résiduel
SELECT COUNT(*) FROM resultats_participation WHERE code_departement LIKE 'Z%';
```
