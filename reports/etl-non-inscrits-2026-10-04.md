# ETL — Non-inscrits de l'AN classés par nuance préfectorale d'élection

Date : 2026-10-04 · Agent : ingenieur-etl · Périmètre : AN, législatures XII à XVII (Datan)

## Résumé exécutif

- 100 mandats NI (Datan, dernière législature) : 70 nuances d'élection retrouvées, 30 non retrouvées (restent DIV, motif explicite).
- Après : CENT 19, DIV 31 (30 non retrouvés + Aly, nuance DIV), DTE 11, EXD 9, GAU 30 ; 69 mandats changent de bloc. Actifs (XVIIe) : EXD 3, DTE 3, CENT 3, DIV 1.
- Exemples cités par l'orientation : Maréchal (FN 2012) et Collard, Aliot (FN 2017) → EXD ; **Ménard (DVD 2022) et Dupont-Aignan (DSV 2022) → DTE, pas EXD**.
- Source : « Données des élections agrégées », Parquet national déjà présent (`data/exploration/general-results.parquet`) ; pas de nouvelle source, aucun téléchargement.
- Schéma : 3 colonnes `nuance_*` sur `leg_mandats` (ALTER IF NOT EXISTS), vues `v_mandats_legislatif` et `v_elus_actuels` recalculées ; addendum ADR-0011.
- Non retrouvés : 28 absent(e)s des candidats élus (remplaçants probables ; Edmond-Mariette et Chouin, partielles probables) et 2 candidats battus à la générale (Poursinoff, Vuibert).
- Tests : `tests/test_legislatif_nuances_ni.py` (7, hermétiques) ; suite complète sur copie de base 628 passés, 1 échec préexistant (`test_aucun_mandat_non_classe`, groupes sénatoriaux C, RP…), couverture 76,6 %.
- Décisions : Q1 remplaçants (nuance de la candidature du titulaire ?) ; Q2 charger AMO (partielles et remplacements) ; Q3 valider DTE pour Ménard et Dupont-Aignan.
- À faire sur le Mac : `uv run python scripts/load_legislatif.py --source nuances` sur la base réelle.

## Faisabilité et source

- Le module Élections ne charge en base que les Hauts-de-France, mais le Parquet source est
  national et déjà sur le Mac (`data/exploration/general-results.parquet`, 154 Mo,
  résultats **par candidat** malgré le nom, gotcha n° 8). 12 scrutins législatifs
  2002-2024 (t1/t2), nuance renseignée. Lu par DuckDB, filtré sur les scrutins visés,
  jamais matérialisé.
- Pas de code de circonscription dans la source pour 2002, 2007 et 2024 : l'appariement
  se fait par **département + identité + élection effective**, ce qui rend le
  redécoupage de 2010 (appliqué en 2012) sans effet. La circonscription citée dans la
  source vient de Datan.
- Codes outre-mer et étranger de la source (ZA…ZZ, numériques en 2024 t1) ramenés aux
  codes Datan (971…988, 099).
- Encodage : en 2012 certains accents sont remplacés par `?` (« Th?r?se ») ; un `?`
  vaut un caractère à l'appariement.
- Limite Datan (ADR-0011) : un seul mandat par député (dernière législature). Un député
  NI dans une législature antérieure à sa dernière n'apparaît pas ; le modèle (par
  mandat) le traitera dès qu'une source complète (AMO) existera.

## Règle appliquée (`etl/loaders/legislatif_nuances_ni.py`)

1. Élection générale de la législature du mandat (XII 2002 … XVII 2024).
2. Candidat du même département, prénom identique, nom identique ou préfixe l'un de
   l'autre après normalisation (un cas : Djebbari, candidat sous « DJEBBARI-BONNET »,
   cité dans la source).
3. Candidat élu : en tête au second tour sur ses bureaux, ou > 50 % au premier tour sans
   second tour.
4. Une seule nuance, sinon ambiguïté (aucun cas).
5. Bloc : jointure vue sur `nuances_harmonisees (nuance, annee)` ; nuance absente du
   référentiel → bloc du groupe (aucun cas).

Cas particuliers :

