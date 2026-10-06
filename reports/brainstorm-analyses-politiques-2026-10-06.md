# Brainstorm — Nouvelles fonctionnalités d'analyse politique

**Date** : 2026-10-06
**Rôle** : politiste / analyste électoral (lecture seule ; base ouverte en `read_only=True`)
**Nature** : propositions, aucune implémentation. Prolonge `brainstorm-nouvelles-fonctionnalites-2026-08-19.md`
(sources, benchmark, croisements) sans le répéter : ici, on parle des **analyses** à offrir à l'utilisateur.

## Résumé exécutif

1. L'essentiel de la valeur est **déjà en base** : participation et résultats par bureau de vote (≈ 6 500 BV,
   5 départements, 30 scrutins), blocs harmonisés, élus AN/Sénat, indicateurs communaux.
2. Cinq analyses indispensables, toutes faisables sans nouvelle source sauf la France entière :
   abstention, cartes d'évolution entre deux scrutins, comparaison commune ↔ département ↔ région ↔ France,
   qualifications et triangulaires, fiche « élu actuel et son élection ».
3. Le principal risque n'est pas technique : c'est la **lecture abusive** (carte qui surreprésente les communes
   rurales, corrélation lue comme cause, report de voix estimé lu comme observé). Six garde-fous transverses
   sont proposés (§ 2) et devraient être adoptés avant tout développement.
4. Les reports de voix et la simulation de sièges sont classés **ambitieux** : méthode lourde, incertitude
   forte, risque de neutralité élevé. À réserver à une page « Méthodes » clairement séparée.
5. Écartés : tout pronostic (projection, « circonscriptions gagnables »), tout ciblage, toute étiquette normative.
6. Données à ajouter, par ordre d'utilité : résultats France entière (même jeu data.gouv), européennes et
   régionales HdF (même jeu), table de passage des communes (INSEE), contours des bureaux de vote.

---

## 1. Ce que la base permet réellement (vérifié le 2026-10-06)

| Constat | Conséquence pour les analyses |
|---|---|
| 30 scrutins chargés : présidentielles et législatives 2002-2024, municipales 2008-2026, HdF uniquement (02, 59, 60, 62, 80) | Pas de point de comparaison « France » en base |
| Européennes, régionales, départementales, cantonales : déclarées dans `elections`, **0 ligne** de résultats | Comparaisons inter-scrutins limitées à 3 types |
| Résultats et participation au **bureau de vote** (≈ 6 200 à 6 550 BV selon les années) | Analyses fines possibles, mais les BV changent de périmètre d'un scrutin à l'autre |
| Pas de contours de bureaux de vote en base | Pas de carte au BV, seulement des tableaux/graphiques |
| `code_circo` présent pour les législatives seulement ; drapeau `ancien_decoupage` (redécoupage 2010) | Évolutions par circo à couper en 2012 |
| `sexe` des candidats : renseigné 2017+ (législatives, présidentielles), municipales 2008, 2020, 2026 t2 ; **absent** 2002-2014 législ./présid., 2014 muni, 2026 muni t1 | Parité : séries courtes, trous à afficher |
| `nuance` 2026 muni t1 renseignée à 65 % (petites communes sans nuance) ; municipales 2008 : 164 communes seulement | Municipales comparables surtout 2014-2026, communes ≥ 1 000 hab. |
| Pas d'identifiant stable de candidat entre scrutins ; `leg_mandats` porte la nuance préfectorale d'élection | Sortants : rapprochement par nom + circo + année, à contrôler |
| Économie : Filosofi 2017-2021 (3 541 communes, secret statistique), RP, populations 2013-2023 | Millésimes économiques ≠ années d'élection : décalage à afficher |

## 2. Garde-fous transverses (à adopter une fois pour toutes)

