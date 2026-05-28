# 0005 — Nomenclature officielle des blocs politiques du Ministère de l'Intérieur

Date : 2026-05-29
Statut : Accepté

## Contexte

Le module Élections doit classer chaque candidat et chaque nuance par bloc politique
pour produire des visualisations comparables sur 25 ans (2002–2026). Ce classement
exige une règle stable, objectivable et vérifiable par un tiers.

La conception initiale (C2a) utilisait 7 blocs "maison" (dont un bloc "écologistes"
absent de toute classification officielle) et un classement au jugement sans traçabilité
explicite. Cela introduit une subjectivité non documentée, difficilement défendable.

## Décision

1. **Blocs officiels** : adopter exactement les 6 blocs de clivages du Ministère de
   l'Intérieur tels que définis dans la circulaire IOMA2322276J (sénatoriales 2023),
   qui est la première à formaliser ce regroupement.

   | Code | Libellé | Ordre |
   |------|---------|-------|
   | EXG | Extrême gauche | 1 |
   | GAU | Gauche | 2 |
   | DIV | Divers | 3 |
   | CENT | Centre | 4 |
   | DTE | Droite | 5 |
   | EXD | Extrême droite | 6 |

2. **Double couche** : la nuance officielle (attribuée par les préfets) est le socle
   factuel. Le bloc est la couche d'agrégation, dérivée de la nuance.

3. **Classement "officiel de l'époque"** : un parti est classé dans le bloc qui lui
   était attribué à la date du scrutin. La grille de classification évolue d'une
   circulaire à l'autre ; on n'applique jamais une grille rétroactivement.
   Exemple : LFI classé GAU en 2017, 2022 (circulaire 2023 confirme GAU) ; classé
   EXG seulement à partir de 2026 (circulaire INTP2602966C).

4. **Reconstruction sourcée avant 2023** : le regroupement officiel en blocs n'existe
   qu'à partir des sénatoriales 2023. Pour les scrutins antérieurs (présidentielles
   2002/2007/2012), le bloc est reconstruit en appliquant la logique des circulaires
   disponibles, avec une justification explicite par candidat (colonne `source_bloc`).

5. **Traçabilité** : les circulaires PDF sont archivées dans
   `docs/sources-officielles/nuances/`. Chaque entrée dans `candidats_presidentielle`
   et `nuances_harmonisees` porte une référence à la circulaire ou décision CE
   utilisée comme source.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|-----------------|
| **Blocs "maison" (C2a)** | Subjectifs, non reproductibles, absence de source vérifiable. Le bloc "écologistes" n'existe dans aucune classification officielle. |
| **Classement académique CEVIPOF** | Riche en nuance mais sans série homogène de 2002 à 2026. Chaque étude utilise sa propre grille. Non compatible avec un pipeline automatisé. |
| **Application rétroactive de la grille 2026** | Anachronique : classer Mélenchon 2012 en EXG parce que LFI est EXG en 2026 est une erreur d'interprétation historique. |
| **Pas de classement par bloc** | Empêche les agrégations et comparaisons temporelles qui constituent la valeur centrale du module. |

## Conséquences

**Positives :**
- Objectivité maximale : tout classement est justifiable par un texte officiel.
- Traçabilité : la source de chaque classement est conservée dans la base.
- Maintenabilité : un nouveau scrutin = une nouvelle circulaire = mise à jour de la table
  de référence sans modifier le code métier.

**À accepter :**
- On hérite des choix de l'État, parfois contestés (cf. contentieux CE sur RN et DLF).
  Ces contentieux sont eux-mêmes documentés et font partie de la traçabilité.
- Les classements changent dans le temps (FI : GAU → EXG) ; c'est une donnée historique,
  non un bug. La clé `(nuance, annee)` dans `nuances_harmonisees` en est la conséquence.
- La grille officielle exclut un bloc "écologistes" distinct : EELV/Verts sont classés
  GAU (allié de gauche historique) et Cap21/Génération Écologie en CENT ou DIV selon
  la circulaire de référence.

## Réversibilité

Un classement = une ligne dans une table de référence (`candidats_presidentielle` ou
`nuances_harmonisees`). Il est modifiable sans toucher aux données brutes ni à la
logique de chargement. Toute modification doit être accompagnée d'une mise à jour de
la colonne `source_bloc` et d'un commit motivé.
