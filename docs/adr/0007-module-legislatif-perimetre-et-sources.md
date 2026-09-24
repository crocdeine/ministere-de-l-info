# 0007 — Module Législatif : périmètre national, sources Datan + data.senat.fr

Date : 2026-09-24
Statut : Accepté (rédigé a posteriori le 2026-09-24)
Décideurs : Mathias (supervision)

> ADR rétroactif : il documente des décisions prises et appliquées pendant la Phase F
> (juin 2026, commits `01afbd5`, `ff645f7`, `c3ec0f9`, `a6f98cf`), sans ADR à l'époque.
> Il ne crée aucune décision nouvelle. Sources : code (`src/ministere_de_l_info/etl/`,
> `scripts/load_legislatif.py`) et rapport `reports/session-2026-06-22_phase-f-cloture.md`.

## Contexte

Le module Législatif devait présenter la composition politique et l'activité des
parlementaires. Le cadrage initial (Phase F1) visait les seuls élus des Hauts-de-France,
par cohérence avec les modules Élections et Économie, en s'appuyant sur deux API tierces :
NosDéputés.fr (Regards Citoyens) pour les métriques d'activité AN, et l'API CLAIR.

En cours de Phase F, deux constats ont imposé une révision :

1. **Sources tierces indisponibles** (rapport Phase F) :
   - NosDéputés.fr : endpoint de métriques (`/synthese/data/json`) renvoyant `{}` depuis la
     dissolution de juin 2024 (données figées) ;
   - API CLAIR : HTTP 500 sur tous les endpoints, panne jugée non récupérable.
2. **Périmètre HdF trop étroit** pour une assemblée nationale : la composition d'une
   chambre n'a de sens qu'au niveau national ; l'échelon HdF (~85 élus actifs selon le
   rapport Phase F) devient un filtre de lecture.

## Décision

### D1 — Périmètre national, filtre HdF en UI

Les données sont chargées pour la France entière (AN et Sénat, élus actifs et anciens).
La restriction territoriale est un filtre d'interface (sidebar de la page Législatif :
« Tous (France) », « Hauts-de-France (région) » ou un département), pas un filtre ETL.
Ce module est donc le seul du projet à ne pas être filtré HdF au chargement.

### D2 — Sources retenues

| Chambre | Source | Fichier / accès | Contenu chargé |
|---|---|---|---|
| Assemblée nationale | Datan, publié sur data.gouv.fr (dataset `historique-des-deputes-de-lassemblee-nationale-depuis-2002-informations-et-statistiques`) | CSV UTF-8, URL résolue via l'API data.gouv.fr, URL statique de secours dans le loader | Profils des députés (législatures 12 à 17) + scores d'activité calculés par Datan (participation, participation spécialisée, loyauté, proximité majorité) |
| Sénat | data.senat.fr | `https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv` (cp1252, 18 lignes de commentaires) | Sénateurs actifs et anciens, groupe, circonscription, profession |

Chargement : `scripts/load_legislatif.py --source {senat|datan|overrides|all}`
(`all` par défaut). Loaders : `etl/loaders/legislatif_senat.py`,
`legislatif_datan.py`, `legislatif_overrides.py`.

### D3 — Abandon de NosDéputés.fr et de CLAIR

Les deux sources sont exclues du chargement (`all` ne les appelle pas). Les modules
`etl/loaders/legislatif_nosdeputes.py` et `legislatif_clair.py` restent présents dans
le dépôt, marqués « sources dépréciées » dans `scripts/load_legislatif.py`.

### D4 — Schéma DuckDB

Défini dans `src/ministere_de_l_info/etl/schema_legislatif.py` :

| Objet | Rôle | Volume (rapport Phase F, 2026-06-22) |
|---|---|---|
| `leg_elus` | Élus AN + Sénat, clé `(id, chambre)`, `bloc_politique` dérivé du groupe, `est_actif` | 4 065 lignes (2 120 AN + 1 945 Sénat) |
| `leg_activite` | Scores d'activité par élu × date d'extraction (AN uniquement) | 1 653 lignes |
| `leg_blocs_override` | Correction manuelle du bloc d'un élu, avec justification | 2 lignes |
| `v_elus_hdf_actuels` | Élus actifs avec `bloc_final = COALESCE(bloc_force, bloc_politique)` — malgré son nom, la vue est nationale | — |
| `v_activite_par_bloc` | Moyennes d'activité par bloc × chambre (élus actifs) | — |

### D5 — Classement des groupes parlementaires en blocs

