# Sources de données

Référence des sources utilisées, abandonnées ou envisagées. Pour le flux d'ingestion,
voir [docs/architecture.md](architecture.md). Dernière mise à jour : 2026-09-24.

| Module | Sources | Script de chargement |
|--------|---------|----------------------|
| Géographie | IGN ADMIN-EXPRESS-COG, INSEE Mélodi, circonscriptions data.gouv.fr | `scripts/etl_territoires.py` |
| Élections | Données des élections agrégées (ministère de l'Intérieur, data.gouv.fr) | `scripts/load_elections_{presidentielles,legislatives,municipales}.py` |
| Économie | Dataset OLAP INSEE Filosofi + RP (data.gouv.fr), CNAF, DREES, URSSAF, Eurostat | `scripts/load_economie.py` |
| Législatif | Datan (data.gouv.fr), Sénat (data.senat.fr) | `scripts/load_legislatif.py` |

Les volumes cités proviennent des rapports de clôture de phase (`reports/`), pas d'une
mesure sur la base.

---

## IGN ADMIN-EXPRESS-COG (data.geopf.fr)

| Aspect | Valeur |
|--------|--------|
| URL | `https://data.geopf.fr/wfs/ows` |
| Format | WFS GeoJSON paginé (GET `outputFormat=application/json`) |
| Auth | Aucune |
| Fréquence de mise à jour | Annuelle (millésime COG — Code Officiel Géographique) |
| Entités couvertes | Régions (18), Départements (101), EPCI (1 265), Communes (34 877), Arrondissements municipaux (45) |
| Module | `src/ministere_de_l_info/data_sources/geo.py` |

**Pagination** : 1 000 features par batch (`count=1000&startindex=N`). Le loader
accumule les pages jusqu'à épuisement de la collection.

**Résolutions géométriques** : plusieurs niveaux de simplification sont stockés dans
DuckDB (`geometry_simplified_national`, `_regional`, `_departemental`, `_communal`,
`_epci`, `_circo`) pour adapter la résolution au zoom affiché.

**Limitations connues** :

- Coupures HTTP chunked aléatoires sur les grandes collections (communes) → retries
  automatiques + reprise depuis le cache disque (`data/raw/`)
- Champ `codes_siren_des_epci` multi-valeur pour 135 communes du Grand Paris →
  stockage de la valeur brute, parsage du premier SIREN prévu en v2
- Saint-Pierre-et-Miquelon retourné avec `code_departement = 'NR'` (COM, hors périmètre
  ADMIN-EXPRESS)

---

## INSEE Mélodi — DS_POPULATIONS_HISTORIQUES (api.insee.fr)

| Aspect | Valeur |
|--------|--------|
| URL | `https://api.insee.fr/melodi/file/DS_POPULATIONS_HISTORIQUES/DS_POPULATIONS_HISTORIQUES_CSV_FR` |
| Dataset | `DS_POPULATIONS_HISTORIQUES` |
| Format | ZIP contenant un CSV UTF-8 `;`, format long (une ligne par mesure × commune × année) |
| Auth | Aucune (endpoint public Mélodi sans OAuth2) |
| Fréquence de mise à jour | Annuelle (après chaque campagne de recensement) |
| Millésimes chargés | 2013, 2018, 2023 |
| Module | `src/ministere_de_l_info/data_sources/insee_populations.py` |

**Colonne fiable** : `population_municipale`. Les colonnes `comptee_a_part` et
`totale` (PCAP) sont absentes de cette source et stockées NULL.

**Couverture territoriale** : France métropolitaine + DROM, hors Mayotte. Les données
de Mayotte sont publiées séparément par l'INSEE dans une source dédiée (à intégrer en v2).

**Granularité** : communale. Les vues DuckDB (`v_population_region`,
`v_population_departement`, `v_population_epci`) sont dérivées par agrégation.

---

## Circonscriptions législatives (data.gouv.fr)

| Aspect | Valeur |
|--------|--------|
| URL | `https://www.data.gouv.fr/api/1/datasets/` |
| Producteur | jerome-desboeufs (contributeur data.gouv.fr) |
| Format | GeoJSON |
| Auth | Aucune |
| Entités | 559 circonscriptions des 577 législatives (hors FPE et étranger) |
| Module | `src/ministere_de_l_info/data_sources/circonscriptions.py` |

**Statut** : source non officielle — aucun export direct de l'Assemblée Nationale
n'est disponible actuellement sur data.gouv.fr. Le dataset jerome-desboeufs est la
référence communautaire la plus complète.

**Limitations** : le découpage peut ne pas refléter les redécoupages électoraux les
plus récents. À remplacer par un export officiel AN dès disponibilité.

---

## Données des élections agrégées (data.gouv.fr / Ministère de l'Intérieur)

| Aspect | Valeur |
|--------|--------|
| URL dataset | `https://www.data.gouv.fr/datasets/donnees-des-elections-agregees/` |
| Producteur | Ministère de l'Intérieur / data.gouv.fr |
| Format | Parquet — à télécharger manuellement dans `data/exploration/` (les scripts ne téléchargent pas) |
| Auth | Aucune |
| Granularité | Bureau de vote |
| Couverture | 56 scrutins de 1999 à 2026 (euro, pres, legi, regi, muni, dpmt, cant) |
| Volume | ~28 M lignes / 222 MB (deux fichiers Parquet) |
| Filtrage | Hauts-de-France uniquement (code_region = '32') au chargement |
| Scripts | `scripts/load_elections_presidentielles.py`, `load_elections_legislatives.py`, `load_elections_municipales.py` |

Le dataset est distribué en deux fichiers Parquet au nommage contre-intuitif :

### PIÈGE 1 — Nommage inversé des fichiers (CRITIQUE)

| Fichier source | Contenu réel | Table DuckDB cible |
|---------------|-------------|-------------------|
| `general-results.parquet` | Résultats **par candidat** (nom, nuance, voix par bureau) | `resultats_candidats` |
| `candidats-results.parquet` | Données de **participation** (inscrits, votants, abstentions…) | `resultats_participation` |

Ne pas se fier aux noms des fichiers sources. Toujours utiliser les noms de tables DuckDB.

### PIÈGE 2 — Nuances absentes pour les présidentielles récentes

La colonne `nuance` (code partisan) est **entièrement NULL** pour 5 scrutins :

| Élection | Lignes |
|----------|--------|
| 2017_pres_t1 | 761 662 |
| 2017_pres_t2 | 138 484 |
| 2019_euro_t1 | 2 356 098 |
| 2022_pres_t1 | 836 184 |
| 2022_pres_t2 | 139 364 |

Pour les présidentielles 2017 et 2022, le classement par bloc politique est réalisé via la
table `candidats_presidentielle` (jointure sur `nom`). Pour les présidentielles 2002/2007/2012,
la colonne `nuance` contient un **code-candidat** (ex. `CHIR` = Chirac) ; la table
`nuances_harmonisees` assure la correspondance avec les blocs politiques.

### Format des identifiants électoraux

```
id_election = {YYYY}_{type}_{tN}
Exemples :
  2022_pres_t1   → Présidentielle 2022 — 1er tour
  2024_legi_t2   → Législatives 2024 — 2e tour
  1999_euro_t1   → Européennes 1999 — 1er tour
```

Types : `pres`, `legi`, `euro`, `regi`, `muni`, `dpmt`, `cant`.

### Codes INSEE dans le Parquet

- `code_commune` : VARCHAR 5 caractères avec zéro-padding (`'01001'`, `'59606'`) — compatible
  avec `geographies_communes.code_insee`
- `code_departement` : VARCHAR sans padding (`'59'`, `'2A'`, `'971'`)

### Filtrage Hauts-de-France

Les scripts de chargement joignent sur `geographies_communes.code_region = '32'` pour ne
conserver que les communes des 5 départements HdF (02, 59, 60, 62, 80). Ce filtrage
réduit le volume d'un facteur ~10.

**Références** : `reports/exploration-elections-legislatives.md` (exploration des législatives). Le rapport d'exploration initial `reports/exploration-elections.md`, cité dans les versions précédentes de ce document, n'existe pas dans le dépôt.

**Schéma détaillé** : `docs/schema-elections.md`.

---

## Dataset OLAP INSEE — Filosofi + Recensement de la population (data.gouv.fr)

| Aspect | Valeur |
|--------|--------|
| Dataset | « Recensement de la population communal et Filosofi depuis 2015 », id `67289477639527408ae687da` |
| Fichier | `https://static.data.gouv.fr/resources/recensement-de-la-population-communal-et-filosofi-depuis-2015-france-metropolitaine/20241104-093439/donnees-insee-olap.parquet` |
| Format | Parquet, format long (OLAP) : `code_com, nom_commune, annee, source, clef_json, valeur` |
| Volume | 1,73 Go national ; cache HdF local `data/raw/economie/donnees-insee-olap-hdf.parquet` (~40 Mo selon le rapport Phase E) |
| Accès | Lecture distante par DuckDB `httpfs` avec filtre HdF poussé, puis cache local |
| Auth | Aucune |
| Couverture chargée | Filosofi 2017-2021 (`source = 'filosofi_disponible'`) ; RP 2015-2021 (`rp_actifs_emploi`, `rp_logements`) |
| Tables | `economie_filosofi`, `economie_rp` |
| Loaders | `etl/loaders/economie_filosofi.py`, `etl/loaders/economie_rp.py` |

**Pièges** :

- Suffixe RP `_p` = effectif **pondéré**, pas un pourcentage ; `_c` = effectif. Les taux
  sont calculés par le loader (ex. `tx_chomage_dec = chomeurs_15_64_ans_p / actifs_15_64_ans_p`).
- `part_emploi_industriel` = emplois **au lieu de travail** industriels / emplois au lieu
  de travail (et non la population résidente).
- Secret statistique : valeur NULL dans le Parquet → colonne `secret = TRUE` dans DuckDB.
- Le fichier couvre la France métropolitaine (d'après son nom).

---

## CNAF — allocataires du RSA (data.caf.fr)

| Aspect | Valeur |
|--------|--------|
| URL | `https://data.caf.fr/explore/dataset/rsa_s_type_com_f/download/?format=csv` (OpenDataSoft) |
| Format | CSV `;`, UTF-8 |
| Auth | Aucune |
| Granularité | Commune × type de RSA × période (`dtreffre` AAAAMM) |
| Couverture chargée | 2020-2024, snapshot de décembre ; 17 381 lignes HdF (rapport Phase E+) |
| Table | `economie_social` (`nb_foyers_rsa`, `taux_foyers_rsa`) |
| Loader | `etl/loaders/economie_cnaf.py` |

**Pièges** : secret statistique CNAF = arrondi au multiple de 5 (aucun NULL, aucun
drapeau) ; `taux_foyers_rsa` utilise `pop_active` du RP comme dénominateur, donc NULL
après 2021.

---

## DREES — Accessibilité potentielle localisée (APL) aux médecins généralistes

| Aspect | Valeur |
|--------|--------|
| URL | `https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/530_l-accessibilite-potentielle-localisee-apl/attachments/…_xlsx` |
| Format | XLSX multi-onglets (un onglet par millésime), 8 lignes d'en-tête |
| Auth | Aucune |
| Granularité | Commune |
| Couverture chargée | Dernier millésime disponible : 2023 ; 3 788 lignes HdF (rapport Phase E+) |
| Table | `economie_social` (`apl_medecins`, `desert_medical`) |
| Loader | `etl/loaders/economie_drees.py` (pandas + openpyxl, groupe `etl`) |

**Règle** : `desert_medical = TRUE` si APL < 2,5 consultations/habitant/an — 943 communes
HdF en 2023 selon le rapport Phase E+. Upsert `ON CONFLICT` pour coexister avec les
lignes CNAF de même clé.

---

## URSSAF — effectifs salariés et établissements par commune × APE (open.urssaf.fr)

| Aspect | Valeur |
|--------|--------|
| URL | `https://open.urssaf.fr/explore/dataset/etablissements-et-effectifs-salaries-au-niveau-commune-x-ape-last/download/?format=csv` |
| Format | CSV `;`, UTF-8, format large (`effectifs_salaries_AAAA`, `nombre_d_etablissements_AAAA`) |
| Auth | Aucune |
| Champ | Salariés du secteur privé |
| Couverture chargée | 2006-2025 ; 1 157 338 lignes HdF après passage au format long (rapport Phase E+) |
| Table | `economie_emploi_urssaf` ; vue `v_desindustrialisation_commune` |
| Loader | `etl/loaders/economie_urssaf.py` (Polars) |

**Piège** : la vue de désindustrialisation sélectionne les lignes dont le libellé
`secteur_gs` contient « Industrie » (grand secteur `GS1 Industrie`).

---

## Eurostat — contexte macro-économique HdF vs France

| Aspect | Valeur |
|--------|--------|
| URL | `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset}?format=TSV&geo=FRE&geo=FR&sinceTimePeriod=2000` |
| Datasets | `lfst_r_lfu3rt` (taux de chômage BIT) ; `nama_10r_2gdp` (PIB par habitant, remplace `tgs00005`) |
| Format | TSV SDMX (valeurs suivies de drapeaux de qualité) |
| Auth | Aucune |
| Granularité | NUTS2 `FRE` (Hauts-de-France) et `FR` (France) |
| Couverture | Chômage 1999-2025, PIB 2000-2024 selon le rapport Phase E++ ; 104 lignes |
| Table | `economie_contexte` ; vue `v_contexte_hdf_vs_france` |
| Loader | `etl/loaders/economie_eurostat.py` (chargé par `--source eurostat`, hors `all`) |

**Pièges** : drapeaux `u`, `b`, `d`, `p` à retirer, `:` = valeur manquante ; filtres
chômage `isced11=TOTAL, sex=T, age=Y15-74, unit=PC`, PIB `unit=EUR_HAB`. L'API INSEE
BDM/IDBank, envisagée pour la même série, était bloquée par une protection anti-robot
(rapport Phase E++). Écart non résolu : l'URL demande `sinceTimePeriod=2000` alors que le
rapport annonce un chômage depuis 1999.

---

## Datan — historique des députés depuis 2002 (data.gouv.fr)

| Aspect | Valeur |
|--------|--------|
| Dataset | `historique-des-deputes-de-lassemblee-nationale-depuis-2002-informations-et-statistiques` |
| Accès | URL du CSV résolue via `https://www.data.gouv.fr/api/1/datasets/{slug}/` ; URL statique de secours (ressource du 2026-06-17) |
| Producteur | Datan (scores calculés par Datan à partir des données AN) |
| Format | CSV UTF-8, séparateur virgule |
| Auth | Aucune |
| Couverture | Législatures 12 à 17 (2002-présent), France entière ; 2 120 députés, 1 653 lignes d'activité (rapport Phase F) |
| Tables | `leg_elus` (chambre `AN`), `leg_mandats`, `leg_activite` |
| Loader | `etl/loaders/legislatif_datan.py` |

**Limites** : pas de région dans le CSV (`region_nom` NULL) ; une ligne par député,
rattachée à sa dernière législature (`legislatureLast`) et au groupe de celle-ci
(`groupeAbrev`) : aucun historique des groupes (ADR-0011, `leg_mandats.granularite =
'derniere_legislature'`) ; `dateMaj` est une date de mise à jour, pas une fin de mandat
(`date_fin_mandat` NULL) ; scores d'activité uniquement pour l'AN.

---

## Sénat — ODSEN_GENERAL (data.senat.fr)

| Aspect | Valeur |
|--------|--------|
| URL | `https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv` |
| Format | CSV cp1252, séparateur virgule, 18 lignes de commentaires `%` en tête |
| Auth | Aucune |
| Couverture | Sénateurs actifs et anciens, France entière (y compris circonscriptions historiques, codées `XX`) ; 1 945 sénateurs (rapport Phase F) |
| Table | `leg_elus` (chambre `SENAT`), `leg_mandats` |
| Loader | `etl/loaders/legislatif_senat.py` |

**Limites** : pas de score d'activité ; aucune date de mandat (`date_debut_mandat` et
`date_fin_mandat` NULL depuis l'ADR-0011) ; groupe actuel ou dernier seulement, sans
date. Filtre 2002-présent partiel : sont écartés les anciens sénateurs des
circonscriptions disparues (`XX`) et ceux décédés avant le 29/09/2002 ; un filtre exact
exigerait les fichiers de mandats de data.senat.fr (non chargés).

---

## Sources abandonnées

| Source | Module | Raison | Code |
|--------|--------|--------|------|
| NosDéputés.fr (Regards Citoyens) | Législatif | Endpoint de métriques vide depuis la dissolution de juin 2024 | `etl/loaders/legislatif_nosdeputes.py`, non appelé |
| API CLAIR (`api.clair.vote`) | Législatif | HTTP 500 sur tous les endpoints | `etl/loaders/legislatif_clair.py`, non appelé |
| INSEE Sirene | Économie | Prévu par l'ADR-0006 pour l'emploi industriel ; remplacé par le RP (communal) et l'URSSAF (série longue) | — |
| INSEE BDM / IDBank | Économie | Protection anti-robot ; remplacé par Eurostat | — |

## Sources envisagées (non intégrées)

| Source | Module | Données |
|--------|--------|---------|
| data.assemblee-nationale.fr (dumps XML) | Législatif | Votes nominatifs, amendements, dossiers législatifs |
| PISTE — Légifrance / JORF (`api.piste.gouv.fr`) | Législatif | Textes de loi, JO, décrets |
| HATVP open-data (`hatvp.fr/open-data`) | Législatif | Déclarations d'intérêts, patrimoines |
| ANCT (QPV, ZRR, typologies) | Économie | Zonages pour filtrer les territoires |
| Overpass API (OpenStreetMap) | Géographie | POI, équipements locaux |

Pour les sources nécessitant une authentification (PISTE OAuth2, INSEE OAuth2),
les identifiants sont à renseigner dans `.env` — voir `.env.example`.
