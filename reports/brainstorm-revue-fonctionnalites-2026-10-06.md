# Revue des fonctionnalités en place, module par module — 2026-10-06

**Rôle** : analyste produit, lecture seule. **Base** : branche `poc/tauri` @ `e19ff1b`, base `data/ministere.duckdb` ouverte en `read_only=True`.
**Lu** : `CLAUDE.md`, `docs/orientations.md`, `docs/guide-utilisateur.md`, `docs/audit-2026-10-04.md`, `docs/roadmap.md`, résumés de `reports/ux-2026-09-24.md`, `reports/brainstorm-nouvelles-fonctionnalites-2026-08-19.md`, `reports/rd-feuille-de-route-2026-09-24.md`, `reports/ui-lisibilite-j3-2026-10-06.md` ; code de `app.py`, `pages/`, `src/ministere_de_l_info/pages/`, `src/ministere_de_l_info/viz/`.

## Résumé exécutif

1. Les calculs sont devenus fiables (J1-J4). Le défaut principal est fonctionnel : l'outil répond à « que montre cette source ? » et pas encore à « que s'est-il passé dans ce territoire ? ».
2. Aucune URL partageable, aucun clic carte → détail, aucune recherche globale : `query_params`, `on_select` et `last_object_clicked` n'apparaissent nulle part dans le code.
3. On ne peut pas voir l'historique électoral d'une commune : l'évolution existe seulement pour la circonscription 21 du Nord, pour une circonscription législative ou pour toute la région.
4. Les noms des candidats sont en base (934 258 lignes), mais présidentielles et législatives n'affichent que des blocs. Le député élu d'une circonscription n'apparaît pas dans Élections.
5. Européennes, régionales, départementales et cantonales sont déclarées dans la table `elections`, mais aucun résultat n'est chargé.
6. Le croisement Économie × Élections se limite aux présidentielles (en pratique 2022, parfois 2017). Il n'affiche aucun coefficient. On ne peut l'exporter nulle part.
7. Législatif : bonne fiche député. Mais les onglets sont tous calculés à chaque clic, aucun export n'existe, et l'historique ne garde que la dernière législature de chaque député.
8. Les priorités des audits de septembre restent valables et ne sont pas faites : fiche territoire, URL partageables, Méthodologie/glossaire. Elles conditionnent la plupart des compléments ci-dessous.
9. Pour la cible Tauri : URL d'état, fiche territoire et export doivent être pensés dès la maquette, et pas ajoutés après coup.

---

## 0. Ce qui a été fait depuis les rapports précédents, et ce qui reste valable

