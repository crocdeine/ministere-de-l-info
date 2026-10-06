# J4 hygiène : cache Géographie et connexion DuckDB partagée (2026-10-06)

## Résumé exécutif
- Page Géographie : plus de connexion `@st.cache_resource` permanente ; lectures en `@st.cache_data`
  (années, référentiels dpt/régions, métadonnées ETL, tableau) et carte en `@st.cache_resource`
  (`get_carte_cache`, 32 entrées max), connexions courtes fermées dans `finally`.
- `viz/_queries.py::open_ro(db_path, *, spatial=True)` : source unique ; les 3 `_open_ro()`
  (économie, élections, législatif) deviennent des wrappers d'une ligne (points d'injection
  des tests conservés, `DB_PATH` du module toujours respecté). Législatif : `spatial=False`.
- Aucun changement visible (mêmes widgets, cartes, tableau).

## Mesures (base réelle, 6 cas : région, dpt, EPCI, circo, commune 59, commune 75)
| | Avant | Après (1er passage) | Après (rerun, cache chaud) |
|---|---|---|---|
| Somme des lectures d'un rerun | 2,49 s (dont 1,34 s au 1er cas, chargement spatial) | 0,84 s | 0,001 s |
Unité : chronométrage des fonctions (pas AppTest). Un clic sans changement de paramètre ne touche plus la base.

## Limites
- Carte partagée entre sessions (`cache_resource`) : hypothèse que `st_folium` ne la modifie pas ; à valider visuellement par Mathias.
- TTL 3600 s sur les lectures : un rechargement ETL est visible après 1 h ou redémarrage (comme les autres modules).
- Tests : `pytest -m "not slow and not network"` 650 passés, couverture 76,23 % (avec base via lien `data`).
  Sans base : 1 test (`test_geographie_sans_script_obsolete`) échoue si `MINISTERE_DB_PATH` pointe sur une vraie base (artefact d'environnement).
