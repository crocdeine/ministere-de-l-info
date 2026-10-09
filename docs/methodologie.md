# Méthodologie

Cette page explique d'où viennent les chiffres de l'application et comment ils sont calculés. Elle est affichée dans le panneau « Méthodologie » de l'application ; chaque affirmation est suivie de sa source. Les références du type « ADR-0010 » désignent les décisions écrites du projet, conservées dans son dépôt public.

Chiffres mesurés dans la base le 9 octobre 2026.

## Règles de présentation {#garde-fous}

Six règles s'appliquent à toutes les visualisations de l'application :

1. **Méthode affichée.** Sous chaque analyse : le calcul, le dénominateur et la période.
2. **Ruptures signalées.** Toute comparaison entre scrutins signale les changements de périmètre, de seuil de nuançage ou de grille de blocs.
3. **Incertitude visible.** Une estimation n'est jamais présentée comme une mesure.
4. **Corrélation n'est pas causalité.** Rappelé à chaque croisement de données, avec le nombre de communes concernées.
5. **Aucun motif attribué.** Aucune intention n'est prêtée à un comportement électoral (abstention, désistement).
6. **Vocabulaire neutre.** Pas de « bastion », de « vote protestataire » ni de « populiste » ; ni pronostic ni ciblage.

Source : décisions de Mathias du 6 octobre 2026 (orientations du projet, point 2), d'après la synthèse des propositions du 6 octobre 2026, § 3.

Le classement des candidats en blocs politiques est une **convention documentée**, pas un fait : il dépend des grilles publiées par le ministère de l'Intérieur et, quand aucune grille n'existe, d'une reconstruction par le projet, signalée comme telle.

## Sources des données {#sources}

- **Résultats électoraux** : ministère de l'Intérieur, jeu « Données des élections agrégées » publié sur data.gouv.fr, au niveau du bureau de vote, sous Licence Ouverte 2.0.
- **Contours des communes** : IGN, ADMIN-EXPRESS-COG, sous Licence Ouverte 2.0.
- **Fond de carte** : Plan IGN (Géoplateforme), sous Licence Ouverte ; c'est le seul élément chargé depuis Internet, les communes s'affichent sans lui.
- **Communes fusionnées** : code officiel géographique de l'INSEE (mouvements des communes), sous Licence Ouverte 2.0.

Sources : registre des sources du projet ; ADR-0013, décision 5 (fond de carte).

La base de données du projet est diffusée sous licence ODbL 1.0 ; chaque contenu garde la licence de son producteur. Le code est sous licence MIT.

Source : ADR-0013, décision 1.

Tableau complet des sources, généré depuis le registre du projet :

{{sources}}

### Scrutins couverts {#scrutins}

- Présidentielles : 2002, 2007, 2012, 2017, 2022.
- Législatives : 2002, 2007, 2012, 2017, 2022, 2024.
- Municipales : 2008, 2014, 2020, 2026.
- Européennes : 1999, 2004, 2009, 2014, 2019, 2024.
- Régionales : 2004, 2010, 2015, 2021.
- Départementales : 2015, 2021.

Les cantonales (2001-2011) ne sont pas chargées.

Sources : mesure dans la base le 9 octobre 2026 (scrutins ayant des résultats) ; ADR-0010, addendum du 7 octobre 2026.

## Blocs politiques {#blocs}

### Nuance et étiquette {#nuances}

La **nuance politique** est attribuée à chaque candidat ou liste par l'administration (la préfecture). Elle peut différer de l'**étiquette**, que le candidat choisit librement. L'application affiche des nuances regroupées en blocs, jamais des étiquettes.

Source : index des circulaires archivées par le projet, « Contexte ».

Les codes de nuance changent d'un scrutin à l'autre : un même code peut désigner des formations différentes selon l'année. Chaque correspondance est donc établie pour un code **et** une année.

Source : schéma de la base électorale, « Évolution des nuances dans le temps ».

### Les six blocs {#six-blocs}

Les nuances sont regroupées en six blocs, ordonnés de gauche à droite : extrême gauche, gauche, divers, centre, droite, extrême droite. Ce découpage est celui des grilles de « blocs de clivages » du ministère de l'Intérieur. Aucun bloc « centre gauche » ou « centre droit » n'est créé.

Source : circulaire INTA1931378J du 3 février 2020, annexe 3, p. 10 ; ADR-0005 ; ADR-0010, § a.

### Grilles officielles {#grilles}

Trois circulaires, et trois seulement, contiennent une grille de blocs :

