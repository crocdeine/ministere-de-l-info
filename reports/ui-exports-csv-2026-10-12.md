# Exports Excel et CSV (vague A, lot A6), 2026-10-12

## Résumé exécutif
- Décision de Mathias (2026-10-12), après lecture du premier CSV (« pas très clair ») : **Excel (.xlsx) + CSV brut**.
- Excel : onglet « Données » (tableau dès la ligne 1, en-têtes en gras et figés, nombres numériques, pourcentages à 2 décimales, entiers avec séparateur de milliers, codes INSEE et de bureau en cellules texte, cellule absente pour n.d.) ; onglet « Notes » (clé / valeur : titre, sources, licence ODbL, dates, filtre, blocs, classement par scrutin, méthode, définition de chaque colonne).
- CSV : même tableau dès la ligne 1, puis ligne vide et les mêmes notes préfixées « # » ; UTF-8 avec BOM, `;`, décimale `,`.
- Contenu : colonnes sans objet retirées (Voix et Part NC seulement s'il y a des non classés, Remarques si vide) ; Votants, Exprimés et voix par bloc ajoutés ; « Méthode » devient « Classement des blocs » (« Grille officielle » / « Reconstruction documentée ») ; artefacts « , » et répétition « Classement des blocs : » supprimés ; libellés avec unités.
- Bibliothèque : `fflate` 0.8 (MIT, zéro dépendance, écriture seule), classeur XML écrit à la main ; import dynamique : **+1,7 Ko gzip** chargés à la demande, **+≈ 6 Ko gzip** dans le JS initial (code d'export), total 405,3 Ko (cible 450). Paquet `xlsx` écarté. `npm audit` : 0 vulnérabilité.
- Tauri : commande `enregistrer_export` (octets bruts, nom en en-tête, `.csv` ou `.xlsx` seulement, 32 Mio, boîte « Enregistrer sous »), permission unique `allow-enregistrer-export`, ni `fs` ni `dialog:*`, CSP inchangée. Renommage de `enregistrer_csv` (qui n'est plus limité au CSV).
- Vérifications : tsc, vitest (42), build, budget, audit, e2e url, fiche et export (télécharge puis relit Excel et CSV, WebKit et Chromium), clippy sans avertissement, `cargo test` (2).
- Non vérifié : ouverture dans Excel, Numbers, LibreOffice (à faire par Mathias) ; enregistrement réel dans le `.app` (corps binaire de l'IPC Tauri, non exécutable sans fenêtre).

## Colonnes
Historique (fiche) : Code INSEE, Commune, Scrutin, Classement des blocs, Inscrits, Votants, Exprimés, Participation (% des inscrits), Voix par bloc, Part par bloc (% des exprimés), Remarques. Bureaux : idem avec « Bureau de vote » à la place du classement. Scrutin (page Élections) : Code INSEE, Commune, Bloc en tête, Part du bloc en tête (% des exprimés), effectifs, voix par bloc.

## Limites
- Valeurs en % stockées en points (68,21) avec format `0.00` et unité dans le titre de colonne, pas en fraction Excel.
- Population, économie et élus de la fiche ne sont pas exportés.
- Lien de méthode : tag `v<version>` du dépôt public ; il doit contenir `docs/methodologie.md`.