Chaque loader contient une table de correspondance `_GROUPE_BLOCS` (sigle de groupe →
un des 6 blocs de l'ADR-0005). Un groupe absent de la table est classé `DIV` par défaut.
Règle inscrite dans les loaders : PCF/GDR/CRCE-K = `GAU` ; `EXG` réservé à LFI et à
l'extrême gauche au sens strict.

### D6 — Table `leg_blocs_override`

Quand le groupe ne reflète pas l'appartenance politique (ex. non-inscrits), une ligne
de `leg_blocs_override` force le bloc, avec une justification textuelle obligatoire.
Au moment de la rédaction, deux entrées (sénateurs RN siégeant en NI, Nord et
Pas-de-Calais, élus en 2023) : `NI` → `EXD`. Les overrides sont appliqués à la lecture
(vues SQL), sans modifier `leg_elus`.

## Alternatives considérées

| Alternative | Raison d'écarter |
|---|---|
| **Conserver le périmètre HdF au chargement** | Composition d'une chambre illisible sans le national ; aucun gain de volume significatif (quelques milliers de lignes) |
| **NosDéputés.fr / NosSénateurs.fr** | Métriques figées depuis juin 2024, endpoint de synthèse vide |
| **API CLAIR** | Hors service (HTTP 500) |
| **Dumps XML officiels data.assemblee-nationale.fr** | Complets (votes nominatifs, amendements) mais nécessitent un parser XML dédié ; non réalisé en Phase F |
| **Classement des élus un par un (sans table de groupes)** | Non maintenable sur 4 000 élus ; le groupe est le critère observable le plus stable, les exceptions passent par `leg_blocs_override` |

## Conséquences

**Positives**
- Module fonctionnel malgré la défaillance des deux API tierces initialement prévues.
- Vue nationale et vue HdF disponibles sans rechargement.
- Exceptions de classement tracées (justification par ligne), réversibles sans ETL.

**Négatives / limitations connues** (rapport Phase F)
- Pas de scores d'activité pour le Sénat (Datan ne couvre que l'AN).
- Pas de votes nominatifs (XML AN non parsé).
- Onglet « Évolution historique » approximatif : chaque député est rattaché à sa
  dernière législature (`legislatureLast` du CSV Datan).
- `region_nom` NULL pour les députés (absent du CSV Datan).

**Réversibilité** : élevée. Changer un classement = modifier `_GROUPE_BLOCS` ou
`leg_blocs_override` puis relancer `load_legislatif.py` (quelques secondes).

## Points ouverts

Ces points sont signalés sans être tranchés ; ils relèvent d'une décision
méthodologique à valider par Mathias.

1. **Mapping rétroactif du groupe FI** : `legislatif_datan.py` classe `FI`,
   `LFI-NUPES` et `LFI-NFP` en `EXG` quelle que soit la législature. Pour les
   législatures 15 et 16 (2017-2024), l'ADR-0005 (classement « de l'époque ») place LFI en
   `GAU` ; seule la grille 2026 (INTP2602966C) la place en `EXG`. L'onglet « Évolution
   historique » est donc incohérent avec le module Élections pour ces législatures.
2. **Mapping unique par groupe, sans dimension temporelle** : la table `_GROUPE_BLOCS`
   ne dépend pas de la législature, alors que l'ADR-0005 impose une grille datée.
3. **Repli `DIV` par défaut** : tout groupe absent de `_GROUPE_BLOCS` est classé `DIV`.
   Côté Sénat, la table ne contient que `CRCE-K`, `SER`, `UC`, `Les Indépendants`,
   `Les Républicains` et `NI` ; les autres groupes présents dans le CSV (libellés non
   vérifiés dans cet environnement faute de données) tombent en `DIV`. Le rapport
   Phase F indique 55 sénateurs actifs en `DIV`.
4. **Non-inscrits** : `NI` → `DIV` dans les deux chambres, hors overrides. La complétude
   des overrides (autres élus NI rattachables à un parti) n'a pas été instruite.
5. **Dates de mandat Sénat** : `date_debut_mandat` n'est pas renseignée et
   `date_fin_mandat` vaut la date du chargement pour les anciens sénateurs (champ non
   représentatif de la date réelle de fin de mandat).
6. **Couverture temporelle Sénat** : le fichier ODSEN_GENERAL contient des sénateurs
   antérieurs à 2002 (le loader prévoit des circonscriptions historiques, codées `XX`) ;
   le libellé « 2002-présent » ne vaut que pour l'AN.
7. **Code conservé des sources abandonnées** : le rapport Phase F indique « code non
   conservé » alors que `legislatif_nosdeputes.py` et `legislatif_clair.py` sont
   toujours présents. Suppression ou conservation à décider.
8. **Nom de la vue `v_elus_hdf_actuels`** : trompeur depuis le passage au national
   (aucun filtre HdF dans la vue).
