# Vague A, lot A4 : recherche globale (2026-10-12)

## Résumé exécutif
- Champ de recherche permanent dans le bandeau (⌘K, Ctrl+K, « / ») : commune (nom, INSEE, **code postal**), département, circonscription, élu en exercice. Combobox ARIA, ordre purement lexical, tolérance accents, tirets, « St ».
- Index `recherche.json.gz` : 34 877 communes, 102 départements, 559 circonscriptions, 888 élus ; 552 Ko gzip (< 1 Mo). Filtrage linéaire, top-N sans tri complet.
- Département, circonscription et élu ouvrent la fiche de la commune la plus peuplée de leur périmètre (indiquée dans le résultat) : règle provisoire acceptée par le directeur.
- Codes postaux : La Poste, Base officielle des codes postaux (hexasmal), Licence Ouverte 2.0, vérifiée le 2026-10-12 ; table `codes_postaux` (35 511 couples), chargée seulement dans la copie `outils/tmp/a4-base`.
- Écarts publiés dans `manifest.perimetre` : `elus_non_indexes` (37 ; par département : 099=11, 977=2, 978=1, 986=2, 987=5, 988=4, 999=12), `elus_rattaches_au_departement`, `circonscriptions_ecartees`, `codes_postaux_charges`.
- Revue (typescript-reviewer, silent-failure-hunter) : 11 corrections appliquées (voir ci-dessous).
- Vérifications : tsc, vitest 37/37, build, budget 399 Ko, e2e `url` et `recherche` (WebKit, Chromium, 6 passages stables), pytest ciblés, ruff, pyright.
- Validation visuelle par Mathias encore à faire (une capture WebKit seulement, hors écran de Mathias).

## Base réelle (à lancer par le directeur)
```bash
uv run python scripts/load_codes_postaux.py
uv run python scripts/export_web.py --exiger-cp
```
`--exiger-cp` : échec si `codes_postaux` manque. Sans l'option, l'index est produit sans codes postaux (placeholder adapté, `codes_postaux_charges: false`).

## Corrections de revue
- Web : focus sur le titre de la fiche après navigation (sans vol de focus si la saisie reprend) ; messages (« Aucun résultat », chargement, erreurs) hors de la `listbox`, annoncés par `role=status` ; `Intl.Collator` partagé et sélection top-N ; réessai de chargement de l'index au prochain focus ; Échap sans double effacement.
- ETL : lignes rejetées = erreur, minimum 35 000 couples, entête contrôlée aussi sur le cache, 150 couples hors référentiel (COM : 977=1, 978=1, 986=3, 987=93, 988=50, 989=1, 991=1) journalisés et conservés.
- Export : écarts de la recherche comptés, journalisés et publiés ; option `--exiger-cp`.

## Écarts et limites
- Le composant s'appelle `ChampRecherche.tsx` (macOS : `Recherche.tsx` entrait en collision avec `recherche.ts`).
- e2e `fiche` : le contrôle « département absent » (59350) suppose un export partiel ; non pertinent sur l'export complet utilisé ici.
- Le champ n'apparaît qu'une fois le manifeste chargé pour ouvrir l'index ; sur export ancien sans `recherche.json.gz`, message « Recherche indisponible ».
