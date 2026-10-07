# Prototype A0 — carte France entière en tuiles vectorielles (PMTiles)

Date : 2026-10-07 · Agent : developpeur-ui · Branche jetable `poc/carte-france-tuiles` (non poussée, jamais fusionnée) · Fiche : `.claude/plans/2026-10-07-vague-a-0-prototype-performance.plan.md`

## Résumé exécutif

- Moteur WebKit (Playwright, sans fenêtre, Mac mini M4) : changement de scrutin sur 34 877 communes et 48 scrutins en **62 ms** (médiane, p90 72, max 128) avec un seul `setPaintProperty`. Budget < 100 ms tenu, seuil de 150 ms jamais atteint.
- Variantes : une couche par scrutin, seule l'opacité change : 20 ms, fondu natif (241 ms avec un fondu de 220 ms), mais 566 Mo de mémoire au lieu de 413 Mo. Boucle `setFeatureState` : 30 ms ; l'extrapolation de l'ADR (270-540 ms) est contredite.
- Données avant la 1re carte : 817 Ko (vue France, zoom 4) à 1,30 Mo (zoom 5), budget de 1,5 Mo tenu. Archive de 19,4 Mo. JS initial : 499 Ko gzip, au-dessus de la cible de 450 Ko mais sous le seuil de 550 Ko.
- Mémoire (`footprint`, après 50 changements) : 413 Mo en WebKit (budget < 600 Mo). Ouverture, document → carte colorée : 402 ms (médiane).
- **Tauri (WKWebView) non mesuré** : écran de session verrouillé (`CGSSessionScreenIsLocked = true`), aucune image n'est rendue. Constat : le protocole `tauri://` ignore `Range` (réponse 200 avec les 19,4 Mo). Une parade est intégrée : archive lue en mémoire (24 ms).
- Recommandations pour A1 : tippecanoe (BSD-2) ; PMTiles et `setPaintProperty` unique ; détail en JSON (décodage 4 ms, 422 Ko gzip contre 504 Ko en binaire). Le fondu n'est pas réalisable avec `fill-color-transition` (MapLibre ne fait pas de transition sur une expression dépendant des données).
- Décisions à soumettre : Q1 fondu, Q2 lecture des tuiles dans Tauri, Q3 « listes non classées en tête » (municipales), Q4 précision des bas zooms.

## 1. Livrables (branche `poc/carte-france-tuiles`)

| Fichier | Rôle |
|---|---|
| `scripts/export_tuiles.py` | Lecture seule de la vue `v_resultats_candidats_avec_bloc` (aucun classement modifié). Bloc dominant de chaque commune pour chaque scrutin, en SQL. Écrit du GeoJSONSeq, appelle tippecanoe et produit `communes.pmtiles`, `meta.json` et `detail/` |
| `web/src/Carte.tsx` | Source vectorielle `pmtiles://`, `promoteId` = code INSEE ; 3 stratégies (`paint`, `couches`, `etat`) ; `SourceMemoire` pour Tauri |
| `web/src/worker/details.ts` | Worker de l'infobulle : décodage JSON ou Int32, nom de la commune et résultats détaillés |
| `web/src/App.tsx`, `donnees.ts` | Page unique : sélecteur de scrutin, légende par bloc, égalité, listes non classées, n.d., source et légende de classement du scrutin, aucun nom de candidat |
| `web/src/banc.ts`, `web/banc/` | Instrumentation (`?banc=1`), écouteur local, lanceurs Chromium, WebKit et Tauri, analyse, mesures brutes `mesures-2026-10-07.jsonl` |
| `.gitignore` | `web/node_modules/`, `web/public/data/`, `web/src-tauri/target/` |

Base : `web/` et `scripts/export_web.py` repris de `origin/poc/tauri` (qui contient `poc/interface-web`). `Evolution.tsx` a été retiré (hors périmètre).

## 2. Tuilage

- **Codage** : propriété `s`, un caractère par scrutin, dans l'ordre des `id_election` (48 scrutins ayant des résultats). Les lettres `a` à `f` correspondent aux blocs dans l'ordre de `BLOCS_ORDERED`. `=` signale une égalité de voix en tête (affichée en blanc, décision du 2026-10-06). `n` signale des listes non classées en tête, `.` une absence de résultat (n.d., jamais 0). Les noms des communes sont retirés des tuiles et placés dans `detail/codes.json`, chargé au premier survol.
- **Outil** : tippecanoe v2.79.0 (felt), licence BSD-2. Compilé depuis les sources dans `/Volumes/le gros stockage/outils/tippecanoe-src` (`make`, environ 1 min, sqlite3 et zlib du système), sans brew et sans rien écrire sur le disque interne. ogr2ogr n'a pas été testé : GDAL est absent et l'installer par brew ajouterait des centaines de Mo de dépendances sur le disque interne. Il ne propose pas non plus l'équivalent de `--detect-shared-borders` ni la conservation de toutes les communes aux bas zooms.
- **Options** : `-Z3 -z10 --detect-shared-borders --no-feature-limit --no-tile-size-limit`. Aucune commune n'est fusionnée ni abandonnée. `--use-attribute-for-id` est écarté : il exige un identifiant numérique, ce qui est impossible avec 2A/2B. MapLibre `promoteId` accepte les chaînes.
- **Export** : 61 s pour 34 877 communes et 48 scrutins.

