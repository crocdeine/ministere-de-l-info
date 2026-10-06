# Vérification sources — Module Législatif

## NosDéputés.fr

### Députés HdF trouvés (liste complète)
L'API (`/deputes/json`) retourne actuellement 52 députés pour les départements des Hauts-de-France (02, 59, 60, 62, 80) rattachés à la législature 2022-2024.
*Note : Suite à la dissolution du 9 juin 2024, tous apparaissent avec une date de `mandat_fin` et ne sont plus actifs au sens strict du terme dans ce jeu de données spécifique.*

| slug | Nom | Prénom | Dept | Circo | Groupe | Actif |
|---|---|---|---|---|---|---|
| paul-christophe | Christophe | Paul | 59 | 14 | HOR | Non (2024-06-09) |
| pierre-vatin | Vatin | Pierre | 60 | 5 | LR | Non (2024-06-09) |
| victor-catteau | Catteau | Victor | 59 | 5 | RN | Non (2024-06-09) |
| pierrick-berteloot | Berteloot | Pierrick | 59 | 15 | RN | Non (2024-06-09) |
| julien-dive | Dive | Julien | 02 | 2 | LR | Non (2024-06-09) |
| *(... et 47 autres députés, liste tronquée pour la lisibilité)* | | | | | | |

### Champs JSON disponibles (profil complet)
Les champs de premier niveau disponibles sur le profil individuel (ex: `/paul-christophe/json`) sont :
`id`, `nom`, `nom_de_famille`, `prenom`, `sexe`, `date_naissance`, `lieu_naissance`, `num_deptmt`, `nom_circo`, `num_circo`, `mandat_debut`, `mandat_fin`, `ancien_depute`, `groupe`, `groupe_sigle`, `parti_ratt_financier`, `responsabilites`, `responsabilites_extra_parlementaires`, `groupes_parlementaires`, `historique_responsabilites`, `sites_web`, `emails`, `adresses`, `collaborateurs`, `autres_mandats`, `anciens_autres_mandats`, `anciens_mandats`, `profession`, `place_en_hemicycle`, `url_an`, `id_an`, `slug`, `url_nosdeputes`, `url_nosdeputes_api`, `nb_mandats`, `twitter`.

### Métriques d'activité (champs exacts)
Les métriques ne sont pas au niveau de la fiche racine du député, mais se trouvent dans l'endpoint de synthèse (`/synthese/data/json`). Voici les valeurs pour Paul Christophe :

| Champ JSON | Type | Signification | Valeur Paul Christophe |
|---|---|---|---|
| semaines_presence | int | Nombre de semaines de présence | 73 |
| commission_presences | int | Présences en commission | 142 |
| commission_interventions | int | Interventions en commission | 623 |
| hemicycle_interventions | int | Interventions dans l'hémicycle | 513 |
| hemicycle_interventions_courtes | int | Interventions courtes dans l'hémicycle | 311 |
| amendements_proposes | int | Amendements proposés | 393 |
| amendements_signes | int | Amendements signés (co-signataire) | 1313 |
| amendements_adoptes | int | Amendements adoptés | 453 |
| rapports | int | Rapports rédigés | 15 |
| propositions_ecrites | int | Propositions de loi écrites | 7 |
| propositions_signees | int | Propositions de loi signées | 57 |
| questions_ecrites | int | Questions écrites au gouvernement | 28 |
| questions_orales | int | Questions orales au gouvernement | 7 |
| *_moyenne_mensuelle | float | Chaque métrique est doublée avec sa moyenne mensuelle calculée | Varie |

### Données mensuelles disponibles ?
**Non**. L'endpoint historique (`/graphes/legislature/json`) ne renvoie plus d'informations ou donne une erreur 404 sur les profils récents de la nouvelle législature.

### Anciens députés accessibles ?
**Oui.** Même si l'endpoint `/deputes/tous/json` retourne une erreur 404, les députés dont le mandat est terminé (ex: dissolution de 2024) sont toujours présents dans `/deputes/json` avec le champ `mandat_fin` renseigné et `ancien_depute = 1`.

### Mapping groupes → blocs HdF
| Groupe sigle | Nom groupe | Bloc proposé |
|---|---|---|
| LFI | La France Insoumise | EXG |
| GDR | Gauche Démocrate et Républicaine | GAU |
| SOC | Socialistes et apparentés | GAU |
| LIOT | Libertés, Indépendants, Outre-mer et Territoires | DIV |
| REN | Renaissance | CENT |
| HOR | Horizons | CENT |
| LR | Les Républicains | DTE |
| RN | Rassemblement National | EXD |

---

## Sénat (data.senat.fr)

