# Exports CSV (vague A, lot A6), 2026-10-12

## Résumé exécutif
- Module `web/src/export-csv.ts` : UTF-8 avec BOM, séparateur `;`, décimale `,` (2 décimales au plus), CRLF, absence = cellule vide (jamais 0).
- En-tête de lignes `# …` : titre, source(s) (mentions du manifeste), licence (ODbL + contenus sous licence producteur), « Données du », « Export du », méthode (docs/methodologie.md sur GitHub), format, blocs, légende de classement de chaque scrutin (officielle ou reconstruit).
- Trois exports : historique électoral de la fiche (ordre et filtres de l'écran), bureaux de vote de la fiche, une ligne par commune pour le tour affiché de la page Élections.
- Codes INSEE et codes de bureau en texte (zéros conservés) ; texte commençant par `= + - @` préfixé d'une apostrophe (injection de formule).
- Nom : `ministere-info_{vue}_{identifiant}_{AAAA-MM-JJ}.csv`.
- Vérifications : tsc, vitest (40 tests dont format CSV), build, budget (398,9 Ko gzip, tenu), npm audit, e2e url, fiche et nouveau `e2e:export` (téléchargement réel puis relecture, WebKit et Chromium).
- Non vérifié : ouverture dans Numbers/LibreOffice (à faire par Mathias) ; téléchargement dans le `.app` Tauri (pas de recompilation).

## Tauri : point bloquant probable
Aucune capability ni plugin dans `web/src-tauri`. Le lien `<a download>` sur un `blob:` est connu pour ne rien faire dans le WKWebView de Tauri 2 sans traitement côté Rust ; à confirmer sur un `.app`. Option la plus restreinte : `tauri-plugin-dialog` côté Rust seulement, avec une commande `enregistrer_csv(nom, contenu)` qui ouvre la boîte « Enregistrer sous » et n'écrit que le chemin choisi. Pas de plugin `fs`, pas de permission `fs:*`, pas de changement de CSP. Côté web : appel `invoke` si `window.__TAURI_INTERNALS__` existe, sinon blob.

## Hors lot
Population et économie de la fiche, listes d'élus (non exportés : petits blocs, pas de tableau de données). Variante « LISEZMOI à côté » écartée : l'en-tête `#` reste dans le fichier.
