# Exploration data.gouv.fr — Module Législatif national

## Datasets AN trouvés
| Nom | Producteur | MAJ | Format | Couvre 17e ? | Métriques ? | URL |
|---|---|---|---|---|---|---|
| Députés actifs de l'Assemblée nationale - Informations et statistiques | Datan | Juin 2026 | CSV | **Oui** | **Oui** (Scores de participation, loyauté, majorité) | [Lien](https://www.data.gouv.fr/datasets/deputes-actifs-de-lassemblee-nationale-informations-et-statistiques) |
| Historique des députés de l'Assemblée nationale (depuis 2002) | Datan | Juin 2026 | CSV | **Oui** (Historique) | **Oui** (Scores historiques) | [Lien](https://www.data.gouv.fr/datasets/historique-des-deputes-de-lassemblee-nationale-depuis-2002-informations-et-statistiques) |
| Amendements déposés à l'Assemblée nationale liés aux PLF et PLFSS | Assemblée nationale | Jan 2020 | XML/JSON (zip) | Non (2018-2020) | Non | [Lien](https://www.data.gouv.fr/datasets/amendements-deposes-a-lassemblee-nationale-lies-aux-plf-et-plfss-2018-2019-2020) |

*Note : La requête "présence députés" et "scrutins assemblée" n'a renvoyé aucun dataset officiel maintenu à jour.*

## Datasets Sénat trouvés
| Nom | Producteur | MAJ | Format | URL |
|---|---|---|---|---|
| Les Sénateurs | Sénat | Dynamique | CSV / JSON / XLS | [Lien](https://www.data.gouv.fr/datasets/les-senateurs) (Redirige vers les dumps `data.senat.fr` tels que `ODSEN_GENERAL.csv`) |

*Note : Les requêtes "sénat votes", "sénateurs activité" et "scrutins sénat" ne renvoient aucun dataset granulaire pré-mâché sur data.gouv.fr.*

## Datasets agrégés tiers
| Nom | Producteur | Fiabilité | URL |
|---|---|---|---|
| Datan (Organisation) | Datan | Haute. Maintient une base à jour avec un mapping propre des groupes et des scores d'activité calculés. | [Lien org](https://www.data.gouv.fr/organizations/datan) |
| Métadonnées des Discours/Rapports publics | Premier ministre (DILA / Vie Publique) | Haute (mais hors sujet) | [Lien](https://www.data.gouv.fr/datasets/metadonnees-des-discours-publics-de-vie-publique-fr) |

*Aucun collectif citoyen (La Fabrique de la Loi, Regards Citoyens) n'a publié d'export CSV réutilisable et maintenu pour la 17e législature concernant les votes ou l'activité.*

## Dumps officiels AN (dernier recours)
Les dumps officiels ne sont pas hébergés sur data.gouv.fr mais sur la plateforme dédiée `data.assemblee-nationale.fr`.
Pour la **17e législature**, l'URL `https://data.assemblee-nationale.fr/acteurs/deputes-en-exercice` propose :
- Un export plat : `liste_deputes_excel.csv` ou `liste_deputes_libre_office.csv` (Situé dans un répertoire racine explicite `/17/amo/...`). C'est la source la plus simple pour avoir la liste exhaustive post-dissolution sans parser de ZIP.
- Les archives complexes : `AMO10_deputes_actifs_mandats_actifs_organes.json.zip` et `AMO40_deputes_actifs_mandats_actifs_organes_divises.json.zip`. Ces archives contiennent les collaborateurs et les appartenances fines aux commissions.

## Sources de votes nominatifs
**Il n'existe actuellement aucune source agrégée ou tabulaire simple (CSV) décrivant "qui a voté quoi" (Scrutins publics)** sur `data.gouv.fr`.
- **L'AN** publie les scrutins bruts uniquement en format XML/JSON très verbeux sur son portail Open Data (`https://data.assemblee-nationale.fr/travaux-parlementaires/scrutins`).
- **Le Sénat** publie une base des scrutins en XML (`Scrutins_Sénat_xxxx.xml`) mais nécessite également un parsing lourd.
- Datan fournit des scores d'alignement mais ne publie pas de table complète des votes nominatifs par député.

## Recommandation finale

1. **Profils 17e législature :**
   Utiliser le dump CSV officiel de l'Assemblée nationale (`liste_deputes_excel.csv`). Il est mis à jour dynamiquement, certifié par l'institution et s'intègre facilement dans DuckDB sans nécessiter d'extraire des ZIP complexes.

2. **Métriques d'activité (Présence, etc.) :**
   Se tourner vers le jeu de données **Datan** ("Députés actifs de l'Assemblée nationale - Informations et statistiques") sur data.gouv.fr. Il est le seul à proposer des indicateurs exploitables (`scoreParticipation`, `scoreLoyaute`, `scoreMajorite`) maintenus à jour pour la législature actuelle, remplaçant avantageusement les comptages morts de NosDéputés.fr.

3. **Votes nominatifs :**
   En l'absence de dataset tiers nettoyé, il n'y a pas d'autre choix que d'ingérer et de parser les dumps **JSON/XML originaux** des scrutins publics de `data.assemblee-nationale.fr`. Cela implique la création d'un script Python dédié pour normaliser la structure des votes (Pour/Contre/Abstention) avant insertion dans `leg_activite` ou une table fille `leg_votes`.
