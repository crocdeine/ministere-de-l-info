# Application web et application Mac (ADR-0015)

Interface Vite + React + TypeScript + MapLibre, emballée en application Mac par Tauri v2.
Données précalculées par l'export Python (lecture seule de la base DuckDB). Streamlit reste la
référence des chiffres jusqu'au portage complet (pages non portées : renvoi vers Streamlit).

## Commandes

```bash
# 1. Données (racine du dépôt) : ≈ 75 s pour la France entière, 84 Mo écrits
uv run python scripts/export_web.py --tippecanoe /chemin/vers/tippecanoe   # → web/public/data/
#    échantillon : --departements 80 ; sans tuiles : --sans-tuiles

# 2. Application (dans web/)
npm ci
npm run dev           # http://localhost:5173
npm test              # vitest (logique pure)
npm run build         # tsc --noEmit puis build dans dist/
npm run budget        # JS initial gzip < 450 Ko (bloquant en CI)
npm run mesure        # WebKit sans fenêtre : ouverture, données, changement de tour, mémoire
```

`npm run mesure` demande `playwright-core` et WebKit (`npx playwright-core install webkit` ;
sur le Mac du projet : `PLAYWRIGHT_BROWSERS_PATH="/Volumes/le gros stockage/outils/playwright-navigateurs"`).
Options : `--strict` (échec au-delà des seuils de l'ADR-0015), `--changements N`,
`--mouvement-reduit`. Résultat : `test-results/mesure.json`.

## Organisation

| Fichier | Rôle |
|---|---|
| `src/donnees.ts` | type unique du manifeste, contrôle de version de schéma, lecture des JSON gzip, formats français |
| `src/etats.ts` | états de la carte (blocs, égalité, non classé, n.d., hors périmètre), choix du tour, expression de couleur |
| `src/Carte.tsx` | MapLibre, tuiles PMTiles, fondu croisé entre deux couches |
| `src/maplibre.ts` | chargement de MapLibre (fichiers ESM d'origine), lecture de l'archive en mémoire sous Tauri |
| `src/worker/details.ts` | résultats détaillés de l'infobulle, décodés hors du thread principal |
| `src/PageElections.tsx`, `src/Legende.tsx`, `src/App.tsx` | page, légende et étiquette de méthode, navigation |
| `src/mesure.ts`, `perf/` | instrumentation (`?mesure=1`), budget de taille, mesures WebKit |

Styles : `tokens.css` du skill `design-system-mi` importé tel quel + `src/styles.css` (uniquement
des `var(--…)`). Palette « Papier » en surfaces (bandeau, filtres), jamais sous la carte.
Seul appel réseau : fond Plan IGN (facultatif ; les communes s'affichent hors ligne).

## Application Mac (Tauri)

Prérequis : Rust (rustup), Xcode Command Line Tools, Node ; données exportées (étape 1).

```bash
npm run tauri:build -- --bundles app   # .app non signé (arm64) ; ≈ 21 min avec 84 Mo de données embarquées
open "src-tauri/target/release/bundle/macos/Ministère de l'Info.app"
```

Le protocole `tauri://` ignore les requêtes par plages : l'archive de tuiles est lue une fois en
mémoire (`SourceMemoire`) ; ce chemin se vérifie dans un navigateur avec `?memoire=1`
(`MESURE_PARAMS="&memoire=1" npm run mesure`). `vite preview` applique la CSP de `tauri.conf.json`,
donc le test de fumée signale toute ressource qu'elle bloquerait. Mesurer dans l'app (session ouverte, écran déverrouillé) : compiler avec
`VITE_MESURE="mesure=1&rapport=http://127.0.0.1:8765/"` et une CSP autorisant cette adresse en
`connect-src`, lancer un écouteur local qui enregistre les POST, puis ouvrir l'app.