| Piste (rapport d'origine) | État au 2026-10-06 | Preuve |
|---|---|---|
| QW1 Onglets paresseux (UX 09-24) | **Fait** pour Élections et Économie ; **pas fait** pour Législatif | `pages/2_🗳️_Élections.py:35-51`, `pages/economie.py:841-856` ; `pages/legislatif.py:495-508` (`st.tabs` sans `on_change`) |
| QW2 Participation pondérée | **Fait** | `viz/elections_queries.py:24` (`taux_participation_agrege`) |
| QW5 Recherche député + classement complet | **Fait** | `pages/legislatif.py:188-247`, `:318-330` |
| QW6 Croisement : années exploitables, choix du tour | **Fait** ; coefficient r **non fait** | `pages/economie.py:614-641` ; pas de `corr` dans le code |
| QW7 Géographie sans limite de lignes + CSV | **Fait** | `pages/1_📍_Géographie.py:246-264` |
| QW10 Périmètre affiché sur les tuiles d'Accueil | **Fait** | `pages/0_🏠_Accueil.py:36-74` |
| QW11 `help=` sur le jargon | **Très partiel** (0 dans Législatif, 1 à 2 par page ailleurs) | `grep -c help=` |
| QW12 / F10 Export d'image Plotly avec source | **Non fait** | pas de `toImageButtonOptions` |
| QW14 Palette selon le sens de l'indicateur | Remplacée par des classes fixes (J3) | `reports/ui-lisibilite-j3-2026-10-06.md` |
| F1 Fiche commune, F2 recherche, F3 URL, F4 clic carte, F5 méthodologie (UX) / TR1, TR3, TR4 (R&D) | **Non faits**, toujours prioritaires | `grep query_params\|on_select` → 0 |
| F11 Résultats par candidat, F12 fiche élu | F12 **fait** (dans l'onglet Activité) ; F11 **non fait** | `pages/legislatif.py:188` |
| Municipales en % (I8), échelles fixes (I7), n.d. au lieu de 0 (I6) | **Faits** (J2-J3) | `pages/elections_municipales.py:176-224`, `viz/maps_elections.py:233-236` |
| EL1 Européennes, EL5 indicateurs dérivés, LG1 député × circonscription (R&D) | **Non faits** ; données présentes pour EL5 et LG1 | voir §3 et §4 |
| Brainstorm 08-19 « sortant réélu », « volatilité généralisée » | **Non faits** ; toujours réalisables sans nouvelle source | `v_evolution_blocs_circo21` reste câblée sur une seule circonscription |

---

## 1. Accueil

**Parcours réel** : 4 tuiles (module, description, périmètre) → lien vers la page. Puis le tableau des sources, licences et dates de chargement. Puis un volet « Diagnostic technique ».

**Ce qui marche** : le périmètre de chaque module est annoncé (`pages/0_🏠_Accueil.py:41-63`). Le tableau des sources est complet, avec licence et date (`:76-91`). C'est un vrai acquis de J1.

**Lacunes et frictions**
- Aucun point d'entrée par question ou par territoire : pas de champ « Ma commune », pas de lien vers une analyse préréglée (`:67-74`).
- Le « Diagnostic technique » affiche un tableau fictif « France, 67 000 000 habitants » (`:102-103`). C'est un reste de gabarit, sans intérêt pour l'utilisateur, et il peut tromper.
- Aucune date de fraîcheur par module sur les tuiles. Elle figure seulement dans le tableau des sources, plus bas.

| Complément | Valeur | Effort | Données | Risque neutralité |
|---|---|---|---|---|
| A1. Champ de recherche « commune, circonscription, élu » qui ouvre la fiche territoire (voir T2) | Entrée directe pour 80 % des usages | S (après T1) | En base | Aucun |
| A2. 4 ou 5 « analyses guidées » préréglées (ex. « participation 2002-2022 », « blocs en tête par circonscription 2024 ») | Rend l'outil lisible par un non-expert | S (après T3 URL) | En base | **Moyen** : choix des questions. Formulation par blocs, sans présupposé (décision du 2026-10-04) |
| A3. Retirer le tableau fictif du diagnostic (`:102-103`) | Propreté | S | — | Aucun |
| A4. Date de la donnée la plus récente sur chaque tuile | Confiance | S | `_etl_metadata` | Aucun |

---

## 2. Géographie

**Parcours réel** : barre latérale → niveau (6 niveaux), année (2013/2018/2023), comparaison facultative, filtres département et région → carte Folium → tableau triable → CSV.

**Ce qui marche** : couverture nationale. Classes fixes (J3). Évolution démographique avec une palette accessible. Export CSV. « n.d. » explicite (`pages/1_📍_Géographie.py:246-264`). Les circonscriptions sont bien marquées « non officiel » sur la carte (`viz/maps.py:268-272`).

**Lacunes et frictions**
- Aucune recherche de commune par nom : il faut choisir un département, puis chercher dans le tableau (`:131-137`).
- Pas de clic sur la carte (`:188`, `returned_objects=[]`).
- Circonscriptions et arrondissements : contours seuls, sans population (`:47-52`, pas de vue population pour ces niveaux).
- La légende sous la carte dit « Géométries : data.geopf.fr » pour tous les niveaux, circonscriptions comprises (`:211`). Elle contredit la mention de la carte (`viz/maps.py:269`).
- La page ne sert qu'à la démographie. Aucun lien vers l'élection ou l'économie du territoire affiché.
- La population comptée à part et la population totale sont en base (colonnes des vues `v_population_*`), mais ne sont pas affichées.

| Complément | Valeur | Effort | Données | Risque neutralité |
|---|---|---|---|---|
| G1. Corriger la légende du bas pour les circonscriptions (`:211`) | Exactitude de la source | S | — | Aucun |
| G2. Population par circonscription (somme des communes, avec la règle annoncée pour les communes coupées) | Contexte des législatives | M | En base (jointure spatiale déjà utilisée par l'ETL) | Faible : méthode de répartition à documenter |
| G3. Clic sur une entité → fiche territoire | Geste attendu | M | En base | Aucun |
| G4. Colonnes « densité » et « population totale » dans le tableau | Analyse urbain/rural | S | Surface calculable (`ST_Area` en Lambert-93) ; population totale en base | Aucun |
| G5. Grille communale de densité INSEE (rural / urbain), réutilisable partout | Clé de lecture de tous les croisements | S-M | **Nouvelle source** (R&D GE3) | Faible : millésime du zonage à dater |

---

## 3. Élections

### 3.1 Présidentielles (2002-2022)

**Parcours réel** : année, tour, zone (« 21e circonscription du Nord » ou « Hauts-de-France »), mode de carte (bloc dominant ou score d'un bloc) → 4 métriques → carte → évolution de la zone → tableau par commune (voix) + CSV → bureaux de vote d'une commune + CSV.

**Ce qui marche** : participation pondérée. Légende honnête sur l'origine du classement (`_blocs_politiques.py:50-68`). Échelle fixe 0-100 %. Détail par bureau de vote. Exports CSV.

**Lacunes et frictions**
- Seulement deux zones : la circonscription 21 (héritage du prototype) ou toute la région (`elections_presidentielles.py:36-39`). Pas de vue par département ni par circonscription.
- **Aucun nom de candidat** : tout est agrégé en blocs (`:111`, `get_scores_communes`). Le 2e tour 2022 ne dit pas « Macron / Le Pen ». Les noms sont pourtant en base (`resultats_candidats.nom`, `candidats_presidentielle`).
- L'évolution porte sur la zone, jamais sur la commune choisie dans le bloc « bureaux de vote » (`:192`, `:315-379`).
- Le tableau par commune est en voix brutes, sans part des exprimés (`:233-235`). Les comparaisons entre communes de tailles différentes sont donc difficiles.
- Blancs et nuls sont en base (26 032 lignes), mais pas affichés.
- Aucune carte d'écart entre deux scrutins.

### 3.2 Législatives (2002-2024)

**Parcours réel** : année, tour, circonscription (ou « toutes ») → vue régionale (carte des circonscriptions, tableau récapitulatif par bloc, évolution) ou vue d'une circonscription (carte des communes, barres par bloc, évolution, détail par nuance, bureaux de vote).

**Ce qui marche** : avertissement clair sur l'ancien découpage 2002-2007 (`elections_legislatives.py:44-52`). Zone grisée sur le graphique. Note sur le 2e tour (`:458`).

**Lacunes et frictions**
- La colonne « Circos gagnées » compte le **bloc arrivé en tête** (`:169-174`, `:186-187`). Au 1er tour, ce n'est pas une victoire : peu de sièges sont pourvus au 1er tour. Le libellé est faux.
- La vue d'une circonscription n'a pas de métrique de participation (`:240-243`), alors que `v_participation_circo_legi` existe.
- « Détail par nuance » sans candidat ni élu (`:289-300`). Pas de lien vers le député (Législatif) alors que la jointure est possible : `leg_mandats.code_departement` + `num_circo` ↔ `code_circo` « 59-21 ».
- L'évolution est disponible par circonscription : c'est la seule échelle infrarégionale où l'historique existe.

### 3.3 Municipales (2008-2026)

**Parcours réel** : scrutin → avertissement sur le seuil de nuançage → carte du bloc dominant → évolution régionale (1er tour, %) → détail d'une commune (métriques, blocs, listes avec tête de liste, CSV).

**Ce qui marche** : avertissements très complets sur les seuils (`elections_municipales.py:30-63`). Note sur la nuance LFI (`:73-79`). Part des voix non classées affichée (`:226-240`). Seule page avec les têtes de liste.

**Lacunes et frictions**
- La commune choisie est perdue quand on change de scrutin : la clé dépend de l'année (`:255`). On ne peut pas suivre une commune de 2008 à 2026.
- Une seule carte (bloc dominant, `:141-161`) : ni score d'un bloc, ni participation.
- Aucune information sur l'issue (liste élue, sièges). Le rapport du 2026-08-19 pointait déjà le RNE.
- Formulation « a annulé un seuil initial de 9 000 hab. » (`:53-54`) : l'audit (§ Mineurs) signale que la décision du Conseil d'État a **suspendu** ce seuil. À vérifier et corriger.

### 3.4 Compléments Élections

| Complément | Valeur | Effort | Données | Risque neutralité |
|---|---|---|---|---|
| E1. **Historique électoral d'une commune** : tous scrutins et tours, part des blocs et participation, sur un seul graphique | Question n°1 des profils citoyen et élu | M | En base | Faible : changement de seuil et de grille à annoter (notes déjà rédigées) |
| E2. **Résultats par candidat** (présidentielles, législatives) à côté des blocs ; élu de la circonscription | Lisibilité grand public ; vérifiable | M | En base (`resultats_candidats`, `candidats_presidentielle`) | Faible : ordre d'affichage neutre (voix décroissantes ou numéro de panneau) |
| E3. Corriger « Circos gagnées » → « Circonscriptions où le bloc est en tête » (`elections_legislatives.py:187`). Au 2e tour : « sièges » | Exactitude | S | — | **Élevé tant que ce n'est pas corrigé** (gonfle un bloc) |
| E4. Zone présidentielle par département et par circonscription (remplacer le cas codé en dur de la circonscription 21) | Échelle d'analyse utile | M | Communes → circonscription disponible par la jointure de l'ETL législatif | Faible : communes coupées (environ 11 % des inscrits) à signaler, comme pour 2002-2007 |
| E5. Carte d'écart entre deux scrutins (« swing » en points pour un bloc), palette divergente | Où le vote a bougé | M | En base | Moyen : comparer seulement à périmètre constant (même type de scrutin, même découpage) |
| E6. Parts des exprimés dans le tableau par commune + blancs et nuls | Comparaisons justes | S | En base | Aucun |
| E7. Lien circonscription ↔ député (Élections → Législatif) | Relie deux modules | S-M | En base ; `leg_mandats` = dernière législature seulement (voir L3) | Faible |
| E8. Municipales : garder la commune entre scrutins ; carte du score d'un bloc et de la participation | Suivi d'une commune | S | En base | Aucun |
| E9. Européennes 1999-2024 et régionales 2004-2021 | Comparaison « à la proportionnelle » des blocs | M-L | Déclarées dans `elections`, **0 résultat chargé** ; disponibles dans la source Parquet déjà utilisée | **Élevé** : classement des listes en blocs sans grille officielle (ADR-0010) ; nécessite l'accord de Mathias |
| E10. Indicateurs dérivés (volatilité de Pedersen, bascules de bloc en tête, écart à la moyenne régionale) | Analyse sérieuse sans nouvelle source | M | En base | Moyen : formules publiées et documentées ; effet de taille des petites communes |

---

## 4. Législatif

**Parcours réel** : barre latérale (chambre, département ou « Hauts-de-France ») → 4 onglets : composition (camembert + métriques), liste des élus (recherche texte), activité (fiche député, top 20, classement complet, moyennes par bloc), évolution par législature.

**Ce qui marche** : périmètre national. Fondement du classement affiché par mandat (`legislatif.py:234-246`). Règle des non-inscrits expliquée (`:175-180`). Avertissement honnête sur la granularité de l'historique (`:392-398`).

**Lacunes et frictions**
- Les 4 onglets sont calculés à chaque interaction (`:495-508`, pas d'onglets paresseux contrairement à Élections et Économie).
- La liste des élus n'a pas d'export (aucun `download_button` dans `legislatif.py`).
- La fiche député est cachée dans l'onglet Activité. Elle n'est pas accessible depuis la liste, ni pour un sénateur.
- « Top 20 » nominatif sur des scores Datan (`:282-316`) : sans note de méthode visible, un classement de personnes par « participation » ou « loyauté » peut être lu comme un jugement. L'audit le signalait déjà (moyennes d'activité sans note de méthode).
- Historique : `leg_mandats` ne contient que la **dernière législature** de chaque député (`granularite = derniere_legislature`, 2 120 lignes). La composition par législature reste approximative, et le lien circonscription ↔ député n'est complet que pour la 17e.
- Sénat : aucun score, aucune évolution (`:252-257`, `:378-383`). Base chargée le 2026-10-04 : il faut vérifier que le fichier source tient compte des sénatoriales du 27/09/2026 (veille R&D V1).
- Pas de lien vers les résultats électoraux de la circonscription du député.

| Complément | Valeur | Effort | Données | Risque neutralité |
|---|---|---|---|---|
| L1. Onglets paresseux (même mécanique qu'Élections) | Rapidité | S | — | Aucun |
| L2. Export CSV de la liste des élus et du classement, avec source et licence | Réutilisation | S | En base | Aucun |
| L3. Historique complet des mandats AN par législature via AMO30 (source autorisée le 2026-10-06) | Composition exacte de chaque législature ; lien député ↔ circonscription pour 2002-2024 | M | **Source déjà autorisée**, utilisée pour les non-inscrits | Faible |
| L4. Fiche élu ouverte depuis la liste (fenêtre ou page), AN et Sénat | Parcours direct | S-M | En base | Aucun |
| L5. Note de méthode Datan à côté du top 20 ; libellé « classement selon l'indicateur Datan » | Évite une lecture partisane | S | — | **Moyen** si absent |
| L6. Député × résultats de sa circonscription (score personnel vs score de son bloc à la présidentielle ; sortant réélu ou non) | Croisement propre au projet | M | En base (après L3 pour l'historique) | Moyen : ne pas qualifier (« sur-performance ») sans définition publiée |
| L7. Contrôle du Sénat après les sénatoriales du 27/09/2026 | Exactitude | S | Source déjà utilisée | Aucun |

---

## 5. Économie

**Parcours réel** : 4 onglets paresseux. (1) Carte d'un indicateur et d'une année, puis détail d'une commune dans un volet repliable. (2) Évolution régionale : Filosofi/RP, RSA ou Eurostat. (3) Croisement indicateur × bloc à la présidentielle (nuage de points). (4) Emploi industriel URSSAF 2006-2025, déserts médicaux.

**Ce qui marche** : classes fixes et légendes datées. Secret statistique en gris. Méthode d'agrégation affichée (`economie.py:67-69`). Carte des déserts à 3 états (`:106-108`). Avertissement « corrélation ≠ causalité » (`:707-713`). RSA explicitement présenté en nombre et non en taux (`:322-329`).

**Lacunes et frictions**
- Le détail d'une commune est caché dans un volet replié (`:350`). Il ne la compare ni au département ni à la région (pas de rang, pas d'écart).
- Le croisement ne porte que sur les présidentielles (`:600`, `get_annees_presidentielles`), en pratique 2022 seulement pour Filosofi (2017-2021). Pas de municipales 2020 ni de législatives 2022/2024, pourtant couvertes par les données économiques n-1.
- Pas de coefficient de corrélation ni de droite de tendance. Pas de mise en évidence d'une commune dans le nuage.
- **Aucun export** dans tout le module (pas de `download_button` dans `economie.py`).
- Les millésimes vieillissent : Filosofi 2017-2021, RP 2015-2021 (veille R&D V2-V3 toujours en suspens).

| Complément | Valeur | Effort | Données | Risque neutralité |
|---|---|---|---|---|
| C1. Profil économique d'une commune comparé au département et à la région (valeur, rang, écart) | Lecture immédiate | M | En base | Faible : moyennes pondérées annoncées |
| C2. Croisement étendu aux législatives 2022/2024 et aux municipales 2020 | Plus d'un scrutin exploitable | S-M | En base | Moyen : municipales limitées aux communes nuancées, à afficher |
| C3. Coefficient r et nombre de communes, sans droite de régression causale ; commune surlignée | Rigueur ; usage journaliste | S | En base | Moyen : rappeler l'erreur écologique (déjà fait) |
| C4. Export CSV de la carte et du croisement, avec source et licence (URSSAF sous ODbL) | Réutilisation conforme | S | En base | Aucun |
| C5. Mise à jour RP 2022 et Filosofi 2023 avec rupture de série affichée | Données à jour | M | **Nouvelle version des sources** ; règle de rupture à décider | Moyen : ne jamais relier 2021 et 2023 par une ligne continue |

---

## 6. Fonctionnalités transverses manquantes

| # | Fonctionnalité | Constat | Valeur | Effort | Données | Risque neutralité | Priorité |
|---|---|---|---|---|---|---|---|
| T1 | **État dans l'URL** (territoire, scrutin, tour, onglet) et territoire partagé entre pages | Aucun `query_params` dans le code | Partage d'une vue précise ; socle de T2, T3 et A2 | S par page (Streamlit) ; à prévoir dès la maquette Tauri | — | Aucun | **P1** |
| T2 | **Fiche territoire** (commune, puis circonscription) : population, historique électoral (E1), profil économique (C1), élus (E7), liens vers chaque module | Aucune page transverse ; la même commune se choisit 5 fois dans 5 listes | Transforme 4 modules juxtaposés en un outil d'analyse | L | En base | Faible (réutilise l'existant) | **P1** |
| T3 | **Recherche globale** (commune, circonscription, élu) | Recherches locales seulement (`legislatif.py:135`, listes déroulantes) | Point d'entrée unique | S-M (après T2) | En base | Aucun | **P1** |
| T4 | **Page Méthodologie et glossaire** : blocs et grilles, seuils de nuançage, ancien découpage, secret statistique, APL, BIT, scores Datan, limites connues | La légende renvoie à un chemin de fichier `docs/adr/…` que l'utilisateur ne peut pas ouvrir (`_blocs_politiques.py:67`) ; 0 `help=` dans Législatif | Rend visible la force du projet (traçabilité) | S-M | Docs existantes | Réduit le risque | **P1** |
| T5 | **Export homogène** : CSV avec en-tête source + licence + date partout ; image des graphiques avec source incrustée | Export présent en Géographie et Élections, absent en Législatif et Économie | Réutilisation conforme aux licences | S | — | Aucun | **P1** |
| T6 | **Clic carte → détail** | `returned_objects=[]` sur toutes les cartes | Geste naturel | M (Streamlit) ; natif en interface web | — | Aucun | P2 |
| T7 | **Comparaison** : deux scrutins (E5) et deux territoires (commune A / B ou commune / moyenne régionale) | Absente | Usage fréquent pour élus et journalistes | M (après T2) | En base | Moyen : comparer seulement des périmètres comparables | P2 |
| T8 | Rapport PDF d'une fiche territoire (Jinja2 + Tectonic, déjà dans la stack) | Absent | Livrable imprimable | L (après T2) | En base | Faible | P3 |
| T9 | Extension du périmètre électoral et économique hors Hauts-de-France | Les données Élections et Économie couvrent seulement 02/59/60/62/80 (vérifié en base) | Comparaisons interrégionales | L | Même source nationale, rechargement | Mise en correspondance des nuances à revalider | P3 (décision lourde, scénario B de la R&D) |

**Ordre conseillé** : T1 → T4 → T5 (rapides, sans décision de fond) → T2 avec E1, C1 et E7 → T3 → T6 et T7. Pour la cible Tauri, T1, T2 et T3 définissent la structure de navigation : ils devraient être le sujet de la maquette prévue.

## 7. Questions fermées pour Mathias

1. E3 : corriger tout de suite le libellé « Circos gagnées » (bug avéré, sans choix de fond) ? Proposition : oui, maintenance.
2. E9 : charger les européennes et les régionales (classement des listes sans grille officielle) : oui / plus tard ?
3. L5 : garder un « Top 20 » nominatif, ou le remplacer par une distribution sans noms et une recherche individuelle ?
4. T2 : la fiche territoire est-elle l'écran à maquetter en premier pour Tauri : oui / non ?