| Cas | Traitement | Effectif |
|---|---|---|
| Remplaçant(e) devenu(e) député(e) (ministre, décès, cumul), probable | Absent(e) des candidats → DIV, « nuance d'élection non retrouvée : absent(e) des candidats… » | 26 |
| Élu(e) d'une partielle, candidat(e) battu(e) à la générale | « candidat(e) non élu(e)… » → DIV | 2 (Poursinoff, Vuibert) |
| Élu(e) d'une partielle, absent(e) de la générale (probable, d'après la date de prise de fonction) | « absent(e) des candidats… » → DIV | 2 (Edmond-Mariette, Chouin) |
| Ministre revenu siéger (Duflot, Touraine…) | Élu(e) à la générale → nuance retrouvée | inclus dans les 70 |
| Redécoupage 2012 | Sans effet (appariement par département) | — |

Les 26 + 4 sont indiscernables sans source des mandats (AMO) : la distinction proposée
dans le motif est indicative, la source ne permet pas de la trancher.

## Volumétrie

| Lég. | Mandats NI | Reclassés | Non retrouvés |
|---|---|---|---|
| XII | 4 | 3 | 1 |
| XIII | 18 | 5 | 12 |
| XIV | 31 | 25 | 6 |
| XV | 30 | 21 | 9 |
| XVI | 5 | 5 | 0 |
| XVII | 12 | 10 | 2 |
| **Total** | **100** | **69** | **30** |

Aly (XIII, 976-1) : nuance retrouvée DIV (2007) → DIV, compté comme non reclassé.

## Liste complète des mandats NI (avant → après)

