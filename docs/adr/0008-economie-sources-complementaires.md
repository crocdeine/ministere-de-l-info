# 0008 — Module Économie : sources complémentaires (CNAF, DREES, URSSAF, Eurostat)

Date : 2026-09-24
Statut : Accepté (rédigé a posteriori le 2026-09-24)
Décideurs : Mathias (supervision)

> ADR rétroactif : il documente des décisions prises et appliquées pendant les
> Phases E+ et E++ (juin 2026, commits `7a53dd5`, `7a3b74c`, `c8258f8`), sans ADR à
> l'époque. Il complète l'ADR-0006 sans le remplacer. Sources : code
> (`src/ministere_de_l_info/etl/schema_economie.py`, `etl/loaders/economie_*.py`,
> `scripts/load_economie.py`) et rapports `reports/session-2026-06-14_phase-eplus.md`,
> `reports/session-2026-06-17_phase-eplus-plus.md`.

## Contexte

L'ADR-0006 a fixé le socle du module Économie : Filosofi + Recensement de la population,
deux tables (`economie_filosofi`, `economie_rp`), trois vues. Le rapport de clôture de la
Phase E (2026-06-12) a identifié des sources complémentaires « quick wins » : RSA (CNAF),
accessibilité aux médecins (DREES), effectifs salariés par secteur (URSSAF), et un
contexte macro-économique régional (chômage BIT, PIB par habitant).

Ces sources ont des granularités, millésimes et formats différents de Filosofi/RP,
et deux d'entre elles (chômage BIT, PIB) avaient été explicitement écartées par
l'ADR-0006 pour le croisement communal.

## Décision

### D1 — Quatre sources complémentaires

| Source | Donnée | Accès (URL dans le loader) | Format | Granularité | Couverture chargée (rapports) |
|---|---|---|---|---|---|
| CNAF | Foyers allocataires du RSA | `data.caf.fr`, dataset `rsa_s_type_com_f` (OpenDataSoft) | CSV `;` | Commune, snapshot de décembre | 2020-2024 |
| DREES | APL aux médecins généralistes | `data.drees.solidarites-sante.gouv.fr`, dataset `530_l-accessibilite-potentielle-localisee-apl` | XLSX multi-onglets | Commune | Dernier millésime disponible (2023 au chargement) |
| URSSAF | Effectifs salariés privés et établissements par commune × code APE | `open.urssaf.fr`, dataset `etablissements-et-effectifs-salaries-au-niveau-commune-x-ape-last` | CSV `;`, format large (une colonne par année) | Commune × APE | 2006-2025 |
| Eurostat | Chômage BIT (`lfst_r_lfu3rt`) et PIB par habitant (`nama_10r_2gdp`) | API SDMX 2.1 de diffusion Eurostat | TSV | NUTS2 `FRE` (Hauts-de-France) et `FR` (France) | Chômage 1999-2025, PIB 2000-2024 (rapport E++) |

### D2 — Trois tables supplémentaires

Définies dans `etl/schema_economie.py` (le module compte désormais 5 tables et 6 vues) :

| Table | Clé primaire | Contenu | Volume (rapports) |
|---|---|---|---|
| `economie_social` | `(code_commune, annee)` | `nb_foyers_rsa`, `taux_foyers_rsa` (CNAF) ; `apl_medecins`, `desert_medical` (DREES) | RSA : 17 381 lignes ; APL : 3 788 lignes (upsert dans la même table) |
| `economie_emploi_urssaf` | `(code_commune, annee, code_ape)` | `secteur_gs`, `nb_salaries`, `nb_etablissements` | 1 157 338 lignes |
| `economie_contexte` | `(code_geo, annee, indicateur)` | Format long : `type_geo`, `valeur`, `source` ; indicateurs `tx_chomage_bit`, `pib_eur_hab` | 104 lignes |

Vues ajoutées : `v_economie_sociale_commune`, `v_desindustrialisation_commune`
(variation de l'emploi des secteurs dont `secteur_gs` contient « Industrie », entre la
première et la dernière année disponibles par commune), `v_contexte_hdf_vs_france`
(pivot HdF / France / écart).

### D3 — Règles d'intégration propres à chaque source

- **CNAF** : le secret statistique est un arrondi au multiple de 5 (pas de NULL, pas de
  drapeau `secret`). Agrégation `SUM` sur tous les types de RSA. `taux_foyers_rsa` est
  calculé avec `pop_active` du RP comme dénominateur, donc uniquement pour les années
  couvertes par le RP (2020-2021).