| # | Garde-fou | Pourquoi |
|---|---|---|
| G1 | **Toujours dire la base du pourcentage** : % des exprimés **et** % des inscrits disponibles côte à côte | Une progression en % exprimés peut être une baisse en voix quand l'abstention monte |
| G2 | **Effectifs visibles** : nombre d'inscrits et de voix dans chaque infobulle ; seuil minimal (ex. 100 inscrits) en dessous duquel une commune est grisée dans les classements et les cartes d'évolution | Petites communes = variations de ±20 points sans signification |
| G3 | **Carte pondérée par la population** en option (cercles proportionnels ou cartogramme) à côté de la carte par surface | La carte par surface donne l'avantage visuel aux blocs implantés dans les communes rurales étendues |
| G4 | **Mention de nomenclature** quand deux scrutins comparés n'utilisent pas la même grille de blocs (ADR-0010 : grille 2020 appliquée à 2002-2022, 2023 à 2024, 2026 à 2026) | Une évolution peut venir d'un changement de classement, pas du vote |
| G5 | **Encadré « Ce que ce graphique ne dit pas »** sur les croisements, estimations et simulations (corrélation ≠ causalité, estimation ≠ observation, simulation ≠ prévision) | Principe « informer, pas plaider » |
| G6 | **Vocabulaire neutre** : « constance » plutôt que « bastion », « écart » plutôt que « circonscription disputée/gagnable », « bloc en tête » plutôt que « bloc dominant » quand il n'a pas la majorité absolue | Les mots portent des conclusions |

---

## 3. Niveau 1 — Indispensables

| # | Fonctionnalité | Question à laquelle elle répond | Représentation | Données | Effort | Risque | Garde-fou |
|---|---|---|---|---|---|---|---|
| I1 | **Géographie de l'abstention** (et du vote blanc et nul) | Où vote-t-on le moins, et cela change-t-il selon le type de scrutin ? | Carte communale du taux d'abstention (classes fixes, comme J3) ; courbe 2002-2026 par type de scrutin ; barres abstention / blancs / nuls / exprimés en % des inscrits | En base (`resultats_participation`) | S | Moyen : l'abstention mesurée ignore les non-inscrits et les « mal-inscrits » ; blancs comptés à part seulement depuis 2014 | Note fixe « % des inscrits sur les listes, hors non-inscrits » ; rupture de série 2014 signalée sur la courbe |
| I2 | **Cartes d'évolution entre deux scrutins** (progression/recul par commune) | Où un bloc, ou la participation, a-t-il le plus progressé ou reculé entre deux élections ? | Carte en palette divergente centrée sur 0 (écart en points) ; liste des plus fortes hausses/baisses ; choix « points d'exprimés » / « points d'inscrits » | En base. Table de passage des communes (communes nouvelles) **à ajouter** pour 2002-2026 | M | Élevé : changements de nomenclature, fusions de communes, comparaison de types de scrutins différents (présidentielle vs municipale) | Par défaut, même type de scrutin seulement ; G1, G2, G4 ; communes fusionnées signalées |
| I3 | **Comparaison commune ↔ département ↔ région ↔ France** | Ma commune vote-t-elle comme son département, sa région, le pays ? | Barres groupées par bloc pour les 4 niveaux ; « écart à la moyenne » en points ; petit tableau | Département et région : agrégation de la base. France : **à ajouter** (même jeu data.gouv « élections agrégées », niveau département suffit) | S (HdF) / M (France) | Faible : addition simple ; risque de lire un écart comme anomalie | Écart affiché en points avec effectifs ; pas de couleur rouge/vert (pas de jugement) |
| I4 | **Qualifications et triangulaires** (législatives ; maintien/fusion aux municipales) | Combien de candidats franchissent le seuil, combien de triangulaires, de désistements ? | Tableau par circo : qualifiés, configuration du 2nd tour (duel, triangulaire, quadrangulaire), désistements constatés ; frise 2002-2024 du nombre de triangulaires | En base. Seuils légaux à coder : 12,5 % des **inscrits** aux législatives (art. L162 code électoral) ; municipales ≥ 1 000 hab. : 10 % des exprimés pour se maintenir, 5 % pour fusionner (seuil ≥ 3 500 hab. avant 2014) | M | Moyen : un « désistement » se déduit (qualifié au 1er tour, absent au 2nd) ; on ne connaît pas son motif ; fusions de listes non tracées | Libellé « absent du 2nd tour bien que qualifié », jamais « retrait en faveur de… » ; seuil légal et article cités |
| I5 | **Élu actuel et son élection** (par circonscription) | Qui représente ce territoire, avec quel score et quelle marge ? | Fiche circo : député en exercice, bloc, score 1er et 2nd tour, écart en voix et en points, participation ; pour les remplaçants, mention et élection du titulaire | En base (`v_elus_actuels`, `leg_mandats`, `v_scores_circo_legi`). Sénateurs : élection indirecte, **pas de données** de grands électeurs → afficher « élu au suffrage indirect », sans score | S-M | Moyen : rapprochement élu ↔ candidat par nom (homonymies) ; élus de partielles absents des résultats généraux | Rapprochement vérifié et tracé ; « élu lors d'une élection partielle, résultats non disponibles » plutôt qu'un vide |

