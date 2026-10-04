# Licence de la base de données

Le **code** de ce dépôt est sous licence MIT (fichier `LICENSE`).

La **base de données** distribuée avec l'outil (`ministere.duckdb`, publiée dans les
releases GitHub) est mise à disposition sous la
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
Ce choix est imposé par les données URSSAF, elles-mêmes sous ODbL : toute base dérivée
doit être rediffusée sous la même licence (partage à l'identique).

Les contenus individuels de la base restent soumis à la licence de leur producteur.
Toute réutilisation doit citer les sources ci-dessous.

| Données | Producteur | Licence |
|---|---|---|
| Contours administratifs (ADMIN-EXPRESS-COG) | IGN | Licence Ouverte 2.0 |
| Contours des circonscriptions législatives (non officiels) | J. Desboeufs, via data.gouv.fr | Licence Ouverte 2.0 |
| Populations légales | INSEE | Licence Ouverte 2.0 |
| Filosofi et recensement (fichier republié) | INSEE, republié par T. Szczurek-Gayant sur data.gouv.fr | Licence Ouverte 2.0 |
| Foyers allocataires du RSA | CNAF | Licence Ouverte 2.0 |
| Accessibilité potentielle localisée (APL) | DREES | Licence Ouverte 2.0 |
| Établissements et effectifs salariés | URSSAF | ODbL 1.0 |
| Chômage BIT régional, PIB par habitant | Eurostat | CC BY 4.0 (politique de réutilisation de la Commission) |
| Résultats électoraux agrégés | Ministère de l'Intérieur, via data.gouv.fr | Licence Ouverte 2.0 |
| Députés et scores d'activité | Datan, d'après l'Assemblée nationale | Licence Ouverte 1.0 |
| Sénateurs (ODSEN_GENERAL) | Sénat | Licence data.senat.fr (Licence Ouverte) |

Les classements politiques (nuances → blocs) sont des choix documentés du projet
(`docs/adr/0005`, `0010`, `0011`) ; seules les municipales 2020 et 2026 suivent une grille
officielle telle quelle. Détail et état de vérification des licences : `docs/sources.md`.
