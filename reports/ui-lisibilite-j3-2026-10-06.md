# UI — Lisibilité honnête (jalon J3), 2026-10-06

## Résumé exécutif
- Cartes : bornes de classes fixes par indicateur (table `BORNES_FIXES`, `viz/_display.py`), légende « Classes fixes, identiques pour toutes les années ». Géographie (population, par niveau) et Économie (8 indicateurs) concernées.
- Carte « score d'un bloc » : échelle fixe 0-60 % (au lieu de 0-max de la carte), annoncée en légende.
- Municipales : évolution par défaut en part des exprimés des communes nuancées ; note sur le seuil de nuançage (3 500 / 1 000 / 3 500 / 3 500 hab.).
- Présidentielles, législatives : « Part des exprimés (%) » par défaut ; note sur le 2e tour des législatives ; infobulle en % corrigée.
- Évolution démographique : palette orange-violet (PuOr) au lieu de rouge-vert.
- Centre : trait des lignes d'évolution assombri (#B38600, 3,3:1) ; remplissages inchangés.
- Métrique « Bloc majoritaire / dominant » : retour à la ligne au lieu de l'ellipse (CSS).
- Tests : `tests/test_lisibilite_j3.py` (9), ruff propre. Validation visuelle Mathias requise.

## Changements visibles et points à regarder
1. **Géographie, carte population** (tous niveaux) : classes fixes par niveau (ex. communes : <500, 500-2 000, 2 000-10 000, 10 000-50 000, ≥50 000). Regarder : lisibilité des classes, légende + mention. Seuils choisis a priori (ordres de grandeur), à valider.
2. **Économie, onglet Carte** : `folium.Choropleth` (échelle auto) remplacé par `GeoJson` + `StepColormap` + légende maison (même palette YlOrRd). Gris conservé pour secret/n.d. Regarder : la carte pour 2 années d'un même indicateur, et la tooltip. Bornes (taux de pauvreté 5/10/15/20 %, niveau de vie 16/19/22/25 k€, chômage 6/9/12/15 %, ouvriers+employés 30/40/50/60 %, industrie 5/10/15/25 %, logements sociaux 5/10/20/30 %, RSA 10/50/200/1 000 foyers, APL 2,5/3,5/4,5/5,5) à valider. Aucun indicateur n'a nécessité de quantiles.
3. **Élections, carte « score d'un bloc »** : échelle 0-60 % fixe (au-delà : couleur max). Un bloc à 8 % est désormais pâle. Regarder : lisibilité pour un bloc fort (EXD, DTE) ; alternative 0-100 %.
4. **Municipales, évolution** : radio « Unité » (défaut % exprimés des communes nuancées, dénominateur = voix de tous les blocs classés du scrutin, 1er tour) + note de seuil. Regarder : courbes plus stables 2008→2014, texte de la note.
5. **Présidentielles / législatives, évolution** : défaut « Part des exprimés (%) ». Note 2e tour législatif sous le graphe. Attention : le dénominateur est la somme des voix classées en blocs (comportement existant), pas les exprimés officiels ; libellé « exprimés » conservé tel quel.
6. **Évolution démographique** : couleurs #e66101 / #fdb863 / #f7f7f7 / #b2abd2 / #5e3c99 (baisse = orange, hausse = violet).
7. **Centre** : `couleurs_traits()` (`_blocs_politiques.py`) appliqué aux 3 lignes d'évolution élections ; non appliqué aux graphiques de `legislatif.py`/`economie.py` (barres/points = remplissages) ; pas d'étiquettes textuelles ajoutées (légende Plotly nomme déjà chaque série).
8. **Métrique** : `custom.css`, `stMetricValue` en retour à la ligne. Regarder « Extrême gauche » sur 4 colonnes en largeur étroite.

## Suppressions / compatibilité
`_compute_breaks` supprimé ; `_COULEURS_RDYLGN5` renommé `_COULEURS_EVOLUTION5`. `_make_choropleth` (Économie) prend un 3e argument `indicateur` (tests adaptés).

## Vérifications
`ruff check` et `ruff format --check` propres. `pytest tests -m "not slow"` avec la base : 301 passés, 1 échec d'environnement (`test_geographie_sans_script_obsolete` suppose la base absente ; passe sans `MINISTERE_DB_PATH`). 363 tests ignorés (dépendent de la base dans le worktree). Couverture globale 72 % (seuil 38 %).

## Décisions à soumettre
- Échelle du score d'un bloc : 0-60 % ou 0-100 % ?
- Seuils des bornes fixes (Géographie, Économie) : valider tels quels ou ajuster ?
- Part des exprimés des évolutions pres/legi : conserver le dénominateur « voix classées » ou passer à l'exprimé officiel ?
- Étiquettes textuelles directes sur les courbes (au-delà de la légende) : oui/non ?
