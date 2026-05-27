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

## Sources prévues (modules futurs)

| Source | Module cible | Données |
|--------|-------------|---------|
| INSEE Sirene (`portail-api.insee.fr`) | `Économie` | Établissements, entreprises |
| PISTE — Légifrance / JORF (`api.piste.gouv.fr`) | `Législatif` | Textes de loi, JO, décrets |
| Banque de France Webstat | `Économie` | Séries macroéconomiques |
| data.gouv.fr / Ministère de l'Intérieur | `Élections` | Résultats électoraux par bureau de vote |
| HATVP open-data (`hatvp.fr/open-data`) | `Élus` | Déclarations d'intérêts, patrimoines |
| data.assemblee-nationale.fr | `Législatif` | Votes, amendements, dossiers législatifs |
| NosDéputés / NosSénateurs (Regards Citoyens) | `Élus` | Mandats, présences, groupes |
| Overpass API (OpenStreetMap) | `Géographie` | POI, équipements locaux |

Pour les sources nécessitant une authentification (INSEE Sirene OAuth2, PISTE OAuth2),
les identifiants sont à renseigner dans `.env` — voir `.env.example`.
