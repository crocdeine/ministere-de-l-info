# Exploration sources — Module Législatif

## Synthèse comparative

| Source | Format | Auth | Indicateurs clés | Complexité ETL | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **data.assemblee-nationale.fr** | JSON/XML (Zip) | Non | Votes, amendements, questions, profils, présences | Moyenne à Haute | **À intégrer** (Données brutes de référence) |
| **data.senat.fr** | Dumps SQL / CSV | Non | Votes, présences, amendements, sénateurs | Moyenne | **À intégrer** (via CSV) |
| **NosDéputés.fr** | API REST (JSON) | Non | Activité (commissions, hémicycle, amendements, questions) | Faible | **À intégrer** (pour le score d'activité) |
| **NosSénateurs.fr** | API REST (JSON) | Non | - | - | **API instable/Écarté** (Erreur 500/HTML renvoyé) |
| **data.gouv.fr / API CLAIR** | API REST (JSON) | Non | Agrégation multichambres (AN + Sénat) | Faible | **Alternative recommandée** |

---

## Assemblée nationale (data.assemblee-nationale.fr)

**Nom et URL :** Open Data de l'Assemblée nationale — [https://data.assemblee-nationale.fr](https://data.assemblee-nationale.fr)
**Format exact :** Fichiers statiques XML et JSON compressés dans des archives ZIP (ex: `AMO10_deputes_actifs.json.zip`). Ce n'est pas une API REST dynamique mais un portail de téléchargement de dumps (Open Data).
**Authentification requise :** Non
**Indicateurs disponibles :**
- Acteurs (Profils détaillés : nom, circo, groupe, mandats)
- Scrutins (Votes individuels en séance publique)
- Amendements (Auteur, contenu, sort)
- Questions (QAG, écrites)
- Dossiers législatifs et rapports
**Granularité :** Par député (profil), par vote (pour ou contre à un scrutin), par texte de loi.
**Couverture temporelle :** Par législature complète (archives distinctes pour la 15e, 16e, etc.).
**Facilité d'intégration ETL :** **Moyenne à haute**. Nécessite de télécharger des archives ZIP, de les décompresser et de parser des hiérarchies JSON/XML complexes.
**Verdict :** À intégrer comme source de vérité (Raw Layer), mais nécessite un travail de modélisation pour croiser les IDs des députés avec leurs votes.

---

## Sénat (data.senat.fr)

**Nom et URL :** Open Data du Sénat — [https://data.senat.fr/les-senateurs/](https://data.senat.fr/les-senateurs/)
**Format exact :** Dumps de base de données complets (fichiers SQL PostgreSQL compressés) et extraits thématiques tabulaires (CSV). L'API native REST n'existe pas.
**Authentification requise :** Non
**Indicateurs disponibles :**
- Sénateurs (Mandats, appartenances politiques, circonscriptions)
- Travaux législatifs (Dosleg)
- Amendements (Ameli)
- Questions et Comptes rendus
**Granularité :** Par sénateur, par amendement, par question.
**Couverture temporelle :** Session en cours et archives historiques.
**Facilité d'intégration ETL :** **Moyenne**. L'utilisation des extraits CSV rend l'intégration dans DuckDB/dbt assez fluide, mais le croisement complexe des votes nécessiterait l'import du dump PostgreSQL complet.
**Verdict :** À intégrer. Privilégier les extraits CSV pour les profils.

---

## NosDéputés.fr / NosSénateurs.fr

**Nom et URL :** Projet de Regards Citoyens — [https://www.nosdeputes.fr/api](https://www.nosdeputes.fr/api)
**Format exact :** API REST en JSON (`/deputes/json` ou `/<slug>/json`).
**Authentification requise :** Non
**Indicateurs disponibles :**
- Profils députés avec identifiants croisés (AN, Twitter).
- "Score d'activité" détaillé : Semaines de présence, participations en commission, interventions en hémicycle, amendements (proposés, signés, adoptés), rapports, questions (écrites/orales).
**Granularité :** Par député (synthèse globale par législature ou mensuelle).
**Couverture temporelle :** Temps réel / Législature en cours.
**Facilité d'intégration ETL :** **Faible**. C'est une API JSON très bien structurée et facile à consommer.
**Verdict :** **NosDéputés.fr est à intégrer** en priorité pour récupérer facilement les KPIs d'activité. Cependant, **NosSénateurs.fr est instable** (l'API renvoie souvent du HTML d'erreur à la place du JSON) et doit être écarté.

---

## data.gouv.fr datasets parlementaires

**Nom et URL :** Dépôts et agrégateurs tiers sur data.gouv.fr
**Format exact :** CSV, API REST (JSON-LD)
**Indicateurs disponibles :** Des projets comme **API CLAIR** ou **Eutyn** regroupent et retraitent les données des deux chambres (Sénat et AN) en une seule API unifiée pour les votes, les amendements et les profils.
**Facilité d'intégration ETL :** **Faible**. Beaucoup plus simple que de traiter les fichiers XML bruts des sites officiels.
**Verdict :** **Recommandé** pour enrichir la donnée ou si l'extraction des ZIP officiels de l'AN devient un goulot d'étranglement ETL.

---

## Sources écartées

- **NosSénateurs.fr** : Rejeté pour instabilité technique (erreurs JSON fréquentes).
- **Wikidata / SPARQL** : Rejeté dans un premier temps. Bien que la modélisation sémantique soit riche, les API NosDéputés ou les CSV du Sénat sont beaucoup plus robustes et à jour concernant le travail législatif pur (votes, amendements).

---

## Recommandation d'architecture

Pour intégrer ces données dans le projet **ministere-de-l-info** tout en limitant la complexité ETL, voici l'architecture recommandée via **DuckDB + dbt** :

1. **Bronze Layer (Ingestion) :**
   - API `NosDéputés.fr` (Endpoints `/deputes/json` et `/<slug>/json`) aspirés via un script Python/Bash vers du JSON local.
   - Extraits `CSV` du Sénat téléchargés directement via requêtes HTTP `GET`.
   - Si les votes nominatifs précis sont requis, télécharger le `AMO10_scrutins.json.zip` de data.assemblee-nationale.fr.
2. **Silver Layer (Nettoyage via DuckDB) :**
   - Utiliser `read_json_auto()` de DuckDB pour aplanir les données NosDéputés.
   - Utiliser `read_csv_auto()` pour le Sénat.
   - Créer un modèle unique de table `elus_hdf` standardisant les colonnes (chambre, id_elu, nom, prenom, departement, groupe_politique).
3. **Gold Layer (Croisement) :**
   - Jointure entre le référentiel des élus et leurs statistiques d'activité.
   - Classification des groupes politiques selon la norme des 6 blocs (EXG / GAU / DIV / CENT / DTE / EXD).

---

## Données HdF vérifiées empiriquement

### Test 1 & 2 : NosDéputés.fr (16e législature)

L'API NosDéputés.fr a identifié avec succès **52 députés** rattachés aux départements des Hauts-de-France (02, 59, 60, 62, 80).

*Échantillon de députés remontés :*
- **Paul Christophe** (Groupe HOR - Horizons)
- **Pierre Vatin** (Groupe LR - Les Républicains)
- **Victor Catteau** (Groupe RN - Rassemblement National)
- **Pierrick Berteloot** (Groupe RN)
- **Julien Dive** (Groupe LR)

*Test d'indicateurs de participation (Exemple : Paul Christophe) :*
- Participations en commission : 142
- Interventions en hémicycle : 513
- Amendements signés : 1313
- Questions orales : 7

### Test 3 : Sénat
Le scraping historique ne fonctionnant pas car le site `senat.fr` met régulièrement à jour sa structure de recherche (actuellement sur `/senateurs/index.html`), il faut s'appuyer sur le téléchargement officiel du jeu de données CSV à l'adresse `https://data.senat.fr/les-senateurs/` pour filtrer les départements du Nord (59). Le format CSV garantit un chargement direct dans l'ETL sans maintenance d'un scraper HTML.
