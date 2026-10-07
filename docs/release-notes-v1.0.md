# Ministère de l'Info 1.0.1 — notes de version (2026-10-07)

## Pour qui

Un petit cercle de lecteurs qui veulent explorer, sur leur Mac, les résultats électoraux, les
indicateurs économiques et la composition du Parlement, sans compétence technique.

## Ce que fait l'application

- **Géographie** : régions, départements, intercommunalités, communes, circonscriptions ;
  population 2013, 2018 et 2023.
- **Élections** : France entière, 1999-2026, 48 scrutins (présidentielles, législatives,
  municipales, européennes, régionales, départementales), jusqu'au bureau de vote ; communes
  fusionnées rattachées à leur commune actuelle ; classement des nuances en six blocs, sources officielles tracées.
- **Économie** : revenus, pauvreté, chômage, emploi industriel, logement social, prestations
  sociales, accès aux médecins ; croisement avec les votes.
- **Législatif** : députés (législatures 12 à 17) et sénateurs, groupes classés par législature.

## Installation

Ouvrir le Terminal (Applications > Utilitaires), coller, appuyer sur Entrée :

```
curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/v1.0.1/install.sh | bash
```

Une icône « Ministère de l'Info » apparaît dans le dossier Applications de votre dossier
personnel. Double-clic : l'application s'ouvre dans le navigateur. Aucun mot de passe, aucun
compte. Mise à jour : relancer la même commande. Désinstallation : même commande avec
`uninstall.sh` au lieu de `install.sh`. Mode d'emploi : `docs/guide-utilisateur.md`.

## Limites

- Mac uniquement. Testé sur Mac Apple Silicon ; Mac Intel non testé.
- 3 Go d'espace libre nécessaires à l'installation, 1,9 Go occupés ensuite ; connexion Internet
  nécessaire à l'installation, pas à l'usage (sauf fond de carte).
- L'application ne fonctionne que sur l'ordinateur où elle est installée (adresse 127.0.0.1).
- Données figées à la date de la base publiée (`db-2026-10-07`) ; les groupes du Sénat issus du
  renouvellement du 27 septembre 2026 ne sont pas encore intégrés.
- Icône générique (pas de logo).

## Données et licences

Code sous licence MIT. Base de données sous licence ODbL (`LICENSE-DONNEES.md`) ; sources et
mentions obligatoires dans `docs/sources.md` (Ministère de l'Intérieur, INSEE, IGN, Assemblée
nationale, Sénat, Datan, CNAF, DREES, URSSAF, Eurostat). Fond de carte : Plan IGN.

## Application non signée : sans conséquence

L'application n'est pas signée par Apple. Cela n'a pas d'effet ici : l'icône est fabriquée sur
votre Mac par l'installateur, et non téléchargée, donc macOS n'affiche aucun avertissement
« développeur non identifié ».
