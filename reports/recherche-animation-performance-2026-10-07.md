# Recherche — animation et performance de l'interface web (France entière)

Date : 2026-10-07 · Rôle : ingénieur front (performance, animation) · Lecture seule hors ce rapport.
Base : maquette `origin/poc/interface-web` (HdF, 3 782 communes) et POC `origin/poc/tauri` (WebKit).

## Résumé

1. Le goulot à 35 000 communes est la boucle `setFeatureState` (une ligne par commune, thread principal) : 15-22 ms pour 3 782 communes dans la maquette ; extrapolation linéaire ~140-200 ms (WebKit : 29-58 ms mesurés pour 3,8 k, soit ~270-540 ms), donc **budget < 100 ms non tenu** sans changement.
2. Correctif principal : porter les résultats de tous les scrutins dans les tuiles (propriété compacte par commune) et changer d'année par **une seule** `setPaintProperty` ; à valider par mesure (le coût se déplace dans le worker de tuiles).
3. Contours en PMTiles (une archive, requêtes `Range`), résultats en fichiers par scrutin, binaires compacts (colonnes entières), décodés dans un Web Worker.
4. Animation : sobre et utile seulement. Fondu de 220 ms sur les couleurs de la carte (ou saut si le budget n'est pas tenu), View Transitions natives pour les pages (support Safari 18+, donc WebKit/Tauri sous macOS 27), chiffres-clés sans compteur animé, graphiques tracés une fois.
5. Aucune bibliothèque d'animation : CSS + View Transitions natives (0 Ko). Motion (~18 Ko gz hors cas avancés) seulement si un besoin de geste/physique apparaît (non prévu).
6. `prefers-reduced-motion` : tous les jetons de durée à 0 ms ; le contenu ne dépend jamais d'une animation.
7. Mesure : Performance API (`mark`/`measure`) dans le code, tests Playwright en CI avec seuils, Lighthouse pour le build web, trace DevTools pour l'investigation ; WebKit mesuré à part (Tauri).
8. Décisions pour Mathias : voir § 7 (3 questions fermées).

## 1. Constat sur la maquette

- `Carte.tsx` : `donnees.resultats.codes.forEach(... m.setFeatureState(...))` à chaque changement de scrutin/mode/bloc, plus un `setPaintProperty` complet. Le calcul `blocDominant` est refait pour chaque commune à chaque changement (aucune mémoïsation).
- Source GeoJSON unique (3,64 Mo pour HdF) : à l'échelle France, ~35 000 communes simplifiées = ~30-40 Mo de GeoJSON (estimation par proportion, à mesurer), inacceptable en chargement initial.
- `resultats.json` 1,1 Mo pour 10 scrutins HdF ; à 35 k communes et ~25 scrutins, ordre de grandeur 25-60 Mo en JSON (estimation), 5-10× moins en colonnes binaires.
- Sélecteurs natifs (radio), focus visible : bonne base d'accessibilité à conserver.
- Mesures de référence : Chromium 15-22 ms, WebKit/Tauri 29-58 ms (médiane ~39 ms), démarrage 0,86-1,13 s, mémoire 257-435 Mo.

## 2. Tokens de mouvement proposés (CSS)

Le design system v2 définit déjà `--duration-fast 140 / base 220 / slow 360 ms`, `--ease-standard`, `--ease-out` et la coupure `prefers-reduced-motion` pour `--duration-fast`. Proposition : compléter, sans rien contredire.

```css
:root {
  /* existants (tokens.css) */
  --duration-fast: 140ms;   /* survol, focus, boutons */
  --duration-base: 220ms;   /* fondu de couleurs de carte, apparition de blocs */
  --duration-slow: 360ms;   /* transition de page, tracé de courbe */
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  /* ajouts */
  --duration-instant: 0ms;          /* état final immédiat */
  --duration-map-fade: var(--duration-base);   /* couleurs de la carte */
  --duration-page: var(--duration-slow);       /* View Transition entre pages */
  --stagger-step: 30ms;             /* décalage entre éléments d'une liste, max 6 pas */
  --ease-in: cubic-bezier(0.4, 0, 1, 1);       /* sorties seulement */
}

/* Une seule règle de coupure, pour TOUS les jetons (le fichier actuel ne coupe que --duration-fast ; à compléter) */
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fast: 0ms; --duration-base: 0ms; --duration-slow: 0ms;
    --duration-map-fade: 0ms; --duration-page: 0ms; --stagger-step: 0ms;
  }
  ::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) {
    animation: none !important;
  }
}

/* Transition de page (View Transitions natives, voir R4) */
@view-transition { navigation: auto; }            /* seulement si multi-documents */
::view-transition-old(root) { animation: fade-out var(--duration-page) var(--ease-in) both; }
::view-transition-new(root) { animation: fade-in  var(--duration-page) var(--ease-out) both; }
@keyframes fade-in  { from { opacity: 0; } }
@keyframes fade-out { to   { opacity: 0; } }
```

Règles : animer uniquement `opacity` et `transform` (compositeur) ; jamais de rebond, d'ombre, ni d'échelle > 2 % ; durée maximale 360 ms ; aucune animation en boucle.
Constat : la règle actuelle du skill ne coupe que `--duration-fast` (à vérifier dans `tokens.css`, lignes 207-210) ; il faut couper aussi `base` et `slow`.

## 3. Animation : ce qui a du sens, ce qu'il faut éviter

| # | Recommandation | Gain | Coût | Risque |
|---|---|---|---|---|
| A1 | **Carte, changement d'année/scrutin** : fondu des couleurs 220 ms (`fill-color-transition: { duration: 220 }` côté style MapLibre, supporté nativement pour les propriétés de peinture) ; saut immédiat si le budget de rendu est dépassé (> 100 ms) ou en mouvement réduit (`duration: 0`). Sens : le changement est perçu comme « la même carte, autre année », sans clignotement. | Continuité perçue ; 0 Ko | S | Moyen : la transition MapLibre interpole les couleurs d'une expression de données ; à vérifier avec `feature-state` ou `match` sur 35 k communes (coût GPU/CPU), sinon saut. Le fondu ne doit jamais retarder l'accès à la donnée (l'infobulle lit toujours la valeur finale). |
| A2 | **Pages** : View Transitions natives, fondu 360 ms entre routes (`document.startViewTransition` autour du changement de route React, ou CSS `@view-transition` si pages multi-documents). | Cohérence de navigation ; 0 Ko, aucune dépendance | S | Faible : same-document supporté Safari 18+, Chrome 111+, Firefox 144+ ([Chrome for Developers](https://developer.chrome.com/blog/view-transitions-in-2025)). Prévoir le repli : si `startViewTransition` absent, changement immédiat. React : ne pas envelopper de `await` long ; l'état doit être appliqué de façon synchrone dans le rappel (voir skill `vercel-react-view-transitions`). |
| A3 | **Chiffres-clés** : pas de compteur qui défile (retarde la lecture, n'est pas lu par les lecteurs d'écran, contraire à la sobriété « chiffre = fait »). Au plus, un fondu de 140 ms au changement de valeur. Largeur fixe (`font-variant-numeric: tabular-nums`) pour éviter le saut de mise en page. | Lisibilité, pas de décalage | S | Nul |
| A4 | **Graphiques d'évolution** : tracé initial d'une seule fois (stroke-dashoffset 360 ms, `ease-out`), puis mises à jour par fondu 140 ms ; pas de réanimation à chaque survol. Les valeurs exactes restent dans le tableau (alternative accessible). | Vivant sans bruit | S | Faible (Observable Plot est du SVG statique : animer via CSS sur le `path`) |
| A5 | **Micro-interactions** : survol/focus des boutons et pastilles via `--transition-colors` (140 ms, déjà défini). Trait de survol de commune : immédiat (pas de transition, c'est un retour de pointage). | Retour d'action | S | Nul |
| A6 | **Squelettes (skeletons)** : blocs gris aplatis aux dimensions finales (aucun décalage), sans scintillement animé ; fondu de 140 ms vers le contenu. Seulement pour > 200 ms d'attente. | Performance perçue | S | Nul |
| A7 | Bibliothèque : **CSS + View Transitions + `fill-color-transition`**. Motion (ex-Framer Motion, ~18 Ko gz pour `m`+`domAnimation` avec LazyMotion, ordre de grandeur à vérifier au build) uniquement pour des gestes (glisser, ressort) : non prévu. | 0 Ko de JS | S | Nul ; WebKit/Tauri : tout l'ensemble est supporté |
| A8 | **À éviter** : parallaxe, animations de défilement, compteurs animés, fondu séquentiel des communes (35 k éléments), animation de zoom automatique à chaque scrutin (perd la position choisie, désoriente), rebonds, grandes durées (> 400 ms), ombres animées (contraire au DS), animation en boucle (WCAG 2.2.2). | Sobriété, accessibilité | — | — |
| A9 | `prefers-reduced-motion` : jetons à 0 ms (§ 2), lecture dans JS par `matchMedia` pour `fill-color-transition` et `flyTo`/`easeTo` (`animate: false`). Test automatisé : émulation `reduce` et vérification que `getAnimations()` est vide. | Accessibilité (WCAG 2.3.3, 2.2.2) | S | Nul |

## 4. Performance réelle et perçue

| # | Recommandation | Gain attendu | Coût | Risque |
|---|---|---|---|---|
| P1 | **Changement d'année sans boucle** : tuiles vectorielles contenant, par commune, une chaîne/propriété compacte des blocs dominants de tous les scrutins (1 caractère par scrutin) ; l'année choisit l'index par expression (`["slice", ["get","d"], k, k+1]` ou propriétés `d_<id>`) et un seul `setPaintProperty`. Alternative : `setFeatureState` seulement pour les communes visibles (`queryRenderedFeatures`) et le reste à la demande. | Ramène le coût JS de O(35 000) à O(1) ; objectif < 100 ms, y compris WebKit | M | Moyen : le coût se reporte sur le re-travail des tuiles dans le worker ; **prototype et mesure obligatoires** sur 35 k communes avant d'engager |
| P2 | **Contours en PMTiles** (archive unique, requêtes `Range` ; en Tauri via le protocole local, sans serveur) générés par tippecanoe ou `ogr2ogr` MVT depuis DuckDB ; niveaux de simplification par zoom ; `promoteId` sur le code INSEE. Remplace le GeoJSON entier. | Ouverture : de ~30-40 Mo à quelques centaines de Ko de tuiles initiales (estimation à mesurer) ; mémoire ↓ | M | Moyen : pipeline de tuilage à ajouter à l'ETL (outil externe, vérifier licence tippecanoe BSD-2) ; protocole PMTiles dans MapLibre (plugin `pmtiles`, ~15 Ko) et CSP Tauri `connect-src` |
| P3 | **Résultats en binaire compact** par scrutin : une colonne par bloc en `Uint16` (pour mille des exprimés) + `exprimes`/`inscrits`/`votants` en `Uint32`, un fichier par scrutin (~35 k × 10 colonnes × 2 o ≈ 0,7 Mo brut, < 300 Ko gzip, estimation). Chargé à la demande, à l'ouverture du seul scrutin affiché + préchargement du suivant. | Données ÷ 5-10 vs JSON ; décodage quasi nul | M | Faible : format maison à documenter (ADR) ; valeur manquante par sentinelle (`0xFFFF`), jamais 0 |
| P4 | **Arrow IPC / Parquet** : écartés pour l'instant. Arrow ajoute ~100+ Ko de JS pour des tableaux déjà triviaux ; `hyparquet` ou duckdb-wasm (~plusieurs Mo) réservés au drill-down par bureau de vote si on abandonne le précalcul. | — | L | Élevé (poids/complexité) pour un gain nul à l'échelle communale |
| P5 | **Chargement progressif** : démarrage avec `meta` + scrutin par défaut + tuiles de la vue ; autres scrutins en idle (`requestIdleCallback`) ; fichiers par département pour les drill-downs (bureaux de vote, tableaux) à la demande. | Ouverture < 1 s ; pas de coût tant qu'on ne navigue pas | M | Faible |
| P6 | **Web Worker** pour décodage/agrégations (chiffres-clés nationaux, évolution), via `new Worker(new URL(...))` (Vite) et `Transferable` (ArrayBuffer sans copie). Pas de worker pour `setFeatureState` (API main thread). | Thread principal libre pendant les chargements | S-M | Faible ; CSP `worker-src 'self' blob:` déjà prévue |
| P7 | **Mémoïsation React** : `useMemo` sur le tableau de blocs dominants par scrutin (calculé une fois, `Uint8Array`), `React.memo` sur légende/chiffres, l'infobulle isolée dans son composant avec état local (le `setInfo` à chaque `mousemove` re-rend aujourd'hui toute la `Carte`), `useDeferredValue` pour le sélecteur. Pas de re-création de l'index `Map` (déjà `useRef`). | Moins de rendus parasites ; survol fluide | S | Faible |
| P8 | **Survol** : limiter `queryRenderedFeatures` à une fois par image (`requestAnimationFrame`), ne mettre à jour l'état React que si la commune change. | Évite le travail inutile à 60 Hz sur 35 k polygones | S | Faible |
| P9 | **Squelette + préchargement** : carte vide (papier + cadre) dès le premier rendu, polices `font-display: swap` avec préchargement des 2 graisses utilisées, `<link rel="modulepreload">`, `preload` des tuiles de la vue initiale. Séparation du code (`React.lazy`) des pages non affichées ; MapLibre (≈ 145 Ko gz + worker) dans un chunk dédié chargé seulement pour les pages carte. | Ouverture perçue < 0,5 s | S | Faible |
| P10 | **Quantification des couleurs** : pour les scores, échelle fixe 0-100 en 0-255 et `interpolate` (déjà fait). Pour les classes de l'économie : `step`, moins coûteux que `interpolate`. | Marginal | S | Nul |
| P11 | **Mémoire** (257-435 Mo mesurés en HdF) : cible < 600 Mo en France entière ; `maxTileCacheSize` MapLibre réduit, libération des scrutins non récents (LRU de 3). | Stabilité Mac mini/MacBook Air | S | Faible |
| P12 | **Hors thème** : compresser en Brotli à la distribution (Tauri compresse déjà les ressources ; 6,8 Mo → 4,85 Mo mesuré). | Taille de l'application | S | Nul |

## 5. Mesure et CI

| # | Recommandation | Gain | Coût | Risque |
|---|---|---|---|---|
| M1 | **Performance API dans le code** : `performance.mark('annee:clic')` → `performance.measure('annee:image', ...)` après le `render` MapLibre suivant ; `PerformanceObserver` pour LCP/CLS/INP (`web-vitals`, ~2 Ko). Remplacer le `console.info` de la maquette ; désactivé en production (ou journal local seulement, aucune télémétrie, cf. sobriété et vie privée). | Mesures reproductibles | S | Nul |
| M2 | **Test de performance automatisé** (Playwright, Chromium en CI) : build de production, jeu de données France synthétique ou réel, 3 scénarios (ouverture, changement d'année ×10, panoramique), seuils en § 6, médiane sur 5 exécutions, tolérance +25 % pour la variance des runners. Échec de la CI au-delà. | Aucune régression silencieuse | M | Moyen : runners GitHub bruités ; utiliser des seuils larges en CI et des seuils stricts sur le Mac de référence |
| M3 | **Lighthouse** (serveur DevTools disponible : `lighthouse_audit`, `performance_start_trace`) sur `vite preview` : LCP, TBT, CLS, accessibilité ≥ 95 ; trace pour l'investigation (non bloquant). Lighthouse ne remplace pas la mesure WebKit. | Détection de poids, a11y | S | Faible : résultats approximatifs sur une carte WebGL |
| M4 | **Mesure WebKit/Tauri sur le Mac de référence** : script manuel documenté (horodatage `open` → `idle`, comme le POC Tauri) à chaque version publiée ; résultats consignés dans `reports/`. | Réalité du produit final | S | Nul (manuel) |
| M5 | **Budget de taille en CI** : `size-limit` ou script `du` sur `dist/` (JS initial gzip, chunk carte, données du scrutin initial). | Contrôle de poids | S | Nul |
| M6 | **Accessibilité en CI** : `axe-core` via Playwright (nécessaire car l'animation et la carte ne sont pas lisibles par défaut) + test `reduced-motion`. | Conformité | S | Faible |
| M7 | **Profilage mémoire** ponctuel (heap snapshot après 50 changements d'année : pas de croissance monotone). | Fuites détectées | S | Nul |

## 6. Budget de performance proposé

| Indicateur | Cible | Seuil d'échec CI | Mesuré (HdF) |
|---|---|---|---|
| Ouverture de l'application Tauri → carte colorée (démarrage à froid, Mac mini M4) | < 1 s | 1,5 s | 0,86-1,13 s |
| LCP (web, build de production, local) | < 1,0 s | 1,5 s | n.m. |
| Changement d'année/scrutin → image suivante (France entière, WebKit) | < 100 ms | 150 ms | 29-58 ms (3,8 k) |
| Idem Chromium (CI) | < 80 ms | 120 ms | 15-22 ms (3,8 k) |
| Survol : durée d'une image | < 16 ms (60 Hz) | 33 ms (tâche > 50 ms = échec) | n.m. |
| INP | < 200 ms | 300 ms | n.m. |
| CLS | 0 | 0,05 | n.m. |
| JS initial (gzip) | < 450 Ko | 550 Ko | 432 Ko + 145 Ko worker |
| Données avant 1re carte colorée (gzip) | < 1,5 Mo | 3 Mo | 1,5 Mo (HdF) |
| Mémoire (empreinte totale, France entière, après usage) | < 600 Mo | 900 Mo | 257-435 Mo |
| Animations | ≤ 360 ms, 0 en `reduce` | tout `getAnimations()` actif en `reduce` | — |

« n.m. » = non mesuré. Les cibles France entière sont des hypothèses à confirmer par le prototype P1/P2.

## 7. Décisions à trancher (questions fermées pour Mathias)

1. Valider le fondu de couleurs de la carte (A1, 220 ms) comme comportement par défaut, avec saut en repli si le budget n'est pas tenu : oui / non ?
2. Autoriser un prototype P1+P2 (tuiles PMTiles + changement d'année sans boucle) comme jalon avant tout portage France entière : oui / non ? (Il introduit un outil de tuilage dans l'ETL ; décision d'architecture, ADR à prévoir.)
3. Format des résultats (P3) : binaire maison par scrutin, ou conserver du JSON compressé jusqu'à la mesure du prototype ?

## Sources

- [What's new in view transitions (2025 update), Chrome for Developers](https://developer.chrome.com/blog/view-transitions-in-2025) — support same-document : Chrome 111, Safari 18, Firefox 144.
- [Smooth transitions with the View Transition API, Chrome for Developers](https://developer.chrome.com/docs/web-platform/view-transitions)
- [Mapping the US elections, guide to feature state, Mapbox](https://www.mapbox.com/blog/mapping-the-us-elections-the-2020-edition-guide-to-feature-state) — feature state évite de réanalyser la géométrie ; `promoteId`.
- [Feature state, MapLibre](https://maplibre.org/flutter-maplibre-gl/advanced/feature-state/)
- Mesures internes : `reports/poc-interface-web-2026-10-06.md` (branche `poc/interface-web`), `reports/poc-tauri-2026-10-06.md` (branche `poc/tauri`).
- Non vérifiées en ligne (à confirmer avant décision) : poids de Motion, coût réel de `fill-color-transition` sur 35 k polygones, tailles France entière (extrapolations).
