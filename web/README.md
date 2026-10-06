# Maquette web — Élections, présidentielles, Hauts-de-France

Maquette d'une page (POC) pour juger l'interface web de production. Site statique, sans serveur.

## Commandes

```bash
# 1. Données (depuis la racine du dépôt ; base DuckDB lue en lecture seule)
uv run python scripts/export_web.py            # écrit web/public/data/ (non commité)

# 2. Application (depuis web/)
npm install
npm run dev        # http://localhost:5173
npm run build      # tsc --noEmit (strict) puis build dans web/dist/
npm run preview    # sert web/dist/ sur http://localhost:4173
```

## Architecture

- `scripts/export_web.py` : vues DuckDB (`v_scores_commune_pres`, `v_participation_commune_pres`)
  → `communes.geojson`, `resultats.json`, `evolution.json`, `meta.json` (sources, licences,
  légendes de classement, couleurs de blocs issues de `_blocs_politiques.py`).
- `src/donnees.ts` : types des fichiers, chargement, calculs par commune, formats français.
- `src/App.tsx` : en-tête, sélecteurs (boutons radio natifs), chiffres-clés, légendes, sources.
- `src/Carte.tsx` : MapLibre GL ; géométrie chargée une fois, recoloration par `feature-state`.
- `src/Evolution.tsx` : graphique Observable Plot (part des exprimés par bloc).
- Styles : `tokens.css` du skill `design-system-mi` importé tel quel + `src/styles.css`
  (uniquement des `var(--…)`). Polices embarquées (Fontsource), aucun CDN.
- Seul appel réseau à l'exécution : tuiles du fond Plan IGN (Géoplateforme) ; la carte des
  communes s'affiche sans elles.

## Application Mac (Tauri)

POC : la même page emballée en application macOS (Tauri v2, WebView système, aucune commande
Rust). Données embarquées dans le binaire ; seul accès réseau autorisé (CSP) : tuiles Plan IGN
sur `data.geopf.fr`, facultatives (les communes s'affichent hors ligne).

Prérequis : Rust (rustup), Xcode Command Line Tools, Node ; données exportées (étape 1).

```bash
npm run tauri:dev     # fenêtre de développement sur le serveur Vite (rechargement à chaud)
npm run tauri:build   # build Vite puis .app et .dmg non signés (arm64)
open "src-tauri/target/release/bundle/macos/Ministère de l'Info.app"
```

Le `.dmg` est dans `src-tauri/target/release/bundle/dmg/`. Le dossier `target/` pèse ~0,8 Go :
le placer sur un disque externe via `CARGO_TARGET_DIR` si besoin. Application non signée :
une copie téléchargée est bloquée par Gatekeeper (Réglages Système > Confidentialité et sécurité > « Ouvrir quand même »).
