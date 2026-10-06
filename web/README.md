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