| Variante | Archive | Tuiles z5 métropole (gzip) |
|---|---|---|
| Précision par défaut (12), avec les noms | 30,8 Mo | — |
| Précision 12, sans les noms, `s` en chaîne | 27,4 Mo | 2,14 Mo |
| Idem, une propriété par scrutin (`s0`…`s47`) | — | 2,26 Mo (+5 %) |
| **Précision 10 aux bas zooms (`--low-detail=10`, retenue)** | **19,4 Mo** | **1,30 Mo** (4 tuiles : 32, 201, 267, 804 Ko) |
| Précision 9 | 15,8 Mo | 0,81 Mo |

Tuiles par zoom (précision 10) : z3 7 tuiles, z4 6, z5 10, z6 18, z7 38, z8 90, z9 284, z10 992 (10,6 Mo, 16 Ko au plus par tuile).

## 3. Mesures

Banc : 50 changements de scrutin (pas de 7 sur 48), chacun mesuré du « clic » (`setState`) à l'événement `idle`, c'est-à-dire jusqu'à ce que les nouvelles couleurs soient affichées. Fenêtre 1280×860 (carte de 600 px de haut, vue France au zoom ≈ 4,6, donc tuiles z4). 3 lancements à froid par cas, profil vierge. Les médianes des médianes sont reportées.

