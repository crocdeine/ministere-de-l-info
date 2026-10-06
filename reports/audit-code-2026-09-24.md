# Audit de correction du code — ministere-de-l-info

**Date** : 2026-09-24
**Périmètre** : `src/`, `pages/`, `app.py`, `scripts/` (dont `scripts/migrations/`), `deploy/`, `tests/`
**Nature** : audit en lecture seule. Aucun fichier applicatif modifié. Il complète `reports/session-2026-09-24_etat-des-lieux.md` sans reprendre ses constats, sauf pour les confirmer ou les préciser.
**Méthode** : lecture intégrale des modules de requêtes, schémas, migrations, loaders ETL, pages et scripts shell. Chaque requête SQL suspecte a été exécutée sur une base DuckDB en mémoire, avec le vrai code du projet quand c'était possible : `create_elections_schema`, `populate_elections_referentiels`, `create_elections_views`, migrations 0006 et 0007, `_insert_nuances_harmonisees`, `create_economie_views`, `_build_bv_df`. L'extension spatial n'était pas disponible.

Légende du statut :
- **CONFIRMÉ** : bug reproduit à l'exécution, ou certain à la simple lecture du code.
- **PLAUSIBLE** : dépend du contenu réel des sources ou de la base, absentes de ce conteneur. La requête de vérification est indiquée.

---

## 1. Tableau récapitulatif