| Lég. | Député(e) | Circ. | Avant | Après | Source |
|---|---|---|---|---|---|
| 12 | Besson Éric | 26-2 | DIV | GAU | nuance préfectorale SOC (législatives 2002, 26-2) → GAU |
| 12 | Edmond-Mariette Philippe | 972-3 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2002 (972) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 12 | Leveau Édouard | 76-11 | DIV | DTE | nuance préfectorale UMP (législatives 2002, 76-11) → DTE |
| 12 | Zuccarelli Émile | 2b-1 | DIV | GAU | nuance préfectorale PRG (législatives 2002, 2B-1) → GAU |
| 13 | Abiven Yvon | 29-4 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (29) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Ajon Emmanuelle | 33-2 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (33) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Aly Abdoulatifou | 976-1 | DIV | DIV | nuance préfectorale DIV (législatives 2007, 976-1) → DIV |
| 13 | Autexier Jean-Yves | 75-21 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (75) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Bayrou François | 64-2 | DIV | CENT | nuance préfectorale UDFD (législatives 2007, 64-2) → CENT |
| 13 | Borowski Joëlle | 57-8 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (57) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Chaintron Rémi | 71-6 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (71) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Couanau René | 35-7 | DIV | DTE | nuance préfectorale UMP (législatives 2007, 35-7) → DTE |
| 13 | Desallangre Jacques | 02-4 | DIV | GAU | nuance préfectorale DVG (législatives 2007, 02-4) → GAU |
| 13 | Francois Patrice | 38-1 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (38) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Garrigue Daniel | 24-2 | DIV | DTE | nuance préfectorale UMP (législatives 2007, 24-2) → DTE |
| 13 | Gremetz Maxime | 80-1 | DIV | GAU | nuance préfectorale DVG (législatives 2007, 80-1) → GAU |
| 13 | Marie Audrey | 973-1 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (973) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Mussington Louis | 971-4 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (971) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Poursinoff Anny | 78-10 | DIV | DIV | nuance d'élection non retrouvée : candidat(e) non élu(e) aux législatives générales 2007 (78) — élection partielle ou remplacement ; bloc du groupe NI (DIV) |
| 13 | Robert Yvon | 76-1 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (76) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Rouxel André | 50-5 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (50) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 13 | Souchet Dominique | 85-5 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2007 (85) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Abeille Laurence | 94-6 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 94-6) → GAU |
| 14 | Allain Brigitte | 24-2 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 24-2) → GAU |
| 14 | Andrieux Sylvie | 13-3 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 13-3) → GAU |
| 14 | Attard Isabelle | 14-5 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 14-5) → GAU |
| 14 | Auroi Danielle | 63-3 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 63-3) → GAU |
| 14 | Baron Esther | 04-2 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2012 (04) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Baupin Denis | 75-10 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 75-10) → GAU |
| 14 | Boistard Pascale | 80-1 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 80-1) → GAU |
| 14 | Bonneton Michèle | 38-9 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 38-9) → GAU |
| 14 | Bourdouleix Gilles | 49-5 | DIV | DTE | nuance préfectorale UMP (législatives 2012, 49-5) → DTE |
| 14 | Cazeneuve Bernard | 50-4 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 50-4) → GAU |
| 14 | Chauvel Dominique | 76-10 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 76-10) → GAU |
| 14 | Coronado Sergio | 099-2 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 099-2) → GAU |
| 14 | Duflot Cécile | 75-6 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 75-6) → GAU |
| 14 | Fromantin Jean-Christophe | 92-6 | DIV | DTE | nuance préfectorale DVD (législatives 2012, 92-6) → DTE |
| 14 | Geoffroy Hélène | 69-7 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 69-7) → GAU |
| 14 | Lebreton Patrick | 974-4 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 974-4) → GAU |
| 14 | Lefrand Guy | 27-1 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2012 (27) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Lubin Monique | 40-3 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2012 (40) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Mallejac Claire | 29-6 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2012 (29) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Mamère Noël | 33-3 | DIV | GAU | nuance préfectorale VEC (législatives 2012, 33-3) → GAU |
| 14 | Maréchal-Le Pen Marion | 84-3 | DIV | EXD | nuance préfectorale FN (législatives 2012, 84-3) → EXD |
| 14 | Noguès Philippe | 56-6 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 56-6) → GAU |
| 14 | Pen Catherine | 975-1 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2012 (975) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Pinville Martine | 16-1 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 16-1) → GAU |
| 14 | Prat Patrice | 30-3 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 30-3) → GAU |
| 14 | Rousselin Jean-Louis | 76-7 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2012 (76) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 14 | Thévenoud Thomas | 71-1 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 71-1) → GAU |
| 14 | Touraine Marisol | 37-3 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 37-3) → GAU |
| 14 | Valter Clotilde | 14-3 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 14-3) → GAU |
| 14 | Vidalies Alain | 40-1 | DIV | GAU | nuance préfectorale SOC (législatives 2012, 40-1) → GAU |
| 15 | Abba Bérangère | 52-1 | DIV | CENT | nuance préfectorale REM (législatives 2017, 52-1) → CENT |
| 15 | Aliot Louis | 66-2 | DIV | EXD | nuance préfectorale FN (législatives 2017, 66-2) → EXD |
| 15 | Bagarry Delphine | 04-1 | DIV | CENT | nuance préfectorale REM (législatives 2017, 04-1) → CENT |
| 15 | Beauvais Bernadette | 77-6 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (77) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Bompard Jacques | 84-4 | DIV | EXD | nuance préfectorale EXD (législatives 2017, 84-4) → EXD |
| 15 | Cariou Émilie | 55-2 | DIV | CENT | nuance préfectorale REM (législatives 2017, 55-2) → CENT |
| 15 | Chiche Guillaume | 79-1 | DIV | CENT | nuance préfectorale REM (législatives 2017, 79-1) → CENT |
| 15 | Collard Gilbert | 30-2 | DIV | EXD | nuance préfectorale FN (législatives 2017, 30-2) → EXD |
| 15 | Coriton Bastien | 76-5 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (76) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Deguerry Jean | 01-5 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (01) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Derelle Damien | 78-5 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (78) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Djebbari Jean-Baptiste | 87-2 | DIV | CENT | nuance préfectorale REM (législatives 2017, 87-2, candidature « DJEBBARI-BONNET Jean-Baptiste ») → CENT |
| 15 | Evrard José | 62-3 | DIV | EXD | nuance préfectorale FN (législatives 2017, 62-3) → EXD |
| 15 | Forteza Paula | 099-2 | DIV | CENT | nuance préfectorale REM (législatives 2017, 099-2) → CENT |
| 15 | Gaillard Olivier | 30-5 | DIV | CENT | nuance préfectorale REM (législatives 2017, 30-5) → CENT |
| 15 | Gaillot Albane | 94-11 | DIV | CENT | nuance préfectorale REM (législatives 2017, 94-11) → CENT |
| 15 | Girardin Annick | 975-1 | DIV | GAU | nuance préfectorale RDG (législatives 2017, 975-1) → GAU |
| 15 | Houplain Myriane | 62-10 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (62) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Jeanne Ghylaine | 971-2 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (971) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Loquet Ludovic | 62-6 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (62) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Orphelin Matthieu | 49-1 | DIV | CENT | nuance préfectorale REM (législatives 2017, 49-1) → CENT |
| 15 | Pajot Ludovic | 62-10 | DIV | EXD | nuance préfectorale FN (législatives 2017, 62-10) → EXD |
| 15 | Pech Margaux | 75-3 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (75) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Peltier Guillaume | 41-2 | DIV | DTE | nuance préfectorale LR (législatives 2017, 41-2) → DTE |
| 15 | Pietraszewski Laurent | 59-11 | DIV | CENT | nuance préfectorale REM (législatives 2017, 59-11) → CENT |
| 15 | Pujol Catherine | 66-2 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2017 (66) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 15 | Son-Forget Joachim | 099-6 | DIV | CENT | nuance préfectorale REM (législatives 2017, 099-6) → CENT |
| 15 | Taquet Adrien | 92-2 | DIV | CENT | nuance préfectorale REM (législatives 2017, 92-2) → CENT |
| 15 | Villani Cédric | 91-5 | DIV | CENT | nuance préfectorale REM (législatives 2017, 91-5) → CENT |
| 15 | Wonner Martine | 67-4 | DIV | CENT | nuance préfectorale REM (législatives 2017, 67-4) → CENT |
| 16 | Bayou Julien | 75-5 | DIV | GAU | nuance préfectorale NUP (législatives 2022, 75-5) → GAU |
| 16 | Dupont-Aignan Nicolas | 91-8 | DIV | DTE | nuance préfectorale DSV (législatives 2022, 91-8) → DTE |
| 16 | Julien-Laferrière Hubert | 69-2 | DIV | GAU | nuance préfectorale NUP (législatives 2022, 69-2) → GAU |
| 16 | Larsonneur Jean-Charles | 29-2 | DIV | CENT | nuance préfectorale DVC (législatives 2022, 29-2) → CENT |
| 16 | Ménard Emmanuelle | 34-6 | DIV | DTE | nuance préfectorale DVD (législatives 2022, 34-6) → DTE |
| 17 | Besse Véronique | 85-4 | DIV | DTE | nuance préfectorale DVD (législatives 2024, 85-4) → DTE |
| 17 | Bonnecarrère Philippe | 81-1 | DIV | CENT | nuance préfectorale DVC (législatives 2024, 81-1) → CENT |
| 17 | Chouin Stéphane | 45-1 | DIV | DIV | nuance d'élection non retrouvée : absent(e) des candidats des législatives générales 2024 (45) — remplaçant(e) ou élection partielle ; bloc du groupe NI (DIV) |
| 17 | Delannoy Sandra | 59-3 | DIV | EXD | nuance préfectorale RN (législatives 2024, 59-3) → EXD |
| 17 | Dupont Stella | 49-2 | DIV | CENT | nuance préfectorale ENS (législatives 2024, 49-2) → CENT |
| 17 | Engrand Christine | 62-6 | DIV | EXD | nuance préfectorale RN (législatives 2024, 62-6) → EXD |
| 17 | Errante Sophie | 44-10 | DIV | CENT | nuance préfectorale ENS (législatives 2024, 44-10) → CENT |
| 17 | Grenon Daniel | 89-1 | DIV | EXD | nuance préfectorale RN (législatives 2024, 89-1) → EXD |
| 17 | Pradié Aurélien | 46-1 | DIV | DTE | nuance préfectorale LR (législatives 2024, 46-1) → DTE |
| 17 | Prevost Hugo | 38-1 | DIV | GAU | nuance préfectorale UG (législatives 2024, 38-1) → GAU |
| 17 | Schellenberger Raphaël | 68-4 | DIV | DTE | nuance préfectorale LR (législatives 2024, 68-4) → DTE |
| 17 | Vuibert Lionel | 08-1 | DIV | DIV | nuance d'élection non retrouvée : candidat(e) non élu(e) aux législatives générales 2024 (08) — élection partielle ou remplacement ; bloc du groupe NI (DIV) |