### URL CSV directe confirmée
**`https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv`** (Fichier encodé en Windows-1252/Latin-1).

### Colonnes disponibles
`Matricule`, `Qualité`, `Nom usuel`, `Prénom usuel`, `État`, `Date naissance`, `Date de décès`, `Groupe politique`, `Type d'app au grp politique`, `Commission permanente`, `Circonscription` (Département), `Fonction au Bureau du Sénat`, `Courrier électronique`, `PCS INSEE`, `Catégorie professionnelle`, `Description de la profession`.

### Sénateurs HdF (répartition)
On compte actuellement **28 sénateurs actifs** dans les Hauts-de-France, ce qui valide parfaitement l'attendu.
* Aisne (02) : 3
* Nord (59) : 11
* Oise (60) : 4
* Pas-de-Calais (62) : 7
* Somme (80) : 3

*Note : La base contient également des dizaines d'anciens sénateurs (État = `ANCIEN`).*

### Mapping groupes sénatoriaux → blocs
| Nom groupe | Bloc proposé |
|---|---|
| CRCE-K (Communiste, Républicain...) | EXG |
| SER (Socialiste, Écologiste...) | GAU |
| UC (Union Centriste) | CENT |
| Les Indépendants | DTE |
| Les Républicains | DTE |
| NI (Non Inscrits) | DIV |

---

## API CLAIR
### Accessible ? Stable ?
L'API CLAIR est accessible gratuitement et sans clé à l'adresse **`https://api.clair.vote/api/v1`**. Elle répond correctement (endpoint testé : `/api/v1/deputes`).
Cependant, étant un projet relativement récent, sa pérennité à très long terme n'est pas garantie comme celle des institutions officielles.

### Apport vs NosDéputés.fr ?
L'API CLAIR offre de nombreux avantages :
- **Unification Assemblée / Sénat :** Une seule et même structure JSON unifiée, au lieu de requêter NosDéputés pour l'AN et data.senat.fr (CSV) pour le Sénat.
- **Résumés et analyses :** Inclut des données qualitatives (ex: `resumeIA`, `parcoursIA`, `faitsNotablesIA`).
- **Modernité :** Formats de date ISO 8601, structure propre (ex: `votesCount`, `interventionsCount` sous un objet propre plutôt qu'à plat).

### Verdict final
L'API CLAIR est excellente pour prototyper rapidement avec une seule source. Néanmoins, pour un ETL robuste sur le long terme qui ne dépend pas d'un agrégateur tiers, le couplage NosDéputés (API) + Sénat (CSV) reste le standard industriel le plus pérenne.

---

## Schéma DuckDB recommandé

```sql
-- Table des Élus (fusion AN et Sénat)
CREATE TABLE leg_elus (
    id VARCHAR PRIMARY KEY, -- Slug (AN) ou Matricule (Sénat)
    chambre VARCHAR(10), -- 'AN' ou 'SENAT'
    nom VARCHAR,
    prenom VARCHAR,
    sexe VARCHAR(1),
    date_naissance DATE,
    departement_code VARCHAR(3), -- ex: '59'
    departement_nom VARCHAR, -- ex: 'Nord'
    circonscription INT, -- NULL pour les sénateurs
    groupe_sigle VARCHAR,
    bloc_politique VARCHAR(4), -- EXG, GAU, DIV, CENT, DTE, EXD
    date_debut_mandat DATE,
    date_fin_mandat DATE, -- NULL si actif
    est_actif BOOLEAN,
    email VARCHAR,
    profession VARCHAR
);

-- Table des Métriques d'Activité
CREATE TABLE leg_activite (
    elu_id VARCHAR,
    date_extraction DATE,
    semaines_presence INT,
    commission_presences INT,
    commission_interventions INT,
    hemicycle_interventions INT,
    amendements_proposes INT,
    amendements_signes INT,
    amendements_adoptes INT,
    propositions_ecrites INT,
    questions_ecrites INT,
    questions_orales INT,
    rapports INT,
    FOREIGN KEY (elu_id) REFERENCES leg_elus(id)
);
```

## Ordre d'intégration recommandé

1. **Sénat (data.senat.fr CSV)** : Source la plus facile à intégrer en premier. Fichier unique tabulaire (ODSEN_GENERAL.csv), facile à ingérer via l'extension CSV de DuckDB, données très complètes sur les anciens et actifs.
2. **NosDéputés.fr (API JSON)** : À intégrer en second temps. Le traitement est légèrement plus complexe (boucle d'appels JSON, dissociation du profil et de la synthèse des métriques d'activité, etc.).
3. **API CLAIR** : Peut servir de complément ou de source de secours si le parsing NosDéputés devient obsolète avec la 17ème législature.