| ID | Gravité | Statut | Fichier:ligne | Constat |
|---|---|---|---|---|
| C1 | Critique | CONFIRMÉ | `scripts/migrations/0007_add_municipales_views.py:130-161` | `v_listes_commune_muni` regroupe par nuance et non par liste : deux listes de même nuance sont fusionnées. Voix additionnées, tête de liste arbitraire (MAX). |
| C2 | Critique | CONFIRMÉ | `src/ministere_de_l_info/etl/schema_elections.py:679` | Relancer `init_elections_schema.py` supprime les 67 nuances municipales (`DELETE FROM nuances_harmonisees` sans filtre). Tous les blocs municipaux passent alors à NULL. |
| C3 | Critique | CONFIRMÉ | `scripts/load_elections_municipales.py:206-211` | `INSERT OR IGNORE` : corriger un mapping municipal dans le code puis relancer le loader ne change rien en base. Cela bloque la correction LCOM/LUDI/LUD/LECO prévue par l'état des lieux. |
| I1 | Important | CONFIRMÉ (logique) / PLAUSIBLE (ampleur) | `scripts/load_elections_legislatives.py:56-63, 113-140` ; `src/ministere_de_l_info/pages/elections_legislatives.py:78` | Législatives 2024 : `code_circo` reconstruit par le centroïde de la commune, donc les communes coupées sont affectées en bloc à une seule circo. Aucun avertissement dans l'UI (affiché pour 2002/2007 seulement). |
| I2 | Important | CONFIRMÉ | `schema_elections.py:745-751` ; `viz/elections_queries.py:253-285` ; `viz/elections_legi_queries.py:389-434` | Drill-down commune/BV : une nuance non mappée donne `bloc = NULL` (et non DIV comme au niveau circo). Repli sur `candidats_presidentielle` par homonymie de nom, sans filtre de type de scrutin. `bloc_gagnant = 'DIV'` peut être affiché avec voix_DIV = 0. |
| I3 | Important | CONFIRMÉ | `src/ministere_de_l_info/viz/elections_muni_queries.py:104-117` ; `viz/maps_elections.py:310` | Carte municipale : une commune où une liste « NC » arrive en tête est affichée « Non classé (commune < seuil) », alors que le drill-down donne un bloc dominant. |
| I4 | Important | CONFIRMÉ | `pages/elections_presidentielles.py:106` ; `pages/elections_legislatives.py:109` ; `etl/schema_economie.py:172-184` | Taux de participation régional et indicateurs « HdF » calculés comme moyennes non pondérées des communes. |
| I5 | Important | CONFIRMÉ | `etl/schema_economie.py:127-146` ; `viz/economie_queries.py:369-386` | Millésimes RP 2015 et 2016 proposés dans le sélecteur mais cartes vides, car `v_economie_commune` part de Filosofi. Croisement présidentielle 2017 toujours vide. |
| I6 | Important | CONFIRMÉ | `pages/1_📍_Géographie.py:261, 272-276, 295` | Tableau Géographie : le filtre région/département est placé dans le `ON` d'un `LEFT JOIN` au lieu d'un `WHERE`. Des entités hors filtre s'affichent avec « — ». |
| I7 | Important | CONFIRMÉ | `etl/schema_legislatif.py:58` ; `etl/loaders/legislatif_datan.py:189-194` | Modèle Législatif : une seule ligne par député (PK `(id, chambre)`, `legislatureLast`, groupe de la dernière législature). L'« évolution par législature » ne représente pas la composition des législatures, et le correctif FI proposé par l'état des lieux (§3.2) ne suffit pas. |
| I8 | Important | PLAUSIBLE | `etl/loaders/legislatif_senat.py:42-49` | Mapping Sénat incomplet : pas de GEST (écologistes), RDPI (Renaissance) ni RDSE. Ces sénateurs basculent vers DIV sans avertissement. |
| I9 | Important | CONFIRMÉ | `scripts/publish_db.sh:66` ; `deploy/update.sh:61-64` ; `scripts/download_db.sh:127-136` ; `deploy/README-deploy.md:21` | Checksum de la base : deux conventions incompatibles. Selon celle utilisée pour publier, soit `update.sh` retélécharge à chaque fois, soit `download_db.sh` refuse la base. `install.sh` et `update.sh` ne vérifient jamais l'intégrité. |
| M1 | Mineur | CONFIRMÉ | `pages/1_📍_Géographie.py:83-88` | Connexion `@st.cache_resource` ouverte en permanence : le verrou DuckDB empêche tout ETL en écriture tant que l'app tourne. Même connexion partagée entre threads. |
| M2 | Mineur | CONFIRMÉ | `viz/elections_muni_queries.py:234-242` | `nb_listes = COUNT(DISTINCT nuance)` : faux dès que deux listes ont la même nuance ou une nuance NULL. Non affiché aujourd'hui. |
| M3 | Mineur | CONFIRMÉ | `viz/elections_muni_queries.py:128` ; `viz/maps_elections.py:367, 398` | Infobulle « Voix totales » de la carte municipale : affiche en réalité les voix du seul bloc dominant. |
| M4 | Mineur | CONFIRMÉ | `pages/elections_municipales.py:194-207` | « Voix non classées : x % » additionne des voix de candidats du scrutin plurinominal (non additives), donc part surestimée. |
| M5 | Mineur | CONFIRMÉ | `etl/schema_elections.py:631-637` | `nuances_harmonisees` sans colonne `type_scrutin`, clé `(nuance, annee)` : collision latente entre scrutins d'une même année. |
| M6 | Mineur | CONFIRMÉ | `pages/3_🏛️_Législatif.py`, `pages/4_📊_Économie.py` ; `viz/legislatif_queries.py:40` ; `viz/economie_queries.py:50` | Base absente (cas prévu par `install.sh`) : exception `IOException` brute au lieu d'un message. |
| M7 | Mineur | CONFIRMÉ | Loaders élections et économie (DELETE puis INSERT) | Aucune transaction : un échec au milieu du rechargement laisse les tables vidées. |
| M8 | Mineur | CONFIRMÉ | `pages/elections_legislatives.py:120, 143-148` | Libellé « Circos 1er tour » affiché aussi au T2. « Circos gagnées » au T1 compte les circos où le bloc est en tête, pas des sièges. |
| M9 | Mineur | CONFIRMÉ | `etl/schema_economie.py:202-243` ; `viz/economie_queries.py:413-443` | Code mort mais faux : `v_desindustrialisation_commune` compare des périodes différentes selon la commune. `get_deserts_medicaux()` n'a pas de filtre d'année. |
| M10 | Mineur | PLAUSIBLE | `etl/loaders/economie_urssaf.py:84, 134, 153, 167` | `zfill(5)` appliqué après le filtre HdF (l'Aisne serait perdue si le code n'a pas son zéro). `cast(Int32, strict=False)` transforme « 12.0 » en NULL sans erreur. |
| M11 | Mineur | PLAUSIBLE | `scripts/load_elections_*.py` (INNER JOIN `geographies_communes`) | Filtre HdF par jointure sur le COG 2025 : les communes fusionnées depuis (anciens codes) disparaissent des scrutins anciens. |
| M12 | Mineur | PLAUSIBLE | `scripts/load_elections_legislatives.py:120-139` | Commune dont le centroïde ne tombe dans aucun polygone HdF : `code_circo` NULL, résultats exclus des vues circo sans avertissement. |
| M13 | Mineur | PLAUSIBLE | `etl/loaders/legislatif_datan.py:46-90, 194` | Groupes AN absents du mapping (EDS 2020, R-UMP 2012…) : repli DIV silencieux. RRDP (radicaux de gauche) classé DIV. |
| M14 | Mineur | CONFIRMÉ | `scripts/load_economie.py:262, 280` | Le cache Parquet de 1,73 Go est demandé même pour `--source eurostat/urssaf/drees`. `--millesimes` filtre aussi CNAF. |
| M15 | Mineur | CONFIRMÉ | `viz/elections_muni_queries.py:41-59` | `get_scrutins_muni()` liste les 8 scrutins du référentiel, même ceux qui ne sont pas chargés. |
| M16 | Mineur | CONFIRMÉ | `scripts/backup_db.sh:17, 48-51` | Backup sans le fichier `.wal`. Nom de volume dépendant du nom du projet compose. Inopérant pour l'installation `deploy/` (bind mount). |
| T1 | Important | CONFIRMÉ | `tests/` (ensemble) | Aucune vue SQL n'est testée sans la base réelle : C1-C3, I2, I3, I5 et I6 ne peuvent pas être détectés en CI. |
| T2 | Mineur | CONFIRMÉ | `tests/test_legislatif.py:95-105, 158-170, 345-358` ; `tests/test_pages_geographie.py:37-40` | Tests quasi tautologiques : le repli DIV passe toujours, `isinstance(rows, list)`, présence des législatures seulement. |
| T3 | Mineur | CONFIRMÉ | `tests/test_circonscriptions.py`, `test_insee_populations.py`, `test_etl_regions.py` | Tests réseau sans `skip` ni marqueur (déjà signalé par l'état des lieux, confirmé). |

**Vérifié sans problème** :
- **Injection SQL** : aucune. Toutes les interpolations f-string portent sur des constantes (`_HDF_DEPTS_SQL`, `_CIRCO21_SQL`, dictionnaires `_config.py`) ou des identifiants validés par liste blanche (`_INDICATEURS_VALIDES`, `_INDICATEURS_ACTIVITE_VALIDES`, `_INDICATEURS_CONTEXTE`). Les entrées utilisateur passent par des paramètres `?`.
- **Connexions** : toutes les fonctions `_open_ro()` ferment leur connexion dans un `finally`.
- **Cache** : aucun objet non sérialisable dans `cache_data`.
- **Carte déserts médicaux à valeur unique** : testée, pas d'erreur Folium.
- **Codes INSEE** : pas de cast en entier dans les loaders d'élections, de Filosofi, du RP, de la CNAF ni de la DREES.

---

## 2. Détail des constats critiques

### C1 — `v_listes_commune_muni` fusionne les listes de même nuance (CONFIRMÉ, critique)

**Où** : `scripts/migrations/0007_add_municipales_views.py:130-161` (`GROUP BY e.annee, e.tour, rc.code_commune, rc.nuance, nh.bloc`), consommée par `get_listes_commune_muni()` (`viz/elections_muni_queries.py:304`), tableau « Détail des listes » (`pages/elections_municipales.py:274-307`).

**Problème** : la vue se présente comme un « détail liste par liste » mais agrège par nuance. Les colonnes descriptives sont prises par `MAX()`.

**Scénario reproduit** en base mémoire, 2020 T1, commune 59350 :

| Liste | Nuance | Voix |
|---|---|---|
| A (DUPONT) | LDVD | 200 |
| B (MARTIN) | LDVD | 150 |
| C (DURAND) | LSOC | 230 |

Résultat de la vue :

```
('LDVD', 'MARTIN', 'LISTE B', 350, 60.34)
('LSOC', 'DURAND', 'LISTE C', 230, 39.66)
```

Une seule ligne « Liste MARTIN » est créditée de 350 voix et 60 % et apparaît 1re, alors que la liste arrivée en tête est C. Deux listes de droite (LDVD/LDVD) ou deux listes divers (LDIV) dans une même commune sont un cas courant.

Autre effet : dans les communes sans nuance, toutes les listes, ou tous les candidats du plurinominal, fusionnent en une seule ligne « Liste (—) ».

**Correctif proposé** : grouper par identifiant de liste, soit `rc.no_panneau` (ou `rc.liste`), avec `rc.nuance` et `nh.bloc`, pour 2014/2020/2026. Attention au cas 2008 : `no_panneau` y est synthétique et varie d'un BV à l'autre (`load_elections_municipales.py:280-286`, tri par `voix DESC`). Pour 2008, grouper plutôt par `(nuance, libelle_abrege_liste, nom_tete_liste)`, ou recalculer un `no_panneau` stable par commune au chargement. Ajouter un test sur fixture mémoire.

### C2 — `populate_elections_referentiels()` supprime les nuances municipales (CONFIRMÉ, critique)

**Où** : `etl/schema_elections.py:678-681` (`DELETE FROM nuances_harmonisees` sans filtre), appelé par `scripts/init_elections_schema.py:52`.

**Problème** : les 67 nuances municipales sont insérées dans cette même table par `load_elections_municipales.py`. Le référentiel ne réinsère ensuite que les nuances présidentielles et législatives.

**Scénario reproduit** : après le chargement municipal, 67 nuances municipales. Après une nouvelle exécution de `populate_elections_referentiels` (par exemple pour corriger une nuance législative) : **0**.
- Toutes les vues municipales renvoient alors `bloc = NULL`.
- La carte devient entièrement « Non classé » et l'évolution des blocs se vide.
- Aucune erreur n'est levée.

**Correctif proposé** : limiter la suppression aux nuances gérées par ce module, par exemple `DELETE FROM nuances_harmonisees WHERE annee IN (<années pres+legi>)`. Mieux, ajouter une colonne `type_scrutin` (voir M5) et supprimer par type. Autre option : déplacer `_NUANCES_MUNI` dans `schema_elections.py` pour qu'un seul point d'entrée gère tout le référentiel.

### C3 — `INSERT OR IGNORE` empêche toute correction des nuances municipales (CONFIRMÉ, critique)

**Où** : `scripts/load_elections_municipales.py:206-211`.

**Scénario reproduit** : LCOM 2026 = EXG en base. On le passe à GAU dans `_NUANCES_MUNI` puis on relance `_insert_nuances_harmonisees` : la base contient toujours **EXG**. Le log annonce « 0 entrées insérées », sans aucun avertissement.

C'est le chemin exact que prendra la priorité 1 de l'état des lieux (correction LCOM/LUDI/LUD/LECO). Sans correctif, on croira la correction appliquée alors que la base est inchangée.

**Correctif proposé** : `INSERT ... ON CONFLICT (nuance, annee) DO UPDATE SET bloc = excluded.bloc, source_bloc = excluded.source_bloc`, précédé d'un `DELETE FROM nuances_harmonisees WHERE annee IN (2008, 2014, 2020, 2026)`. Ce DELETE est sans risque : aucune nuance présidentielle ou législative ne porte ces années. Le commentaire « pour ne pas écraser pres/legi » ne tient pas, puisque les années sont disjointes.

---

## 3. Détail des constats importants

### I1 — Législatives 2024 : attribution des circonscriptions au centroïde, sans avertissement (CONFIRMÉ / ampleur PLAUSIBLE)

**Où** : `scripts/load_elections_legislatives.py:56-63` (2024 dans `_SPATIAL_IDS`) et `113-140` (`ST_Within(ST_Centroid(commune), circo)`). Dans l'UI, `pages/elections_legislatives.py:78` n'affiche l'avertissement que pour `annee in (2002, 2007)`.

**Problème** : pour 2024, tous les BV d'une commune coupée (Lille, Roubaix, Tourcoing, Amiens, Calais…) sont imputés à la circo qui contient le centroïde de la commune. Or l'avertissement 2002/2007 de la page estime lui-même à environ 11 % la part des inscrits HdF concernés.

Scénario : en 2024, la carte HdF, le récapitulatif « circos gagnées » et la vue par circo de 59-01…59-04 (Lille) attribuent 100 % des voix lilloises à une seule circo. Une circo située entièrement à l'intérieur d'une commune coupée peut n'avoir aucun résultat. Et 2024 est le scrutin le plus récent, donc le plus consulté.

**Vérification** :

```sql
SELECT code_circo, COUNT(*)
FROM resultats_participation
WHERE id_election = '2024_legi_t1'
GROUP BY 1
ORDER BY 1;
```

À comparer avec 2022 (circos absentes ou vides).

**Correctif proposé** : le découpage 2024 est identique à celui de 2012-2022. Reprendre l'affectation BV → circo de 2022 (`(code_commune, code_bv) → code_circo` depuis `2022_legi_t1`), avec le centroïde en repli pour les BV renumérotés. Autre option : la table REU « bureaux de vote et adresses », qui porte la circo. Dans tous les cas, étendre l'avertissement à 2024 tant que le correctif n'est pas en place.

### I2 — Bloc NULL et repli par homonymie dans les drill-down commune/BV (CONFIRMÉ)

**Où** :
- `etl/schema_elections.py:745-751` : `COALESCE(nh.bloc, cp.bloc)` ; jointure `candidats_presidentielle` sur `nom` et `annee`, **sans** `type_scrutin = 'pres'`.
- `viz/elections_legi_queries.py:389-396, 426-434` : métriques et BV législatifs lus dans cette vue.
- `viz/elections_queries.py:253-285` : `_build_bv_df`.

**Problème 1 : incohérence d'agrégation.** Au niveau circo (`v_scores_circo_legi`), une nuance non mappée est ramenée à `'DIV'`. Au niveau commune/BV, elle reste NULL.

Reproduit avec `_build_bv_df` sur voix `[(None, 40), ('GAU', 18)]` :
- résultat : `bloc_gagnant = 'DIV'`, `voix_DIV = 0`, `voix_GAU = 18` ;
- une colonne parasite `null = 40`, non affichée.

Le BV est donc présenté comme gagné par DIV avec 0 voix DIV, et la somme des colonnes affichées ne correspond pas aux exprimés. `get_metrics_commune_*` peut aussi renvoyer `bloc_dominant = None`, affiché « — ».

**Problème 2 : repli par homonymie.** Reproduit en législatives 2022 avec une nuance fictive `XYZ` et le nom `ROUSSEL` : la vue renvoie `bloc = 'GAU'`, pris sur le candidat présidentiel. Tout candidat législatif de 2017/2022 dont le nom de famille coïncide avec celui d'un candidat présidentiel (ARTHAUD, HAMON, ROUSSEL, LE PEN, MACRON, POUTOU, FILLON…) hérite du bloc présidentiel si sa nuance n'est pas mappée.

**Correctif proposé** :
- Dans la vue : `LEFT JOIN candidats_presidentielle cp ON cp.nom = rc.nom AND cp.annee = e.annee AND e.type_scrutin = 'pres'`.
- Pour les législatives : `COALESCE(nh.bloc, cp.bloc, 'DIV')`, afin d'aligner commune/BV sur circo. Alternative : garder NULL partout, mais de façon cohérente.
- Dans `_build_bv_df`, ne pas remplir `bloc_gagnant` par « DIV » quand aucune voix n'est rattachée à un bloc.

### I3 — Carte municipale : « Non classé » quand une liste NC est en tête (CONFIRMÉ)

**Où** : `viz/elections_muni_queries.py:104-117`. `ROW_NUMBER()` est calculé sur tous les blocs, NULL compris, puis la requête garde `rn = 1 AND bloc IS NOT NULL`.

**Scénario reproduit** : commune avec NC = 500 voix et DTE = 300 voix. La carte ne trouve aucun bloc dominant et affiche « Non classé ». Le drill-down (`get_metrics_commune_muni`, qui trie seulement les blocs non NULL) affiche DTE.

En 2014 et 2020, la nuance NC est massive (environ 45 000 lignes HdF). La légende « Non classé (commune < seuil) » (`maps_elections.py:310`) est alors fausse pour des communes au-dessus du seuil.

**Correctif proposé** : choisir la règle voulue, puis l'appliquer aux deux endroits. Soit filtrer `bloc IS NOT NULL` avant le `ROW_NUMBER()`, soit afficher « Non classé » dans le drill-down aussi. Dans les deux cas, corriger la légende : « liste non nuancée en tête ou commune < seuil ».

### I4 — Taux de participation et agrégats « HdF » non pondérés (CONFIRMÉ)

**Où** :
- `pages/elections_presidentielles.py:106` : `taux_moy = part_df["taux_participation_pct"].mean()`, métrique « Participation ».
- `pages/elections_legislatives.py:109` : « Participation moy. ».
- `etl/schema_economie.py:172-184` : `AVG(taux_pauvrete)`, `MEDIAN(niveau_vie_median)`, `AVG(tx_chomage_dec)`, présentés comme « Hauts-de-France ».

**Scénario** : en zone HdF (environ 3 800 communes), une commune de 80 inscrits pèse autant que Lille. Le taux affiché n'est pas le taux régional (Σ votants / Σ inscrits). Même chose pour « Taux de pauvreté moyen HdF » et « Niveau de vie médian HdF » (médiane des médianes communales). La légende indique seulement « moyenne des communes avec données », et les communes sous secret statistique en sont exclues.

**Correctif proposé** :
- Participation : `100 * part_df["votants"].sum() / part_df["inscrits"].sum()`.
- Économie : pondérer par la population (pop_active ou population Filosofi), ou utiliser les valeurs officielles régionales. Renommer les libellés en « moyenne communale non pondérée » si le choix est assumé.

### I5 — RP 2015/2016 proposés mais vides ; croisement 2017 vide (CONFIRMÉ)

**Où** :
- `etl/schema_economie.py:127-146` : `FROM economie_filosofi f LEFT JOIN economie_rp r`, donc seules les années 2017-2021 de Filosofi existent dans la vue.
- `viz/economie_queries.py:370, 382-385` : les années RP (2015-2021) viennent de `economie_rp`.
- `viz/economie_queries.py:161-176` : la carte lit `v_economie_commune`.

**Scénario reproduit** : RP 2016 et 2017 en base. `v_economie_commune` ne contient que 2017, et `v_croisement_eco_elections` pour la présidentielle 2017 (données n-1 = 2016) renvoie `tx_chomage_dec = NULL`. Dans l'UI, les indicateurs « Taux de chômage (RP) » et suivants proposent 2016 et 2015 dans le sélecteur, mais la carte est entièrement grise (« 0 communes avec données »).

**Correctif proposé** : bâtir `v_economie_commune` sur l'union des clés des deux tables, `FULL OUTER JOIN` avec `COALESCE(f.code_commune, r.code_commune)` et `COALESCE(f.annee, r.annee_millesime)`. Autre option : router les indicateurs RP directement vers `economie_rp`, comme c'est déjà fait pour les indicateurs sociaux.

### I6 — Tableau Géographie : filtre dans le `ON` du `LEFT JOIN` (CONFIRMÉ)

**Où** : `pages/1_📍_Géographie.py:261` (`where_sql = f"AND ..."`), concaténé après `LEFT JOIN {vue} p ON ... AND p.annee = ?` (lignes 272-276, 295).

**Problème** : la requête n'a pas de `WHERE`. Le filtre porte sur `g.*` mais se retrouve dans la condition de jointure : il ne retire aucune ligne de `g`, il vide seulement la population des lignes hors filtre.

**Scénario reproduit** : niveau Département, filtre région 32. Résultat : `[('59','Nord',2600000), ('62','PdC',1450000), ('75','Paris',0)]`. Tous les départements hors région apparaissent avec « — ». Pour une commune filtrée sur un département de moins de 200 communes, le tableau est complété par des communes d'autres départements. La carte, elle, est correcte (`_queries.py` utilise bien `WHERE`).

**Correctif proposé** : `where_sql = f" WHERE {' AND '.join(where)}"`, placé après les `JOIN`.

### I7 — Modèle Législatif incapable de représenter l'historique (CONFIRMÉ)

**Où** :
- `etl/schema_legislatif.py:58` : `PRIMARY KEY (id, chambre)`.
- `etl/loaders/legislatif_datan.py:189-194` : `legislature = legislatureLast` ; `groupeAbrev` = groupe à la dernière législature.
- `viz/legislatif_queries.py:426-440` : `get_evolution_composition_an`.

**Problème** : un député n'a qu'une ligne, rattachée à sa dernière législature et à son dernier groupe. Le graphique « Composition de l'Assemblée nationale par législature » compte donc, pour la 12e législature, uniquement les députés dont la carrière s'est arrêtée en 2007. Un député élu de 2002 à 2024 n'apparaît qu'en 17e. La légende de l'UI le mentionne (« législature de référence (dernière) »), mais le titre et le graphique restent trompeurs.

Conséquence pour l'état des lieux §3.2 (FI → EXG rétroactif) : rendre le mapping dépendant de la législature ne suffit pas. Les données chargées ne contiennent ni le groupe de chaque législature, ni une ligne par législature.

**Correctif proposé** : table `leg_mandats (elu_id, chambre, legislature, groupe_sigle, bloc, date_debut, date_fin)`, alimentée par les dumps AN (acteurs/mandats) ou un fichier Datan par législature, avec un mapping `(groupe, legislature) → bloc`. En attendant, renommer le graphique (par exemple « Députés par dernière législature siégée ») ou le retirer. Décision structurante : ADR à prévoir.

### I8 — Mapping des groupes du Sénat incomplet (PLAUSIBLE)

**Où** : `etl/loaders/legislatif_senat.py:42-49`. Seuls CRCE-K, SER, UC, « Les Indépendants », « Les Républicains » et NI sont mappés. Tout autre libellé donne `"DIV"` (ligne 266).

**Problème** : les groupes actuels GEST (écologistes, environ 16 sénateurs, attendu GAU), RDPI (Renaissance, environ 20, attendu CENT) et RDSE (environ 15) sont absents. Le mélange de sigles (UC, SER) et de libellés longs (« Les Républicains ») laisse penser que la colonne n'a pas été inventoriée. Si elle contient « LR » ou « INDEP », les plus gros groupes basculent aussi en DIV. `test_mapping_blocs_senat` ne peut pas le détecter (DIV est un bloc valide).

**Vérification** :

```sql
SELECT groupe_sigle, bloc_politique, COUNT(*)
FROM leg_elus
WHERE chambre = 'SENAT' AND est_actif
GROUP BY 1, 2
ORDER BY 3 DESC;
```

**Correctif proposé** : compléter le mapping à partir de cet inventaire. Journaliser (WARNING) tout groupe non mappé au lieu du repli DIV silencieux. Même traitement pour Datan (M13).

### I9 — Checksum de la base : l'incohérence est confirmée (CONFIRMÉ)

L'état des lieux (§3.3) est confirmé et précisé :

| Script | Ce qui est haché | Comparé à |
|---|---|---|
| `scripts/publish_db.sh:66` | `ministere.duckdb.gz` (compressé) | — (publie `ministere.duckdb.gz.sha256`) |
| `scripts/download_db.sh:127-136` | `.gz` téléchargé | fichier `.sha256` de la release. **Cohérent avec publish_db.sh** |
| `deploy/update.sh:61-64` | `~/.ministere-info/data/ministere.duckdb` **décompressé** | fichier `.sha256` de la release. **Incohérent avec publish_db.sh** |
| `deploy/README-deploy.md:21` | fichier **décompressé**, écrit sous le nom `.gz.sha256` | Cohérent avec update.sh, **incompatible avec download_db.sh** |

Conséquence : quelle que soit la convention utilisée pour publier, un des deux scripts est cassé.
- Release faite avec `publish_db.sh` : `update.sh` ne trouve jamais d'égalité et retélécharge environ 635 Mo à chaque mise à jour.
- Release faite selon le README : `download_db.sh` échoue (« SHA256 invalide ») et supprime le fichier téléchargé.

Défauts supplémentaires :
- `install.sh:120-128` et `update.sh:64-70` ne vérifient jamais le fichier téléchargé : une archive tronquée remplace la base (`gunzip -f` puis `mv`) après l'arrêt du conteneur.
- `update.sh` et `install.sh` interrogent `releases/latest`, alors que `download_db.sh` cherche la dernière release `db-*`. Une release de code sans base publiée après une release `db-*` désactive la mise à jour de la base (« Pas de checksum disponible »).
- `gzip` inscrit un horodatage dans l'archive : deux compressions d'une base identique donnent des SHA différents. C'est un argument de plus pour hacher le fichier décompressé.

**Correctif proposé** :
- Une seule convention : publier deux empreintes (`ministere.duckdb.sha256` pour le fichier décompressé, `.gz.sha256` pour l'archive). `update.sh` compare l'empreinte décompressée, et tous les scripts vérifient l'archive avant `gunzip`.
- Même filtre de release partout (`db-*`).
- Tester réellement `update.sh` (TODO déjà inscrit dans CLAUDE.md).

### T1 — Aucune vue SQL testée sans la base réelle (CONFIRMÉ, important)

Tous les tests de vues et de requêtes sont `skip` quand `data/ministere.duckdb` est absent, ce qui est le cas en CI. Les bugs C1, C2, C3, I2, I3, I5 et I6 ont pourtant tous été reproduits dans cet audit en quelques lignes, sur une base DuckDB en mémoire, sans extension spatial et avec les fonctions réelles du projet (`create_elections_views`, migrations 0006/0007, `_insert_nuances_harmonisees`, `create_economie_views`, `_build_bv_df`).

**Correctif proposé** : une fixture pytest `mem_db` qui crée les schémas et insère 5 à 10 lignes synthétiques par cas limite (deux listes de même nuance, liste NC en tête, nuance non mappée, homonyme présidentiel, millésime RP seul, relance des référentiels), plus des tests de régression sur ces cas. Ce sont des tests hermétiques, exécutables en CI.

---

## 4. Détail des constats mineurs

**M1 — Connexion persistante (Géographie).** `@st.cache_resource _get_con()` garde une connexion `read_only` ouverte tant que le processus vit.
- Vérifié : un second processus qui ouvre la base en écriture échoue (`IOException: Could not set lock on file … Conflicting lock is held`). Tout script ETL échoue donc dès que la page Géographie a été visitée. Sur le même hôte, c'est confirmé. À travers le bind mount OrbStack, c'est plausible.
- La même `DuckDBPyConnection` est partagée entre les threads des sessions Streamlit, ce que DuckDB déconseille.
- Correctif : ouvrir et fermer la connexion par requête, comme les autres modules, ou utiliser `con.cursor()` par appel.

**M2 — `nb_listes`** (`elections_muni_queries.py:234-242`). `COUNT(DISTINCT rc.nuance)` ne compte pas les nuances NULL et fusionne les nuances identiques (2 au lieu de 3 dans le scénario de C1). Correctif : `COUNT(DISTINCT rc.no_panneau)`. Valeur non affichée aujourd'hui.

**M3 — « Voix totales » de la carte municipale.** `COALESCE(dom.voix_total, vt.voix_total_all)` : pour une commune nuancée, c'est le nombre de voix du bloc dominant. Correctif : sélectionner `vt.voix_total_all` et `dom.voix_total` séparément, ou renommer l'infobulle « Voix du bloc dominant ».

**M4 — Part des « voix non classées ».** `pages/elections_municipales.py:194-207` rapporte la somme des voix NULL (y compris les voix de candidats du plurinominal, plusieurs par électeur) au total de ces mêmes voix. La part des communes sous le seuil est donc surestimée, alors que la vue 0007 prévient elle-même que ces voix ne sont pas additives. Correctif : raisonner en exprimés (communes non nuancées / exprimés HdF) ou en nombre de communes.

**M5 — `nuances_harmonisees` sans type de scrutin.** La clé `(nuance, annee)` est partagée entre présidentielles (codes candidats), législatives et municipales. Il n'y a pas de collision aujourd'hui (années ou codes disjoints). Mais le chargement d'européennes 2024, de cantonales 2008 ou de régionales 2021 avec des codes communs (`DIV`, `EXG`, `RN`…) sera refusé (PK) ou produira un mauvais bloc. C'est aussi la cause racine de C2. Correctif : ajouter une colonne `type_scrutin` à la PK et aux jointures. Décision structurante : ADR.

**M6 — Base absente.** `pages/3_🏛️_Législatif.py` et `pages/4_📊_Économie.py` appellent directement `is_data_loaded()`. `duckdb.connect(..., read_only=True)` sur un fichier absent lève `IOException` (vérifié), d'où une pile d'appels à l'écran. Or c'est le cas prévu par `install.sh` (« L'app démarrera sans données »). Correctif : tester `DB_PATH.exists()` comme dans `2_🗳️_Élections.py`. Une base ancienne sans les tables Législatif ou Économie lève de même `CatalogException`.

**M7 — Absence de transactions.** Les loaders suivants enchaînent DELETE puis INSERT sans `BEGIN/COMMIT` : `load_elections_*.py`, `load_economie_filosofi/rp`, `load_economie_urssaf` (DELETE total), `legislatif_*`. Un Parquet corrompu ou une coupure réseau en cours de route laisse des tables vides. Correctif : `con.begin()` / `con.commit()` / `con.rollback()` autour de chaque source.

**M8 — Libellés législatifs.** Ligne 120 : « Circos 1er tour » s'affiche aussi au 2e tour. Lignes 143-148 : « Circos gagnées » au T1 désigne le bloc en tête, pas un siège, et l'agrégat par bloc peut désigner vainqueur un bloc qui a deux candidats derrière un candidat unique d'un autre bloc. Correctif : libellé dépendant du tour ; au T2, vainqueur par candidat.

**M9 — Code économie non utilisé mais faux.** Ni `v_desindustrialisation_commune` ni `get_deserts_medicaux()` ne sont appelés par l'UI.
- `v_desindustrialisation_commune` (`schema_economie.py:202-243`) : les bornes MIN/MAX sont calculées par commune. Vérifié : commune 59001 mesurée sur 2006-2010, 59002 sur 2006-2025. Les variations ne sont pas comparables, et une commune dont l'industrie disparaît affiche une baisse partielle au lieu de −100 %.
- `get_deserts_medicaux()` : pas de filtre sur `annee`. Le loader DREES ajoute un millésime à chaque nouvelle publication (upsert sans suppression), donc des doublons apparaîtront.
- Correctif : bornes globales 2006/2025 avec `COALESCE(..., 0)` ; filtrer `annee = MAX(annee)`. Ou supprimer ce code mort.

**M10 — URSSAF (PLAUSIBLE).**
- Le filtre HdF `LEFT(code_commune, 2)` est appliqué sur le CSV brut, avant `str.zfill(5)` (ligne 167). Si l'export OpenDataSoft supprime le zéro initial (« 2001 »), l'Aisne disparaît. DREES fait l'inverse, correctement.
- `pl.col(...).cast(pl.Int32, strict=False)` : vérifié, `"12.0"` devient `None` sans erreur.
- `DataFrame.melt` est déprécié (polars 1.40, vérifié).
- Vérification : `head -3 data/raw/economie/urssaf-commune-ape.csv` et `SELECT COUNT(*) FROM economie_emploi_urssaf WHERE code_commune LIKE '02%'`.
- Correctif : `zfill` puis filtre ; `cast(pl.Float64).cast(pl.Int32)` ; `unpivot`.

**M11 — Communes fusionnées (PLAUSIBLE).** Les trois loaders d'élections filtrent par `INNER JOIN geographies_communes` (COG 2025). Les BV des communes fusionnées depuis 2002 (anciens codes INSEE) sont exclus sans trace des scrutins anciens, ce qui fausse les évolutions. Vérification :

```sql
SELECT id_election, COUNT(DISTINCT code_commune)
FROM read_parquet('data/exploration/candidats-results.parquet')
WHERE code_departement IN ('02', '59', '60', '62', '80')
  AND code_commune NOT IN (SELECT code_insee FROM geographies_communes)
GROUP BY 1;
```

Correctif : filtrer sur `code_departement` et rattacher les anciens codes par une table de passage COG (INSEE « communes nouvelles »).

**M12 — Centroïde hors polygone (PLAUSIBLE).** Une commune littorale ou à géométrie divergente dont le centroïde n'est dans aucune circo HdF garde `code_circo = NULL`. Elle est exclue de `v_scores_circo_legi` (`WHERE rp.code_circo IS NOT NULL`). Vérification : `SELECT id_election, COUNT(*) FROM resultats_participation WHERE id_election LIKE '%legi%' AND code_circo IS NULL GROUP BY 1`. Correctif : repli `ST_Intersects` ou plus proche voisin, et journaliser le reliquat.

**M13 — Groupes Datan non mappés (PLAUSIBLE).** EDS (2020), R-UMP (2012) et tout nouveau sigle basculent silencieusement en DIV. RRDP (PRG, allié du PS) est classé DIV. Correctif : WARNING sur les sigles inconnus ; revoir RRDP (décision méthodologique).

**M14 — `load_economie.py`.**
- `_build_hdf_cache()` (ligne 262) est appelé quelle que soit `--source`. Pour `--source eurostat` ou `urssaf` sans cache, il demande de télécharger 1,73 Go inutiles.
- `--millesimes` (pensé pour Filosofi et RP) est aussi passé à CNAF (ligne 280).
- `all` exclut Eurostat alors que l'aide le présente comme source.
- Correctif : conditionner le cache à `filosofi/rp/all` et séparer les options.

**M15 — `get_scrutins_muni()`.** La liste vient de `elections` (référentiel), pas des résultats. Un scrutin non chargé est sélectionnable et donne une page vide. Correctif : `WHERE EXISTS (SELECT 1 FROM resultats_candidats rc WHERE rc.id_election = e.id_election)`.

**M16 — `backup_db.sh`.**
- Copie `ministere.duckdb` sans `ministere.duckdb.wal`.
- Nom de volume `ministere-info_duckdb-data` codé en dur (dépend du nom du répertoire compose).
- Sans objet pour l'installation utilisateur `deploy/` (bind mount sous `~/.ministere-info/data`).
- Risque faible (application en lecture seule). Correctif : `CHECKPOINT` avant copie, ou copie du `.wal` ; nom de volume paramétrable.

**T2 — Tests quasi tautologiques.**
- `test_mapping_blocs_senat` et `test_datan_blocs_valides` : DIV, bloc de repli, fait toujours partie du référentiel. Mieux vaut tester la part de DIV ou l'absence de sigle non mappé.
- `test_populations_query` : `assert isinstance(rows, list)` est toujours vrai.
- `test_get_evolution_composition_an` : ne vérifie que la présence des législatures 12-17, compatible avec le défaut I7.
- Nombreux tests de cartes réduits à `isinstance(carte, folium.Map)` : acceptables comme smoke tests, sans valeur de correction.

**T3 — Tests réseau.** `test_circonscriptions.py::test_count` et suivants, `test_insee_populations.py` et `test_etl_regions.py` appellent les API réelles sans `skip` ni marqueur. Ils échouent hors ligne (26 échecs dans ce conteneur). Correctif : marqueur `network` exclu par défaut dans `addopts`, ou `pytest.importorskip` / détection réseau.

---

## 5. Priorités suggérées (aucune engagée)

1. **C2 + C3, avant toute correction des nuances municipales** (priorité 1 de l'état des lieux) : sinon la correction LCOM/LUDI/LUD/LECO sera silencieusement ignorée ou effacée.
2. **C1** (tableau des listes municipales) et **I3** (carte municipale) : données fausses directement visibles.
3. **I1** (législatives 2024) et **I2** (drill-down BV) : cohérence de l'agrégation électorale.
4. **I9** (checksums) avant le premier test réel de `update.sh`.
5. **T1** : fixture DuckDB en mémoire et tests de régression sur tous les cas reproduits ici.
6. **I4, I5, I6** : correctifs locaux de quelques lignes.
7. **I7, M5** : décisions de modélisation, ADR à prévoir (validation de Mathias requise).

Scripts de reproduction utilisés (hors dépôt, scratchpad de session) : `t_elec.py` (C1, C2, C3, I2), `t_eco.py` (I5, M9), `t_bv.py` (I2), requêtes DuckDB en ligne (I3, I6, M1, M6, M10).