| Circulaire | Date | Scrutin | Emplacement de la grille |
|---|---|---|---|
| INTA1931378J | 3 février 2020 | Municipales 2020 | annexe 3, p. 10 |
| IOMA2322276J | 16 août 2023 | Sénatoriales 2023 | annexes 1 et 2, p. 6-7 |
| INTP2602966C | 2 février 2026 | Municipales 2026 | annexe 3, p. 11 et 12 |

Le bloc « divers » s'appelle « AUT » en 2020 et « Autres » en 2023 ; il est enregistré sous le code « DIV ». Les circulaires des législatives 2022 (INTA2212053C) et 2024 (IOMA2415630C) ne contiennent pas de grille de blocs. Les circulaires de nuançage des législatives 2002 à 2017 n'ont pas été publiées au Journal officiel.

Sources : ADR-0010, § a ; index des circulaires archivées par le projet (copies PDF des cinq circulaires citées).

### Étiquette « Grille officielle » ou « Reconstruit » {#methode}

Chaque carte porte une étiquette de méthode :

- **Grille officielle** : une grille du ministère couvre ce scrutin et elle est appliquée telle quelle. C'est le cas des seules municipales 2020 et 2026. Les codes de liste de ces deux scrutins sont identiques aux grilles, code pour code et bloc pour bloc.
- **Reconstruit** : aucune grille officielle ne couvre ce scrutin. Le classement est une reconstruction par le projet, selon la règle décrite ci-dessous. C'est le cas de tous les autres scrutins chargés, dont toutes les présidentielles et législatives.

La grille de 2023 porte sur les sénatoriales, qui ne sont pas chargées : elle ne sert que de grille de référence.

Sources : ADR-0013, décision 3 ; ADR-0010, § a, § b et § d ; vérification du 4 octobre 2026 (rapport « vérification des classements J2 », § 3).

### Règle de reconstruction {#reconstruction}

Pour un scrutin sans grille officielle, le projet applique trois règles, dans l'ordre :

1. Une grille officielle couvre le scrutin : elle s'applique telle quelle.
2. Sinon, on applique la grille officielle la plus proche dans le temps, de préférence antérieure au scrutin, à condition que le code désigne **la même famille politique** dans les deux textes. Si le sens du code a changé, le sens qu'il avait à l'époque du scrutin prime.
3. Si aucune grille ne convient, le classement reconstruit existant est maintenu, avec sa justification écrite.

Grilles de référence qui en découlent : la grille de 2020 pour les scrutins de 1999 à 2022 ; la grille de 2023 pour les législatives et les européennes de 2024, ainsi que pour un code des départementales 2021 absent de la grille de 2020.

Sources : ADR-0010, § b et addendum du 7 octobre 2026.

Un parti est classé dans le bloc qui lui était attribué à la date du scrutin, et non selon un classement actuel.

Source : ADR-0005, décision 3, maintenue par l'ADR-0010.

### Cas particuliers {#cas-particuliers}

- **Écologistes.** Les Verts, EELV et Les Écologistes (codes VEC, LVEC) sont classés à gauche sur tous les scrutins, comme dans les trois grilles. Les autres écologistes (codes ECO, LECO) sont classés en divers, comme dans les grilles, sauf quand le code inclut EELV faute de code distinct : législatives 2017 et 2022, régionales et départementales 2021.
- **Scrutins sans nuance dans la source.** Présidentielles 2017 et 2022, européennes 2019 : la source ne donne pas de nuance. Chaque candidat ou tête de liste est classé individuellement, avec sa justification.
- **Unions.** Une union dont toutes les composantes sont de gauche est classée à gauche. Les unions du centre et de la droite (2021) sont classées à droite.

Sources : ADR-0010, § c et addendum du 7 octobre 2026 (questions Q3, Q5, Q7, Q8) ; schéma de la base électorale, « Nuances NULL pour certains scrutins ».

### Contestations devant le Conseil d'État {#conseil-etat}

Les grilles du ministère peuvent être contestées. Le Conseil d'État a suspendu en 2020 une partie de la circulaire préparant les municipales 2020 (décision n° 437675 du 31 janvier 2020). Il a rejeté en 2026 les recours contre la circulaire des municipales 2026 (décision n° 512694 du 27 février 2026).

Source : index des circulaires archivées par le projet, « Décisions du Conseil d'État » (textes intégraux archivés).

### Non classé {#non-classe}

Certaines voix ne sont rattachées à aucun bloc ; elles sont regroupées sous « non classé » :