## 4. Niveau 2 — Utiles

| # | Fonctionnalité | Question | Représentation | Données | Effort | Risque | Garde-fou |
|---|---|---|---|---|---|---|---|
| U1 | **Sortants et réélections** (prolonge l'axe 3 du brainstorm du 19 août) | Quelle part des députés sortants se représente, est réélue ? Quel renouvellement par législature ? | Tableau de flux par législature : sortant non candidat / battu / réélu ; barres par bloc | En base (`leg_mandats` × `resultats_candidats` législ.). Municipales : RNE (déjà identifié le 19 août) | M | Moyen : homonymies, changements de circo après 2010, candidats sous une autre nuance | Table de correspondance relue à la main et versionnée ; cas incertains listés à part |
| U2 | **Écarts de victoire** | Où l'élection s'est-elle jouée à peu de voix ? | Histogramme des écarts du 2nd tour ; tableau trié par écart en voix | En base | S | Moyen : glisse facilement vers « circonscriptions à prendre » (pronostic) | G6 ; pas de liste « à surveiller » ; seulement le passé constaté |
| U3 | **Constance et volatilité** | Les communes changent-elles souvent de bloc en tête ? Quel volume de voix bouge d'un scrutin à l'autre ? | Indice de volatilité de Pedersen (somme des écarts de scores / 2) par commune, en carte ; frise « bloc en tête » par commune sur 5 scrutins | En base | M | Moyen : « bastion » est un mot militant ; la volatilité nette sous-estime les mouvements réels d'électeurs | G6 (« constance ») ; note « mesure les soldes, pas les électeurs individuels » ; G2 |
| U4 | **Croisements socio-électoraux généralisés** (étend `v_croisement_eco_elections`) | Les communes plus pauvres, plus ouvrières, plus touchées par le chômage votent-elles différemment ? | Nuage de points commune par commune, taille = inscrits ; coefficient de corrélation de rang (Spearman) avec n ; pas de droite de régression par défaut | En base. Millésimes : Filosofi 2017-2021, RP | M | **Élevé** : erreur écologique (une commune pauvre qui vote X ≠ les pauvres votent X) ; secret statistique ; décalage d'années | G5 obligatoire en haut du graphique ; communes secrètes exclues et comptées ; année de l'indicateur affichée à côté de l'année d'élection |
| U5 | **Profils de bureaux de vote dans une commune** | Comment les quartiers d'une même ville votent-ils les uns par rapport aux autres ? | Barres empilées par BV, triées ; écart de chaque BV à la moyenne communale ; participation par BV | En base. Carte au BV : contours **à ajouter** (data.gouv, contours de BV issus du REU) | S (tableau) / L (carte) | Moyen : périmètres de BV modifiés entre scrutins ; usage possible pour du ciblage de campagne | Pas de comparaison temporelle au BV sans contrôle de périmètre ; pas de classement « BV les plus favorables à… » |
| U6 | **Parité des candidatures et des élus** | Quelle part de femmes parmi les candidats et les élus, selon le bloc et le scrutin ? | Barres par bloc et par année ; part des femmes au 1er tour vs parmi les élus | En base pour 2017+ (et municipales 2008, 2020, 2026 t2). 2002-2014 : sexe **à ajouter** depuis les fichiers de candidats du ministère (à vérifier) | S | Moyen : séries trouées ; tentation de déduire le sexe du prénom | Ne jamais déduire du prénom ; années sans donnée affichées « n.d. » ; rappel des lois sur la parité (contexte, pas jugement) |
| U7 | **Effet taille de commune et densité** | Le vote diffère-t-il entre grandes villes, villes moyennes, bourgs et villages ? | Barres par strate (grille communale de densité INSEE ou tranches de population) | Population en base ; grille de densité **à ajouter** (INSEE, petit fichier) | S | Moyen : la strate est corrélée à d'autres facteurs | G5 ; seuils de strates fixes et documentés |
| U8 | **Fragmentation de l'offre et du vote** | L'offre électorale se fragmente-t-elle ? Le vote se concentre-t-il ? | Nombre de candidats/listes ; « nombre effectif de partis » (Laakso-Taagepera) par commune/circo, en frise | En base | S | Faible ; indicateur technique peu connu | Définition en une phrase et exemple chiffré |
| U9 | **Écart présidentielle ↔ législatives de la même année** | Les électeurs d'une commune votent-ils pareil à quelques semaines d'écart ? | Carte divergente de l'écart de score par bloc (2002, 2007, 2012, 2017, 2022) et de participation | En base | S | Moyen : offre différente (pas de candidat de chaque bloc partout aux législatives) | Comparaison seulement là où le bloc était présent aux deux ; mention de l'offre |
| U10 | **Homogénéité territoriale du vote** | Le vote d'un bloc est-il uniforme sur le territoire ou concentré dans quelques zones ? | Écart-type / coefficient de variation du score entre communes, en frise par bloc | En base | S | Faible | Pondération par inscrits ; définition affichée |

## 5. Niveau 3 — Ambitieuses

| # | Fonctionnalité | Question | Représentation | Données | Effort | Risque | Garde-fou |
|---|---|---|---|---|---|---|---|
| A1 | **Estimation des reports de voix entre tours** (voir § 6) | D'où viennent, en moyenne, les voix du 2nd tour ? | Matrice de transfert (1er tour en lignes, 2nd tour + abstention en colonnes) avec **intervalles** ; diagramme de flux seulement avec bandes d'incertitude | En base (BV, deux tours). Bibliothèque d'inférence écologique **à ajouter** (ex. PyEI, dépendance lourde) | L | **Très élevé** : estimation lue comme fait ; résultats instables ; hypothèses rarement vérifiées | Page « Méthodes » séparée ; intervalles toujours visibles ; mention « estimation statistique, non observée » ; pas d'estimation à la commune |
| A2 | **Simulation de répartition des sièges** | (a) Les sièges du conseil municipal correspondent-ils aux voix (prime majoritaire) ? (b) Quelle répartition donnerait un autre mode de scrutin ? | (a) Hémicycle par commune ; (b) hémicycle comparatif « réel / simulé » | (a) Règle CGCT (prime de 50 %, seuil 5 %) + taille du conseil selon la population légale : calculable. (b) En base | M (a) / L (b) | (a) Faible : application d'une règle. (b) **Très élevé** : les électeurs auraient voté autrement sous un autre mode ; sujet en débat public (le choix du mode affiché vaut prise de position) | (a) Comparer au résultat officiel (RNE) et signaler les écarts. (b) À ne faire **qu'avec accord de Mathias**, plusieurs modes à égalité, bandeau « exercice arithmétique, pas une prévision » |
| A3 | **Typologie des communes ou des BV** (classification automatique) | Quels profils socio-électoraux types existent dans la région ? | Carte de types ; profil moyen de chaque type | En base ; à l'IRIS, Filosofi IRIS **à ajouter** (IRIS ≠ BV : correspondance approximative) | L | Élevé : les noms de types deviennent des étiquettes ; résultats sensibles aux choix de variables | Types nommés par leurs caractéristiques chiffrées, pas par des adjectifs ; variables et méthode affichées ; stabilité testée |
| A4 | **Trajectoires longues 2002-2026 par commune** | Comment une commune a-t-elle évolué sur 25 ans, tous scrutins confondus ? | Petits multiples (une courbe par bloc) ou « slope chart » 2002 → 2024 | En base ; européennes/régionales **à ajouter** pour combler les trous ; table de passage des communes | M-L | Élevé : mélange de types de scrutins et de grilles | Une couleur de point par type de scrutin ; G4 ; option « même type seulement » |
| A5 | **Détecteur d'anomalies de saisie** (usage interne) | Y a-t-il des BV aux chiffres incohérents (votants > inscrits, exprimés ≠ somme des voix) ? | Tableau de contrôles | En base | S | Faible, mais un « BV anormal » affiché publiquement suggérerait une fraude | Usage interne et qualité des données seulement ; jamais publié comme analyse |

## 6. Focus — reports de voix : ce qu'on peut dire honnêtement

- **Problème** : le vote est secret ; on connaît, par BV, les totaux du 1er et du 2nd tour, jamais le parcours
  d'un électeur. Toute « matrice de reports » est une **inférence écologique** : on déduit un comportement
  individuel de totaux agrégés.
- **Méthodes** : régression de Goodman (simple, peut donner des taux impossibles, < 0 % ou > 100 %) ; méthode
  de King (bornes + modèle statistique) ; modèles bayésiens multicatégories dits « R×C » (les plus défendables,
  mais lents et sensibles aux réglages).
- **Hypothèse clé, souvent fausse** : les taux de report seraient à peu près les mêmes dans tous les BV.
  Si les électeurs d'un même bloc se comportent différemment en ville et à la campagne, l'estimation est biaisée,
  et l'intervalle ne le montre pas forcément.
- **Autres pièges** : abstentionnistes du 1er tour qui votent au 2nd (à traiter comme une catégorie à part) ;
  configurations de 2nd tour différentes selon les circonscriptions (à estimer séparément) ; pas de donnée de
  référence ouverte pour valider (les enquêtes sortie des urnes des instituts ne sont pas des données ouvertes).
- **Proposition** : étape 1 (niveau 2, effort S) = nuage de points **descriptif** par BV, « score du candidat
  éliminé au 1er tour » contre « progression du finaliste », sans calcul de taux. Étape 2 (niveau 3) =
  estimation R×C seulement pour HdF entier, intervalles affichés, page Méthodes, et accord de Mathias.

## 7. Écarté explicitement

| Idée | Raison |
|---|---|
| Projection de résultats futurs, « swing uniforme » appliqué à un prochain scrutin | Pronostic |
| Liste de « circonscriptions gagnables », « communes à reconquérir », « BV prioritaires » | Recommandation et ciblage de campagne |
| Agrégateur de sondages | Hors périmètre (résultats définitifs seulement) ; méthodologie contestée |
| Score idéologique gauche-droite calculé des élus | Classification reconstruite présentée comme mesure ; contraire à l'ADR-0005/0010 |
| Indicateurs étiquetés « vote protestataire », « vote populiste », « vote sanction » | Interprétation normative intégrée à la mesure |
| Explication causale (« le chômage explique le vote X ») | Données agrégées : la causalité n'est pas démontrable ici |
| Publication de BV « suspects » | Insinuation de fraude sans fondement juridique |

## 8. Données à ajouter (par ordre d'utilité)

| Donnée | Pour | Source | Effort ETL |
|---|---|---|---|
| Résultats France entière au niveau département | I3, A4 | data.gouv « élections agrégées » (déjà la source) — simple levée du filtre HdF à l'agrégat | S |
| Européennes 2019/2024, régionales 2015/2021, départementales 2015/2021 (HdF) | I1, I2, A4 | Même jeu ; lignes déjà prévues dans `elections` | M (nuances et blocs à classer selon l'ADR-0010) |
| Table de passage des communes (communes nouvelles, fusions) | I2, U3, A4 | INSEE, COG | S |
| Grille communale de densité | U7 | INSEE | S |
| Contours des bureaux de vote | U5 (carte) | data.gouv (contours issus du REU, Etalab) — couverture à vérifier | M-L |
| Sexe des candidats 2002-2014 | U6 | Fichiers de candidats du ministère (data.gouv) — à vérifier | S-M |
| Taille légale des conseils municipaux | A2 (a) | Calculable (CGCT art. L2121-2) | S |

## 9. Questions fermées pour Mathias

1. Adopter les six garde-fous transverses (§ 2) comme règle de toutes les futures analyses ? (oui / non / à amender)
2. Charger les résultats France entière au niveau département pour la comparaison I3 ? (oui / HdF seulement)
3. Reports de voix : s'en tenir à l'étape descriptive, ou prévoir l'estimation R×C ? (descriptif seul / les deux)
4. Simulation de sièges sous un autre mode de scrutin (A2 b) : l'écarter ou l'étudier ? (écarter / étudier)
