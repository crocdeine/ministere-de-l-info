# Analyse technique des formats — Module Économie HdF

## Matrice de compatibilité
| Source | Format | Encodage | Lecture DuckDB | Transformation requise | Complexité |
|---|---|---|---|---|---|
| INSEE Filosofi | CSV / Parquet | UTF-8 (majorité) | Oui (`read_csv` / `read_parquet`) | Préciser `delim=';'`, typer Code Insee en `VARCHAR` | Faible |
| INSEE RP | CSV / Parquet | UTF-8 | Oui | Typer Code Insee en `VARCHAR` | Faible |
| INSEE BPE | CSV / Parquet | UTF-8 | Oui | Agréger par commune si au niveau équipement | Moyenne |
| data.gouv.fr | Parquet / CSV | UTF-8 | Oui | Typer Code Insee en `VARCHAR` | Faible |

## Détail par source

### INSEE Filosofi (revenus/pauvreté)
- **Format** : Historiquement et très fréquemment distribué en **CSV** (parfois zippé), mais l'INSEE commence à proposer des versions **Parquet** pour les gros volumes.
- **Séparateur** : Le fichier CSV Insee utilise typiquement le point-virgule (`;`) et non la virgule.
- **Encodage** : Encodage standard en **UTF-8**, ce qui évite les soucis avec les toponymes accentués.
- **Codes géographiques** : Identifiant standard (Code Commune INSEE sur 5 caractères).

### INSEE Recensement de la Population
- **Format** : Les bases détaillées (individus localisés) sont volumineuses. Elles sont diffusées en **CSV** (souvent à importer par morceaux ou avec précaution dans Excel) et, de plus en plus, en **Parquet**.
- **Structure** : Il existe des fichiers de "tableaux" (statistiques pré-agrégées par commune) et des "fichiers détails". Ces derniers requièrent des groupements (ex: par code commune) lors de l'ETL.

### data.gouv.fr données économiques
- **Format** : Transition massive vers le format **Parquet** (ex : base Sirene des entreprises et établissements). Le CSV reste présent pour les tables de plus petites dimensions.
- **Compatibilité** : Optimale avec DuckDB et Polars, permettant des requêtes performantes directement sur les fichiers Parquet locaux ou distants.

### Autres sources (Base permanente des équipements - BPE)
- **Format** : Disponible en CSV, dBase, et Parquet pour des millésimes récents.
- **Structure** : Fournit soit des fichiers de comptage (déjà agrégés par commune), soit des données géolocalisées à l'échelle de l'équipement, nécessitant un regroupement lors du traitement ETL.

## Pièges identifiés et solutions proposées
1. **Zéros initiaux des codes Insee**
   - *Problème* : Les codes communes (ex: `02001` dans l'Aisne) perdent leur zéro s'ils sont inférés comme entiers (`INT`). La jointure avec les données existantes échouera.
   - *Solution* : Lors du `read_csv` ou via Polars, forcer explicitement le typage de la colonne en chaîne de caractères (`VARCHAR` / `String`).
2. **Valeurs manquantes et secret statistique**
   - *Problème* : L'Insee utilise fréquemment `"s"` (secret statistique) ou `"nd"` (non disponible) dans les colonnes numériques, ce qui pousse les moteurs à typer la colonne entière en `VARCHAR`.
   - *Solution* : Configurer l'ingestion avec DuckDB/Polars pour interpréter ces valeurs comme des `NULL` (ex. paramètre `nullstr=['s', 'nd']` ou traitement de remplacement avant le cast numérique).
3. **Cas de Paris, Lyon, Marseille (PLM)**
   - *Problème* : Les données peuvent être soit consolidées sous le code commune global (ex: `75056` pour Paris), soit éclatées par arrondissement (`75101` à `75120`).
   - *Solution* : Vérifier l'échelle et, si besoin, effectuer une somme/moyenne pondérée pour retomber sur l'échelle choisie dans la base existante.
4. **Fusions de communes (Communes nouvelles)**
   - *Problème* : Le référentiel (Code Officiel Géographique - COG) évolue chaque année. Un fichier de 2018 n'aura pas la même liste de codes communes qu'un fichier de 2023.
   - *Solution* : S'assurer du millésime de la donnée et utiliser une table de passage du COG si l'on souhaite tout ramener à la géographie d'une année de référence.

## Volumes estimés (HdF filtré)
- **Taille de l'univers HdF** : ~3782 communes.
- **Volume téléchargé (brut)** : Les bases nationales détaillées (RP, Sirene) pèsent facilement de plusieurs centaines de Mégaoctets à quelques Gigaoctets.
- **Volume dans DuckDB** : Une fois la donnée filtrée sur les seules ~3782 communes des Hauts-de-France et agrégée à la maille communale, le volume par jeu de données sera infime (quelques Mo au maximum).

## Recommandations pour le script ETL
1. **Adopter le format Parquet :** Privilégier systématiquement les URLs Parquet sur data.gouv.fr et le site de l'INSEE.
2. **Pousser les filtres à la source (Pushdown) :** Avec DuckDB ou Polars (en mode `LazyFrame`), appliquer la clause de filtre spatial (ex: `WHERE code_commune LIKE '02%' OR code_commune LIKE '59%'...` ou via une jointure avec la table des communes) *dès la lecture*. Cela évitera de charger les bases nationales en RAM.
3. **Schéma explicite :** Ne pas se reposer sur l'inférence de types pour le CSV de l'INSEE. Définir un schéma de lecture strict dans Polars/DuckDB, spécialement pour protéger les `code_commune` et nettoyer les secrets statistiques.