- les codes « NC » (municipales 2014 et 2020) et « LNC » (municipales 2020), volontairement laissés sans bloc ;
- les candidats des municipales 2026 sans nuance dans la source, dans les communes sous le seuil de nuançage (3 500 habitants) ;
- trois codes résiduels des européennes 2009 (11 voix au total).

Sources : schéma de la base électorale, table des correspondances et « Municipales 2026 : nuance NULL » ; ADR-0010, addendum du 7 octobre 2026.

### Table des correspondances {#correspondances}

Le 9 octobre 2026, la base compte **384 correspondances** entre un code de nuance et un bloc (172 codes distincts), et **57 classements individuels** de candidats ou de listes sans nuance. Chacune porte sa justification : grille appliquée, règle, décision. La table ci-dessous est lue dans les données de l'application ; elle n'est pas recopiée à la main.

Sources : mesure dans la base le 9 octobre 2026 (tables des correspondances et des candidats) ; ADR-0010.

{{correspondances}}

## Calculs {#calculs}

- **Inscrits** : électeurs inscrits sur les listes électorales.
- **Votants** : inscrits qui ont pris part au vote.
- **Exprimés** : votants moins les bulletins blancs et nuls.
- **Participation** : somme des votants divisée par la somme des inscrits, sur l'ensemble des bureaux de vote de la commune.

Sources : schéma de la base électorale, table de participation ; code électoral, art. L. 65 et L. 66 (blancs et nuls décomptés à part).

### Bulletins blancs et nuls {#blancs-nuls}

Depuis la loi n° 2014-172 du 21 février 2014, les bulletins blancs sont décomptés à part des bulletins nuls. Dans la source utilisée (élections agrégées, data.gouv.fr), les blancs et les nuls ne sont distingués qu'à partir de 2017. Pour les scrutins de 2015 et avant, y compris les européennes et les municipales de 2014 et les départementales et les régionales de 2015, la colonne des blancs est vide et celle des nuls réunit blancs et nuls. Le vote blanc ne peut donc pas être comparé avant 2017, et toute comparaison des nuls doit en tenir compte.

Sources : loi n° 2014-172 du 21 février 2014 ; code électoral, art. L. 65 (blancs) et L. 66 (nuls) ; vérification dans la base par le directeur du projet (lecture seule), octobre 2026.

### Bloc en tête {#bloc-en-tete}

Le **bloc en tête** est le bloc qui totalise le plus de voix dans la commune : on additionne les voix de tous ses candidats ou listes. Ce n'est pas toujours le bloc de la liste arrivée en tête : les deux diffèrent quand plusieurs listes d'un même bloc se partagent les voix.

- **Égalité** entre les premiers : la commune est affichée en blanc ; aucun bloc n'est favorisé.
- **Non classé** en tête : la commune est affichée comme « non classé ».
- **Part du bloc en tête** : voix du bloc divisées par les exprimés. Elle n'est pas affichée quand la somme des voix dépasse les exprimés (communes où l'électeur vote pour plusieurs candidats) : le pourcentage n'aurait pas de sens.

Sources : schéma de la base électorale, « Bloc en tête d'une commune » ; programme d'export des données de l'application.

### Géographie {#geographie}

Les résultats sont présentés dans les communes actuelles. Les résultats d'une commune disparue par fusion sont rattachés à la commune qui l'a absorbée, d'après la table officielle de l'INSEE ; son code d'origine est conservé.

Sources : décision de Mathias du 7 octobre 2026 ; schéma de la base électorale, « Rattachement des communes fusionnées ».

## Valeurs absentes {#valeurs-absentes}

Une absence n'est jamais affichée comme un zéro.

- **n.d.** (non disponible) : la commune a des lignes de résultats, mais sans voix exploitables, y compris quand la source indique 0 voix ; l'infobulle le précise.
- **Aucun scrutin** : la source ne contient aucune ligne pour la commune à ce tour. Exemples : pas de second tour ; commune hors du champ publié, comme les municipales 2008, publiées pour les seules communes de 3 500 habitants et plus.
- **Tours sans résultats** : les tours déclarés dont les résultats ne sont pas chargés sont listés sous la carte.

Sources : schéma de la base électorale, « Bloc en tête d'une commune » ; programme d'export des données de l'application.

## Ruptures entre scrutins {#ruptures}

Comparer deux scrutins demande de la prudence. L'application affiche une mention « Limite » quand on passe d'un type de scrutin à un autre, ou d'une grille officielle à un classement reconstruit.

