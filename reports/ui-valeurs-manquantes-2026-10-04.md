# UI — valeurs manquantes et carte déserts médicaux (2026-10-04)

## Résumé exécutif
- I6 : une valeur absente reste NULL et s'affiche « n.d. » (plus de 0 / 0 %) dans Élections pres/legi/muni.
- Helper `fmt_nd()` dans `viz/_display.py` ; les 3 `get_metrics_commune_*` renvoient `None` (et non 0) si absent.
- Carte score de bloc : exprimés absents/nuls -> gris foncé `#5F6368` + légende « n.d. » ; info-bulle « n.d. ».
- Tableaux pres (détail commune) et muni (blocs, listes) : `na_rep="n.d."`.
- I9 : carte déserts médicaux à 3 états (désert rouge `#C62828`, au-dessus du seuil `#DDE6EE`, sans donnée gris foncé `#5F6368`), légende HTML, colorbar supprimée.
- Légende/caption : « APL < 2,5 consultations/hab./an (seuil de sous-densité utilisé par la DREES) ».
- Aucun classement ni couleur de bloc modifié. Tests : `tests/test_valeurs_manquantes.py` (hermétique).
- Non vérifié visuellement (validation Mathias requise).

## Corrections
| Fichier | Avant | Après |
|---|---|---|
| `pages/elections_presidentielles.py` | `.fill_null(0)` global après jointure participation | `fill_null(0)` limité aux colonnes de blocs ; inscrits/exprimés/taux NULL -> « n.d. » |
| `viz/maps_elections.py` (score bloc) | exprimés absents -> 0 % | NULL -> gris + légende ; bloc absent mais exprimés connus -> 0 % conservé |
| `pages/elections_municipales.py` | `pct_exprimes.fill_null(0.0)` x2 | retiré, `na_rep="n.d."` |
| `viz/elections_{,legi_,muni_}queries.py` + pages | `row[i] or 0` : commune sans participation affichée 0 inscrit / 0 % | `None` -> `fmt_nd` |
| `pages/economie.py` | binaire rouge/gris (NULL pour hors désert) | 3 catégories distinctes, `_etat_desert()` |

## `fill_null(0)` / `or 0` conservés (0 sémantiquement juste)
- `elections_presidentielles.py` pivot voix par bloc : bloc sans voix dans la commune = 0 voix.
- `elections_legislatives.py` ~l.156 : `circos_gagnees` null après jointure = 0 circonscription gagnée.
- `elections_queries.py` pivot BV et `voix_*` : idem, voix de bloc absent = 0.
- `elections_queries.py` ~l.246-262 (séries d'évolution) : comptages issus de SUM/agrégats par BV, lignes présentes ; non modifiés (hors périmètre signalé, à revoir si une année manque).
- `elections_muni_queries.py` `nb_listes or 0` : un comptage de listes vaut 0 s'il n'y en a pas.
- `maps_elections.py` ~l.346 `voix_total or 0` (carte bloc dominant) : sert au tooltip ; non modifié.

## Tests
`tests/test_valeurs_manquantes.py` : `fmt_nd`, métriques commune sans participation (DuckDB mémoire) = None, carte score bloc exprimés absents -> « n.d. » (et 0 % conservé si exprimés connus), `_etat_desert`, carte déserts = 3 états + légende. `test_commune_inconnue_retourne_zeros` renommé en `..._none` (comportement voulu changé).

## Décisions / limites
- Couleurs `#C62828`, `#DDE6EE`, `#5F6368` en dur (hors tokens CSS) : à valider ou à mapper sur des tokens.
- Gris foncé choisi plutôt que hachures pour « sans donnée ».
- Rendu visuel non vérifié ; la session de test n'a pas exécuté les tests dépendant de la base (skipped).
