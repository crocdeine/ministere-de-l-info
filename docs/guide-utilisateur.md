# Guide utilisateur — Ministère de l'Info

## Accéder à l'application

Après installation (voir README), lancer :

```bash
uv run streamlit run app.py
```

Ouvrir ensuite **http://localhost:8501** dans un navigateur.

---

## La page Géographie

C'est la page principale. Elle affiche une carte interactive de France avec des données
de population par territoire.

### Choisir un niveau territorial

Le menu déroulant **"Niveau territorial"** propose 6 découpages :

| Niveau | Nombre | Description |
|--------|--------|-------------|
| Régions | 18 | Les 13 régions métropolitaines + 5 DROM (Guadeloupe, Martinique, Guyane, La Réunion, Mayotte) |
| Départements | 101 | 96 métropole + 5 DROM (971 à 976) |
| EPCI | ~1 265 | Communautés de communes, d'agglomération, métropoles |
| Communes | ~34 877 | Toutes les communes — **un département doit être sélectionné** |
| Arrondissements municipaux | 45 | Paris (20), Lyon (9), Marseille (16) uniquement |
| Circonscriptions législatives | 559 | Découpages électoraux pour les législatives |

> **Astuce :** pour les communes, le sélecteur de département apparaît automatiquement
> dans la barre latérale — il est obligatoire pour éviter de charger 35 000 polygones d'un coup.

### Choisir le millésime de population

Le menu **"Millésime"** permet de choisir l'année de référence des données INSEE :
- **2013** — recensement 2013
- **2018** — recensement 2018
- **2023** — recensement 2023 (le plus récent chargé)

### Lire une carte choroplèthe

La carte choroplèthe colorie chaque territoire selon sa population :

- **Jaune clair** → faible population
- **Rouge foncé** → forte population
- La **légende** en bas à gauche indique les seuils (5 classes équidistantes)
- **Survoler** un territoire affiche son nom et sa population exacte
- La **source** apparaît en bas à droite de la carte

### Utiliser les filtres

Selon le niveau sélectionné, des filtres supplémentaires apparaissent dans la barre latérale :

- **Filtre Département** : disponible pour EPCI, Circonscriptions et Communes — recentre la carte
- **Filtre Région** : disponible pour Départements et Communes — filtre par région
- **Mode de rendu** (Options avancées) : `auto` (défaut), `choropleth`, `contours`

### Niveaux en mode contours (carte bleue)

Les **arrondissements municipaux** et les **circonscriptions législatives** s'affichent
en contours bleus sans coloration — c'est normal. Ces découpages n'ont pas de données
de population directement associées dans la base actuelle.

---

## Comprendre les données

### Sources géographiques

Toutes les géométries proviennent de **IGN ADMIN-EXPRESS-COG** (millésime latest),
disponible sur [data.geopf.fr](https://data.geopf.fr). C'est la référence officielle
du découpage administratif français, mise à jour annuellement par l'IGN.

### Sources démographiques

Les populations proviennent de **l'INSEE — Mélodi (DS_POPULATIONS_HISTORIQUES)**.
Il s'agit des **populations légales** au sens du recensement :

- **Population municipale** : habitants comptés dans la commune (c'est le chiffre affiché)
- **Population comptée à part** : étudiants, militaires, détenus en internat... (non chargé actuellement)
- **Population totale** = municipale + comptée à part (non chargé actuellement)

### Codes INSEE vs codes postaux

Le code INSEE d'une commune ≠ son code postal :

| Ville | Code INSEE | Code postal |
|-------|------------|-------------|
| Paris (commune entière) | 75056 | 75001 à 75020 |
| Lyon | 69123 | 69001 à 69009 |
| Marseille | 13055 | 13001 à 13016 |

Les **arrondissements** de Paris ont leurs propres codes : 75101 (1er) → 75120 (20e).

---

## FAQ

**Q : Pourquoi Mayotte n'apparaît pas dans les cartes de population ?**

R : Les données de population de Mayotte sont publiées séparément par l'INSEE, dans
une source différente de celle chargée actuellement. Les contours géographiques de
Mayotte sont bien présents, mais sans population associée. Correction prévue en v2.

---

**Q : Pourquoi certains EPCI n'ont pas de département affiché dans le tableau ?**

R : Les 11 Établissements Publics Territoriaux (EPT) du Grand Paris couvrent plusieurs
départements simultanément. Le WFS IGN retourne un champ multi-valeur pour ces cas,
ce qui empêche d'associer un département unique. Correctif prévu en v2.

---

**Q : La carte des communes est longue à charger, c'est normal ?**

R : Oui. Un département comme le Nord (59) contient ~648 communes avec leurs géométries.
Le chargement prend 3 à 10 secondes selon la machine. La carte est mise en cache pour
les navigations suivantes dans la même session.

---

**Q : Pourquoi la population affichée est-elle différente de la population "officielle" ?**

R : La population légale INSEE (utilisée ici) est la référence officielle mais peut
différer des estimations en milieu d'intercensal. Le millésime 2023 est le plus récent
disponible dans la source chargée.

---

**Q : Comment relancer le chargement des données si la base est vide ou corrompue ?**

R : Arrêter l'application (Ctrl+C dans le terminal), puis :

```bash
uv run python scripts/etl_territoires.py --millesimes 2023 --yes --force
```

Le flag `--force` retélécharge toutes les sources depuis zéro.