## Vérifications

```
PYTHONPATH=src uv run pytest tests/test_legislatif_nuances_ni.py -q        # 7 passed
PYTHONPATH=src uv run pytest -q   # copie de base : 628 passed, 1 failed (préexistant), cov 76,63 %
uv run ruff check --output-format concise src tests scripts                # All checks passed
uv run ruff format --check src tests scripts                                # OK
MINISTERE_DB_PATH=<copie> uv run python scripts/load_legislatif.py --source nuances
  # Non-inscrits AN : 100 mandat(s), nuance d'élection retrouvée pour 70
```

Le test en échec `tests/test_legislatif.py::test_aucun_mandat_non_classe` échoue à
l'identique sur la base non modifiée (35 mandats sénatoriaux C, RP, G.D.S.R.G.,
Écologiste ; hors périmètre).

## Requêtes de contrôle (base réelle, après chargement)

```sql
-- Répartition des mandats NI après reclassement (attendu : CENT 19, DIV 31, DTE 11, EXD 9, GAU 30)
SELECT bloc_final, COUNT(*) FROM v_mandats_legislatif
WHERE chambre = 'AN' AND groupe_sigle = 'NI' GROUP BY 1 ORDER BY 1;
-- Non retrouvés (30 attendus)
SELECT legislature, nom, prenom, nuance_source FROM v_mandats_legislatif
WHERE groupe_sigle = 'NI' AND nuance_election IS NULL AND nuance_source IS NOT NULL ORDER BY 1, 2;
-- Aucune nuance en dehors des NI (0 attendu)
SELECT COUNT(*) FROM leg_mandats WHERE nuance_source IS NOT NULL AND groupe_sigle <> 'NI';
-- Exemples de l'orientation
SELECT legislature, nom, bloc_final, source_bloc FROM v_mandats_legislatif
WHERE nom IN ('Maréchal-Le Pen', 'Collard', 'Aliot', 'Ménard', 'Dupont-Aignan');
```

