# Sources de données

Référence des sources utilisées ou prévues. Pour le flux d'ingestion, voir
[docs/architecture.md](architecture.md).

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
| URL | `https://api.insee.fr/melodi/file` |
| Dataset | `DS_POPULATIONS_HISTORIQUES` |
| Format | JSON (clé `value`, tableau de séries temporelles) |
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

---

## Données des élections agrégées (data.gouv.fr / Ministère de l'Intérieur)

| Aspect | Valeur |
|--------|--------|
| URL dataset | `https://www.data.gouv.fr/datasets/donnees-des-elections-agregees/` |
| Producteur | Ministère de l'Intérieur / data.gouv.fr |
| Format | Parquet (téléchargement direct) |
| Auth | Aucune |
| Granularité | Bureau de vote |
| Couverture | 56 scrutins de 1999 à 2026 (euro, pres, legi, regi, muni, dpmt, cant) |
| Volume | ~28 M lignes / 222 MB (deux fichiers Parquet) |
| Filtrage | Hauts-de-France uniquement (code_region = '32') au chargement |
| Module cible | `scripts/load_elections.py` (C2b) |

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

Le chargement (C2b) jointure sur `geographies_communes.code_region = '32'` pour ne
conserver que les communes des 5 départements HdF (02, 59, 60, 62, 80). Ce filtrage
réduit le volume d'un facteur ~10.

**Référence** : `reports/exploration-elections.md` — analyse structurelle complète des Parquet.

**Schéma détaillé** : `docs/schema-elections.md`.

---

## Sources prévues (modules futurs)

| Source | Module cible | Données |
|--------|-------------|---------|
| INSEE Sirene (`portail-api.insee.fr`) | `Économie` | Établissements, entreprises |
| PISTE — Légifrance / JORF (`api.piste.gouv.fr`) | `Législatif` | Textes de loi, JO, décrets |
| Banque de France Webstat | `Économie` | Séries macroéconomiques |
| HATVP open-data (`hatvp.fr/open-data`) | `Élus` | Déclarations d'intérêts, patrimoines |
| data.assemblee-nationale.fr | `Législatif` | Votes, amendements, dossiers législatifs |
| NosDéputés / NosSénateurs (Regards Citoyens) | `Élus` | Mandats, présences, groupes |
| Overpass API (OpenStreetMap) | `Géographie` | POI, équipements locaux |

Pour les sources nécessitant une authentification (INSEE Sirene OAuth2, PISTE OAuth2),
les identifiants sont à renseigner dans `.env` — voir `.env.example`.