- **DREES** : lecture XLSX via pandas + openpyxl (groupe `etl`), 8 lignes d'en-tête
  ignorées, sélection automatique de l'onglet le plus récent. `desert_medical = TRUE` si
  APL < 2,5 consultations/habitant/an. Upsert `ON CONFLICT` pour coexister avec les
  lignes CNAF de la même clé.
- **URSSAF** : fichier national mis en cache, filtré HdF, passage du format large au
  format long avec Polars.
- **Eurostat** : TSV SDMX ; drapeaux de qualité (`u`, `b`, `d`, `p`) retirés, `:` → NULL.
  Filtres : chômage `isced11=TOTAL, sex=T, age=Y15-74, unit=PC` ; PIB `unit=EUR_HAB`.
  Le dataset `tgs00005` initialement envisagé est remplacé par `nama_10r_2gdp`
  (déprécié selon le rapport E++). L'API INSEE BDM/IDBank a été écartée (blocage
  anti-robot constaté).

### D4 — Statut des données de contexte

Les indicateurs Eurostat ne sont **pas** croisés commune par commune avec les élections :
ils servent uniquement de toile de fond régionale (HdF vs France) dans l'onglet
« Évolution HdF ». Cela reste compatible avec le rejet, par l'ADR-0006, du chômage BIT
et des données régionales pour le croisement communal.

### D5 — Chargement

`scripts/load_economie.py --source {filosofi|rp|cnaf|urssaf|drees|social|eurostat|contexte|all}`.
`all` (défaut) enchaîne filosofi, rp, cnaf, urssaf, drees ; **Eurostat n'est chargé
que par `--source eurostat` (ou `contexte`)**. Filtre HdF (départements 02, 59, 60, 62,
80) appliqué avant insertion, sauf `economie_contexte` (codes NUTS).

## Alternatives considérées

| Alternative | Raison d'écarter |
|---|---|
| **Ajouter les colonnes RSA/APL à `economie_rp`** | Millésimes et sources différents du RP ; logiques de chargement distinctes |
| **Table URSSAF agrégée par grand secteur** | Perte du détail APE, utile pour d'autres lectures sectorielles ; volume (1,15 M lignes) acceptable pour DuckDB |
| **INSEE BDM (séries longues chômage)** | Accès bloqué par une protection anti-robot au moment de la Phase E++ |
| **Sirene pour l'emploi industriel** | Voir note d'exécution de l'ADR-0006 : l'emploi industriel communal vient du RP ; l'URSSAF fournit la série longue |
| **ANCT (QPV, ZRR)** | Identifié en Phase E, non réalisé (pas de décision de rejet) |

## Conséquences

**Positives**
- Onglet « Désindustrialisation » (série URSSAF 2006-2025, drill-down commune, carte des
  déserts médicaux), indicateurs RSA et APL disponibles dans la carte et l'évolution.
- Contexte macro-économique sourcé (HdF vs France) sans prétendre à une granularité
  communale.

**Négatives**
- Trois formats d'ingestion supplémentaires (CSV large, XLSX, TSV SDMX) à maintenir.
- Deux loaders (`economie_drees.py`, `economie_eurostat.py`) utilisent pandas
  (lecture XLSX / TSV), à justifier au regard de l'ADR-0004.
- `economie_social` mélange deux sources aux millésimes disjoints (RSA 2020-2024,
  APL 2023) : la plupart des lignes n'ont qu'une moitié des colonnes renseignée.

**Réversibilité** : élevée ; chaque source a son loader, son option `--source` et ses
colonnes ou tables propres.

## Points ouverts

Signalés sans être tranchés.

1. **Borne de début du chômage Eurostat** : le rapport E++ annonce 1999-2025, alors que
   l'URL du loader demande `sinceTimePeriod=2000`. Non vérifiable sans la base.
2. **URL DREES** : le rapport E+ cite data.gouv.fr comme source DREES ; le loader
   télécharge depuis `data.drees.solidarites-sante.gouv.fr`.
3. **Rapport de vérification cité mais absent** :
   `reports/verification-sources-phase-e-plus.md` est référencé dans les docstrings des
   loaders DREES et URSSAF mais n'existe pas dans le dépôt.
4. **Eurostat hors de `all`** : un premier chargement complet via `load_economie.py`
   sans option ne remplit pas `economie_contexte`.
5. **Filtre « Industrie »** : `v_desindustrialisation_commune` repose sur
   `secteur_gs LIKE '%Industrie%'` (libellé texte URSSAF), fragile si le libellé change.
6. **`taux_foyers_rsa`** : NULL pour 2022-2024 (pas de millésime RP correspondant).
7. **Pandas dans deux loaders** : conformité à l'ADR-0004 à confirmer (lecture XLSX et
   TSV).