## Décisions à soumettre (questions fermées)

1. **Remplaçants** : leur attribuer la nuance de la candidature dont ils étaient
   remplaçants (déclarée conjointement avec le titulaire) ? — oui / non. Exige d'identifier
   le titulaire : source AMO (Q2) ; l'inférence « vainqueur de la circonscription »
   confondrait remplaçants et élus de partielles (Poursinoff aurait reçu la nuance de
   C. Boutin).
2. **Source AMO** (data.assemblee-nationale.fr, mandats avec cause : générale, partielle,
   remplacement) : instruire l'ADR (déjà point ouvert n° 4 de l'ADR-0011) ? — oui / non.
   Les résultats des partielles ne sont pas dans « Données des élections agrégées ».
3. **Ménard et Dupont-Aignan (XVIe)** : la nuance préfectorale 2022 donne DTE (DVD, DSV),
   non EXD comme supposé dans l'orientation. Appliquer la règle telle quelle ? — oui / non.

## Fichiers

- `src/ministere_de_l_info/etl/loaders/legislatif_nuances_ni.py` (nouveau)
- `src/ministere_de_l_info/etl/schema_legislatif.py` (colonnes, vues)
- `src/ministere_de_l_info/etl/schema_elections.py` (`create_nuances_harmonisees` factorisée)
- `src/ministere_de_l_info/etl/legislatif_groupes.py` (fondement NI)
- `scripts/load_legislatif.py` (`--source nuances`)
- `tests/test_legislatif_nuances_ni.py` (nouveau)
- `docs/adr/0011-legislatif-groupes-par-legislature.md` (addendum)

Mise à jour de CLAUDE.md proposée : ligne Législatif, « non-inscrits AN classés par
nuance préfectorale d'élection (70/100), 30 remplaçants/partielles en DIV ».
