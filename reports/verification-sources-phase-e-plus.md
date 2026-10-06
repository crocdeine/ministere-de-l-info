# Vérification sources Phase E+

## CNAF — RSA par commune
### Accès et format
- **URL exacte de téléchargement :** `https://data.caf.fr/explore/dataset/rsa_s_type_com_f/download/?format=csv&timezone=Europe/Berlin&use_labels_for_header=false`
- **Colonnes exactes disponibles :** `dtreffre`, `numcomdo`, `nomcom`, `rsa_type`, `indfoy_rsa`, `indnbp_rsa`
- **Format et encodage :** Fichier CSV (séparateur `;`, encodage UTF-8).
- **Automatisation :** API REST (OpenDataSoft) disponible. Pas de fichier Parquet natif, mais un export CSV rapide et automatisable.

### Couverture temporelle
Données disponibles annuellement au mois de décembre, couvrant la période de **2020 à 2024**.

### Code commune et secret statistique
- **Format du code commune :** 5 caractères alphanumériques (ex: `59350`), avec le zéro initial préservé.
- **Secret statistique :** Les effectifs (nombre de foyers et personnes couvertes) sont systématiquement arrondis au multiple de 5 le plus proche. Les petites communes rurales sont présentes, mais l'arrondi masque la granularité unitaire pour garantir la confidentialité.

### Valeurs de référence HdF
- Pour la commune de **Lille (59350)** en 2024-12 : on compte ~1 010 foyers au titre du `RSA majoré` et ~9 995 foyers pour le `RSA non majoré`, soit environ **11 005 foyers allocataires** au total.

### Verdict : intégrable immédiatement / nécessite adaptation
**Intégrable immédiatement.** Structure de données très propre. La seule manipulation requise sera d'agréger (sommer) la dimension `rsa_type` pour obtenir le volume global de foyers par commune.

## DREES — APL déserts médicaux
### Accès et format
- **URL exacte de téléchargement (Médecins généralistes) :** `https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/530_l-accessibilite-potentielle-localisee-apl/attachments/indicateur_d_accessibilite_potentielle_localisee_apl_aux_medecins_generalistes_xlsx`
- **Ressources :** Plusieurs fichiers par spécialité (Infirmières, Sages-femmes, Kinés, Dentistes, Médecins généralistes).
- **Format :** Fichier natif **XLSX**. Ce n'est pas un CSV direct.
- **Colonnes (pour la feuille APL 2023) :** `Code commune INSEE`, `Commune`, `APL aux médecins généralistes`, `APL aux médecins généralistes de 65 ans et moins`, `APL aux médecins généralistes de 62 ans et moins`, `APL aux médecins généralistes de 60 ans et moins`, `Population standardisée 2021 pour la médecine générale`, `Population totale 2021`.

### Définition APL et seuil désert médical
- **Définition :** L'APL est définie comme un **"nombre de consultations ou visites accessibles par habitant standardisé"** par an.
- **Représentation des déserts médicaux :** Il s'agit d'un seuil numérique sur l'indicateur continu. Historiquement et pour la DREES, une commune est considérée comme un désert médical (ou zone sous-dense) si son APL est inférieur à **2,5** consultations.

### Couverture HdF
Couverture exhaustive des communes, y compris rurales. Les millésimes les plus récents (2022 et 2023) sont chacun dans un onglet dédié du fichier Excel.

### Valeurs de référence
- Pour **Lille (59350)**, l'APL 2023 aux médecins généralistes est de **6.106**. La ville est très bien couverte et largement au-dessus du seuil de désert médical.

### Verdict
**Nécessite une petite adaptation technique.** La lecture doit cibler le format `.xlsx` (avec une librairie comme Pandas/openpyxl), identifier le bon onglet (ex: `APL 2023`) et impérativement **ignorer les 8 premières lignes d'en-tête** (métadonnées textuelles) pour parser proprement le tableau de données.

## URSSAF — Effectifs salariés privés
### Accès et format
- **URL de téléchargement direct :** `https://open.urssaf.fr/explore/dataset/etablissements-et-effectifs-salaries-au-niveau-commune-x-ape-last/download/?format=csv&timezone=Europe/Berlin&use_labels_for_header=false`
- **Format :** CSV (via l'API OpenDataSoft classique).

### Structure dataset (colonnes exactes)
- Le niveau de granularité est le croisement **Commune × Secteur APE**.
- Le dataset est pivoté (format *wide*), incluant : `code_commune`, `code_ape`, `grand_secteur_d_activite` (ex: `GS1 Industrie`), ainsi qu'une série très longue de colonnes pour les années allant de 2006 à 2025 : `effectifs_salaries_2006` ... `effectifs_salaries_2025` et `nombre_d_etablissements_2006` ... `nombre_d_etablissements_2025`.

### Pertinence pour désindustrialisation
**Excellente**. On y retrouve les effectifs par code APE à 5 caractères. Il est très aisé d'isoler le secteur industriel en filtrant sur la colonne `grand_secteur_d_activite` (GS1) ou sur les sections NAF de l'industrie manufacturière. La série temporelle allant de 2006 à 2025 permet de capter finement la dynamique historique de l'emploi industriel et de révéler d'éventuels décrochages sur les communes locales.

### Volume HdF estimé
Le fichier national comprend environ 1,22 million de lignes. En filtrant sur la région Hauts-de-France (via `code_region == 32`), le volume sera très gérable et on peut l'estimer entre **100 000 et 150 000 lignes**. Le code commune est bien de 5 caractères.

### Verdict
**Intégrable immédiatement.** Jeu de données massif et structuré de manière très propre. Une manipulation technique (un `melt` ou `unpivot`) sera cependant recommandée pour transformer les colonnes annuelles (wide) en format long (long) pour des agrégations et visualisations plus simples en aval.

## Recommandation d'ordre d'intégration
Je préconise d'intégrer les sources dans cet ordre pour la Phase E+ :

1. **CNAF (RSA par commune)** : Un pur *Quick Win*. Fichier CSV direct, léger, facile à charger, sans besoin de restructuration majeure. C'est le plus simple à intégrer pour valider le processus technique très rapidement et disposer d'un marqueur de précarité.
2. **URSSAF (Effectifs salariés du privé par commune)** : Potentiel analytique extrêmement fort pour le croisement électoral (la désindustrialisation expliquant structurellement de nombreux basculements politiques). Son téléchargement via CSV est direct ; la seule contrainte est de prévoir le "dépivotage" temporel. C'est la donnée la plus impactante sur le long terme.
3. **DREES (APL / Déserts Médicaux)** : L'impact thématique est indéniable, mais il existe une friction technique à cause de la dépendance à un fichier binaire `.xlsx` (multi-onglets et comprenant des en-têtes complexes textuels sur les 8 premières lignes). Il est préférable de l'intégrer en dernier, une fois les deux pipelines CSV standard (CNAF/URSSAF) validés.