| Stratégie | WebKit : changement (méd. / p90 / max) | Chromium : changement (méd.) | WebKit : document → carte colorée | WebKit : mémoire `footprint` |
|---|---|---|---|---|
| **`paint`** (1 `setPaintProperty`, MapLibre recalcule les tuiles dans son worker) | **62 / 72 / 128 ms** | 81 ms | **402 ms** | **413 Mo** |
| `couches` (48 couches, seule l'opacité change) | 20 / 29 / 42 ms | 30 ms | 842 ms | 566 Mo |
| `couches` + fondu 220 ms | 241 ms (fondu compris), 1re image 18 ms | 247 ms | 706 ms | — |
| `etat` (boucle `setFeatureState`, référence) | 30 / 34 / 60 ms | 24 ms | (carte grise jusqu'au 1er `idle`) | 464 Mo |

- Avec `paint`, la première image après le clic (8 ms) montre encore les anciennes couleurs. Les nouvelles arrivent avec `idle` (≈ 62 ms), qui est donc le chiffre perçu.
- Chromium sans fenêtre : les temps d'ouverture (1 à 9 s) sont dominés par le démarrage du navigateur et ne sont pas retenus.
- Mémoire Chromium : la RSS cumulée (1,4 à 2 Go) compte plusieurs fois la mémoire partagée et n'est pas comparable. Tas JS : 15 à 53 Mo.
- **Données avant la 1re carte** (`transferSize`) : 817 Ko de PMTiles en 4 requêtes (en-tête et répertoire de 16,7 Ko, puis tuiles), plus `meta.json` (1,2 Ko gzip). Une vue au zoom 5 (fenêtre plus grande) demande 1,30 Mo.
- **JS initial gzip** : `index` 353 Ko + worker MapLibre 145 Ko + worker de détail 0,5 Ko = 499 Ko. MapLibre en représente l'essentiel. pmtiles ajoute environ 8 Ko.

| Budget ADR-0015 | Mesuré | Verdict |
|---|---|---|
| Ouverture → carte colorée < 1 s (seuil 1,5 s), Tauri à froid | Non mesuré dans Tauri. WebKit : 402 ms depuis le document ; le POC Tauri mesurait 300-550 ms de `open` à la navigation | Probablement 0,7-1,0 s, **à confirmer** |
| Changement d'année < 100 ms (seuil 150 ms), WebKit | 62 ms (max 128 ms) | Tenu (moteur WebKit, hors WKWebView) |
| JS initial < 450 Ko (seuil 550 Ko) | 499 Ko | Cible dépassée, seuil respecté |
| Données avant 1re carte < 1,5 Mo (seuil 3 Mo) | 0,82-1,30 Mo (web) ; Tauri : archive de 19,4 Mo lue localement en 24 ms | Tenu |
| Mémoire < 600 Mo (seuil 900 Mo) | 413 Mo (WebKit) | Tenu |

## 4. Format des résultats détaillés (tâche 4)

Scrutin 2022, présidentielle, 1er tour, France entière. 9 colonnes (inscrits, votants, exprimés, 6 blocs) alignées sur `codes.json`.

| Format | Brut | gzip | Décodage WebKit | Décodage Chromium |
|---|---|---|---|---|
| **JSON en colonnes (`null` = n.d.)** | 1 057 Ko | **422 Ko** | **3-5 ms** | 2-6 ms |
| Int32 petit-boutiste (−1 = n.d.) | 1 256 Ko | 504 Ko | < 1 ms | < 1 ms |
| `codes.json` (codes et noms, commun aux deux) | 873 Ko | 271 Ko | — | — |

Recommandation : **JSON**. L'écart de décodage (≈ 4 ms dans le worker) n'est pas décisif et le JSON est plus petit une fois compressé. Les « lectures » mesurées sur `vite preview` incluent la compression faite par le serveur et ne sont pas retenues.

## 5. Tauri

- Le build de mesure (`Banc A0.app`, 23,2 Mo, tuiles comprises) se compile. Il a été lancé 5 fois. À chaque fois, `demarrage` a été reçu, mais ni `style.load` ni aucune image. L'écran de la session était verrouillé (`CGSSessionScreenIsLocked = true`) : WKWebView ne déclenche alors pas `requestAnimationFrame`, et MapLibre ne charge pas son style. Les fenêtres ont été fermées (`kill`) après chaque lancement.
- **Constat mesuré** : `fetch(tauri://localhost/data/communes.pmtiles, Range: bytes=0-99)` renvoie `200` et le fichier complet (19 420 309 octets, 24 ms), sans `Content-Range`. La lecture par plages de PMTiles est donc impossible telle quelle.
- Parade intégrée : `SourceMemoire` (`Carte.tsx`, 12 lignes), active seulement sous `tauri:`. L'archive est lue une fois puis découpée en mémoire, ce qui coûte environ 19 Mo de mémoire en plus. Cette parade n'a pas été vérifiée à l'écran (voir ci-dessus).
- Pour mesurer, session ouverte : `bash`, puis `python3 web/banc/ecouteur.py mesures.jsonl &`. Ensuite, construire avec `VITE_BANC="banc=1&rotation=1&rapport=http://127.0.0.1:8765/"` et `npx tauri build --bundles app --config web/banc/tauri-banc.json`. Lancer ensuite `python3 web/banc/banc_tauri.py 12`, puis `python3 web/banc/analyse.py` (4 stratégies en rotation × 3 lancements). Cela ouvre 12 fenêtres pendant environ 3 min.

## 6. Limites

1. WebKit mesuré via Playwright (WebKit 26, sans fenêtre), pas via WKWebView/Tauri. Moteur JS et rendu de même famille, mais composition et processus différents.
2. Une seule vue mesurée (France, zoom ≈ 4,6). Le coût de `paint` dépend du nombre de tuiles chargées (recalcul de toutes les tuiles visibles). Au zoom 7-9, les tuiles sont plus nombreuses mais plus petites ; ce cas n'est pas mesuré.
3. Le bloc dominant est calculé sur toutes les voix, listes non classées comprises (code `n`). Ce choix n'est pas validé (Q3). Les communes absentes des contours actuels (anciens codes) sont n.d.
4. `etat` ne couvre que les communes des tuiles déjà chargées (référence de mesure seulement). En mode `couches`, l'infobulle suit la couche initiale.
5. Aucun test automatisé du SQL de dominance ni de l'égalité (prototype jetable). Le survol et le worker n'ont pas été vérifiés à l'œil.
6. Outils hors dépôt, tous sur le disque externe : tippecanoe (`outils/tippecanoe-src`), Playwright et WebKit (`outils/playwright-navigateurs`, 320 Mo), copie de la base (`outils/tmp/poc-a0/ministere.duckdb`, 1,2 Go, à supprimer après lecture).

## 7. Décisions à soumettre (questions fermées)

- **Q1 Fondu entre scrutins** : (a) aucun, `paint`, 62 ms ; (b) fondu natif à 48 couches, 20 ms, +150 Mo, ouverture ×2 ; (c) fondu entre 2 couches (actuelle et précédente), à prototyper.
- **Q2 Tuiles dans Tauri** : (a) archive lue en mémoire (fait, +19 Mo) ; (b) protocole Rust gérant `Range` ; (c) dossier `{z}/{x}/{y}.pbf` non compressé.
- **Q3 Municipales, listes non classées en tête** : (a) couleur propre, gris clair `--grey-300` (prototype) ; (b) n.d. ; (c) dominance calculée sur les seules listes classées.
- **Q4 Précision des bas zooms** : (a) 10 (1,30 Mo en vue z5) ; (b) 9 (0,81 Mo, contours plus anguleux, à juger à l'œil).
- **Q5 Outil de tuilage** : (a) tippecanoe compilé sur le disque externe ; (b) tippecanoe par brew ; (c) GDAL/ogr2ogr.