- **Types de scrutin.** Mode de scrutin, offre électorale et nombre de tours diffèrent d'une élection à l'autre.
- **Changements de grille.** Une même formation peut changer de bloc d'une grille à l'autre. La France insoumise est classée à gauche dans les grilles de 2020 et de 2023, et à l'extrême gauche dans celle de 2026. L'UDI est classée au centre en 2020 et en 2026, à droite en 2023.
- **Codes de nuance.** Les codes changent à chaque circulaire ; seule la comparaison par bloc reste possible sur longue période.
- **Seuil de nuançage.** Aux municipales 2020 et 2026, seules les listes des communes de 3 500 habitants et plus et des chefs-lieux d'arrondissement reçoivent une nuance.
- **Circonscriptions.** Les législatives 2002 et 2007 ont eu lieu avant le redécoupage de 2010.
- **Blancs et nuls.** La source ne les distingue qu'à partir de 2017 : avant, les nuls incluent les blancs (voir « Bulletins blancs et nuls »).

Sources : schéma de la base électorale, « Classements — blocs politiques » et vues législatives ; ADR-0010, § e, point 4 ; index des circulaires archivées par le projet ; vérification dans la base (blancs et nuls), octobre 2026.

## Limites connues {#limites}

- **Communes partagées entre circonscriptions.** Pour les législatives 2002, 2007 et 2024, la source ne donne pas la circonscription : elle est reconstruite, et une commune partagée entre plusieurs circonscriptions (Paris, Marseille…) est rattachée à une seule. Limite acceptée par Mathias le 7 octobre 2026.
- **Contours des circonscriptions.** Ils ne sont pas officiels : ils sont publiés par un particulier sur data.gouv.fr.
- **Scissions de communes.** Elles sont recensées, mais les voix ne sont jamais réparties entre les communes issues de la scission.
- **Électeurs écartés.** Français de l'étranger et collectivités d'outre-mer absentes du référentiel des communes (Pacifique, Saint-Martin, Saint-Barthélemy).
- **Clé des correspondances.** Elle combine le code et l'année, sans le type de scrutin. Un contrôle empêche qu'une année de municipales soit partagée avec une présidentielle ou des législatives.
- **Écologistes 2022.** Le code ECO des législatives 2022 inclut EELV dans la circulaire, mais la plupart des candidats EELV étaient nuancés NUP. Son classement à gauche reste à confirmer au vu des candidats concernés.

Sources : schéma de la base électorale, « Rattachement des communes fusionnées », « Contrôles de chargement » et vues législatives ; registre des sources du projet (contours des circonscriptions) ; ADR-0010, § e, points 2 et 3.

## Glossaire {#glossaire}

| Terme | Définition |
|---|---|
| Abstention | Inscrits qui n'ont pas voté. |
| Bloc | Regroupement de nuances en six familles, de l'extrême gauche à l'extrême droite (voir « Blocs politiques »). |
| Bloc en tête | Bloc qui totalise le plus de voix dans la commune (voir « Bloc en tête »). |
| Bureau de vote | Lieu de vote ; niveau le plus fin des résultats publiés. |
| Circonscription | Territoire qui élit un député aux législatives. |
| Code INSEE | Code à cinq caractères qui identifie une commune ; il diffère du code postal. |
| Commune nouvelle | Commune issue de la fusion de plusieurs communes. |
| EPCI | Établissement public de coopération intercommunale : groupement de communes (communauté de communes, d'agglomération, urbaine, métropole). |
| Étiquette | Appartenance politique déclarée par le candidat lui-même. |
| Exprimés | Votants moins les bulletins blancs et nuls. |
| Grille de blocs | Tableau du ministère de l'Intérieur qui range chaque nuance dans un bloc. |
| Inscrits | Électeurs inscrits sur les listes électorales. |
| n.d. | Non disponible : donnée absente ou inexploitable, jamais remplacée par zéro. |
| Nuance | Classement politique attribué par l'administration à un candidat ou à une liste. |
| Participation | Votants divisés par les inscrits. |
| Scrutin de liste | Élection où l'on vote pour une liste de candidats et non pour une personne. |
| Tour | Chacun des deux votes d'une même élection ; le second tour n'a pas toujours lieu. |
| Votants | Inscrits qui ont pris part au vote. |

Sources : schéma de la base électorale ; code électoral, art. L. 65 et L. 66 ; définitions de l'INSEE (code commune, EPCI).
