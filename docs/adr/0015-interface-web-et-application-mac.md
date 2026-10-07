# 0015 — Interface web emballée en application Mac (Tauri), données précalculées

Date : 2026-10-07
Statut : Proposé — révise l'[ADR-0002](0002-streamlit-vs-fastapi.md)
Décideurs : Mathias (orientation du 2026-10-06), instruction : agent architecte

## Résumé

- Orientation déjà prise par Mathias le 2026-10-06 (`docs/orientations.md`) : interface web moderne,
  emballée en application Mac (Tauri), non signée, public très restreint. Cet ADR fixe le **modèle de
  données** et le **plan de migration**.
- Mesures sur la base réelle (1,29 Go, 48 scrutins chargés, 2 926 846 lignes de bureaux de vote) :
  les agrégats par bloc tiennent en JSON précalculé, **bureau de vote compris** (≈ 67 Mo compressés) ;
  seul le détail **par candidat** dépasse ce que le JSON supporte (2,5 Go bruts au bureau de vote).
- Recommandation : **option B** — données précalculées par un export Python (JSON, ou binaire compact
  si le prototype le justifie), découpées par scrutin et par département, contours en tuiles
  vectorielles (PMTiles), le tout inclus dans l'application. DuckDB embarqué (DuckDB-wasm sur Parquet)
  reporté au premier besoin de détail par candidat, par un ADR distinct.
- Verrou de performance (rapport `reports/recherche-animation-performance-2026-10-07.md`) : la
  recoloration commune par commune de la maquette coûterait ~270-540 ms en WebKit pour 35 000
  communes (budget < 100 ms). Un **prototype mesuré** (tuiles + changement d'année en une seule
  instruction) est le premier lot, avant tout portage France entière.
- Streamlit est gelé (corrections de bugs seulement) et retiré page par page, à parité.

## Contexte

L'ADR-0002 (2026-05-27) a retenu Streamlit pour un usage local mono-utilisateur. Depuis :

1. La maquette web (`origin/poc/interface-web`, rapport `reports/poc-interface-web-2026-10-06.md`) :
   changement d'année en 15-22 ms contre 1,9 s sous Streamlit (rerun + Folium), design system v2
   (ADR-0014) appliqué sans contournement CSS, chargement initial < 0,25 s.
2. Le prototype Tauri (`origin/poc/tauri`, rapport `reports/poc-tauri-2026-10-06.md`) : `.app` de
   4,85 Mo, `.dmg` de 3,2 Mo, ouverture → carte en 0,9-1,1 s, hors ligne fonctionnel (sauf fond IGN).
3. La vague B a chargé la France entière (48 scrutins sur 56 déclarés dans `elections`, niveau
   bureau de vote). Les deux prototypes ne portaient que sur les Hauts-de-France (3 782 communes,
   10 scrutins, 5,2 Mo de données) : leur modèle « tout précalculé, tout chargé » doit être revu.
4. La feuille de route (vagues A-D, `reports/synthese-brainstorm-fonctionnalites-2026-10-06.md`) se
   construit directement dans la nouvelle interface.

Contraintes : un seul développeur non professionnel qui supervise des agents ; application Mac non
signée (pas de compte Apple Developer, décision du 2026-10-06) ; disque interne presque plein ;
licences (code MIT, base ODbL, ADR-0013) ; garde-fous de neutralité.

## Mesures

Base `data/ministere.duckdb` ouverte en lecture seule le 2026-10-07 ; scripts jetables hors dépôt,
sorties dans `/Volumes/le gros stockage/outils/tmp/adr0015/`. JSON compact (`separators=(",", ":")`),
compression gzip niveau 6. Agrégation : participation (`resultats_participation`) + voix par bloc
(`v_resultats_candidats_avec_bloc`, 6 blocs + voix non classées), soit 12 entiers par ligne.

| Jeu | Découpage | Volume brut | gzip | Remarque |
|---|---|---|---|---|
| Base DuckDB complète | — | 1 294 Mo | — | référence |
| Communes × scrutin, par bloc | 48 fichiers (un par scrutin), colonnes alignées sur les codes | 79,8 Mo | 20,1 Mo | 1,7 Mo brut par scrutin ; 34 871 communes avec résultats |
| Idem, rangé par commune (fiche territoire) | 1 fichier par commune | 93 Mo | 30 Mo | 2,7 Ko par commune en moyenne |
| Idem, rangé par département | 102 fichiers | 93 Mo | ≈ 30 Mo | max 2,4 Mo brut (2,6 % du total), médiane 0,9 Mo |
| Bureaux de vote × scrutin, par bloc | 102 fichiers (par département) | 253 Mo | 67 Mo | max ≈ 7,3 Mo brut, médiane ≈ 2,2 Mo ; commune la plus lourde (Paris, 37 304 lignes) : 2,7 Mo / 0,7 Mo |
| Candidats × commune (noms, nuance, liste, voix) | — | 1 314 Mo | non mesuré | 13,7 M lignes (objets JSON) |
| Candidats × bureau de vote | — | 2 530 Mo | non mesuré | 26,5 M lignes |
| Parquet zstd, BV par bloc | 1 fichier | — | 38,5 Mo | format de l'option C |
| Parquet zstd, communes par bloc | 1 fichier | — | 23,2 Mo | |
| Parquet zstd, candidats × BV | 1 fichier | — | 79,2 Mo | détail complet |
| Contours des communes (simplifiés, ~1 m) | 1 fichier national | 41,3 Mo | 12,3 Mo | 34 877 communes ; trop lourd pour un chargement d'ouverture |

Temps : agrégation complète au bureau de vote en 9,2 s (DuckDB, Mac mini M4) ; l'export total est
une affaire de minutes, pas d'heures.

Autres mesures, utiles à la comparaison : moteur Python du sidecar (option D) — `pyarrow` 121 Mo,
`polars` 179 Mo, `duckdb` 38 Mo dans `.venv` (474 Mo au total) ; paquet npm `@duckdb/duckdb-wasm`
1.33 : 149 Mo décompressé, toutes variantes confondues (une seule variante WASM est chargée, de
l'ordre de 30-40 Mo non compressée ; non mesuré dans Tauri).

Estimation de l'application (option B, élections seules, JSON compressé dans le paquet) : contours
12 Mo + scrutins 20 Mo + fiches 30 Mo + bureaux de vote 67 Mo ≈ **130 Mo**, contre 3,2 Mo pour le
prototype HdF. Économie et Législatif ajoutent quelques Mo (tables < 2 M lignes, Économie limitée
aux HdF). Tauri compresse les ressources (brotli) : la taille réelle sera plutôt inférieure ; à
mesurer au lot A0.

Performance de rendu (rapport `reports/recherche-animation-performance-2026-10-07.md`, non mesuré
par cet ADR) : la maquette recolore la carte par une boucle `setFeatureState` (une instruction par
commune, thread principal) : 15-22 ms en Chromium et 29-58 ms en WebKit (Tauri) pour 3 782
communes, soit ~270-540 ms extrapolés en WebKit pour ~35 000 communes. Piste : blocs dominants de
tous les scrutins encodés dans des tuiles vectorielles PMTiles (une archive, lectures par plage),
changement d'année par un seul `setPaintProperty` ; résultats détaillés par scrutin décodés dans un
Web Worker. **Budget proposé** (à confirmer par le prototype) :

| Indicateur | Cible | Seuil d'échec |
|---|---|---|
| Ouverture de l'app → carte colorée (à froid, Mac mini M4) | < 1 s | 1,5 s |
| Changement d'année, France entière, WebKit | < 100 ms | 150 ms |
| JS initial (gzip) | < 450 Ko | 550 Ko |
| Données avant la 1re carte colorée (gzip) | < 1,5 Mo | 3 Mo |
| Mémoire après usage, France entière | < 600 Mo | 900 Mo |

## Options comparées

- **A — Statu quo** : Streamlit + installateur (v1.0.1, `deploy/install.sh`).
- **B — Web + Tauri, JSON précalculés** : export Python lecture seule → fichiers JSON découpés
  (par scrutin pour la carte, par département pour la fiche et le bureau de vote), chargés à la
  demande par l'interface ; aucune base dans l'application.
- **C — Web + Tauri, DuckDB-wasm** : l'interface interroge en SQL des fichiers Parquet embarqués.
- **D — Web + Tauri, sidecar Python** : Tauri lance un petit serveur local Python/DuckDB (base
  complète) ; l'interface l'appelle en HTTP sur `127.0.0.1`.

Variante écartée d'emblée : DuckDB natif dans le processus Rust de Tauri (crate `duckdb`). Elle
impose d'écrire et maintenir du Rust, hors compétence du mainteneur.

| Critère | A Streamlit | B JSON | C DuckDB-wasm | D sidecar Python |
|---|---|---|---|---|
| Volume France entière | base 1,3 Go, aucune limite | ≈ 130 Mo (agrégats par bloc jusqu'au BV) ; détail par candidat exclu | ≈ 60-140 Mo Parquet + moteur 30-40 Mo ; détail par candidat possible | base 1,3 Go + Python ≈ 0,5 Go |
| Hors ligne | oui | oui | oui | oui |
| Temps d'ouverture | serveur à lancer, 1-2 s par interaction | ≈ 1 s mesuré (HdF) ; fichiers de 1-2 Mo à la demande | + initialisation du moteur WASM et lecture Parquet (non mesuré, probablement 1-3 s) | + démarrage Python et DuckDB (plusieurs secondes) |
| Changement d'année, France entière | rerun ≈ 2 s, carte Folium recalculée | < 100 ms visé avec tuiles PMTiles (à prouver, lot A0) ; ~270-540 ms avec la boucle actuelle | même contrainte de rendu que B, plus la requête SQL | même contrainte de rendu que B, plus l'aller-retour HTTP |
| Taille de l'app | n/a (installateur + base téléchargée) | ≈ 130 Mo estimé | ≈ 100-180 Mo | ≈ 1,8 Go |
| Maintenance, un développeur | Python seul ; limite d'interactivité atteinte | Python (export) + TypeScript (affichage) ; aucune requête côté interface | SQL réécrit côté TypeScript, deux endroits où calculer | trois couches (Rust, Python packagé, TS) ; empaquetage Python fragile (PyInstaller, signatures) |
| Sécurité | port local 127.0.0.1 | aucun serveur, CSP stricte (POC Tauri) | aucun serveur ; WASM + workers à ouvrir dans la CSP | port local à protéger, processus à superviser |
| Réutilisation du Python | totale | ETL, vues, classements, `sources.py`, `_blocs_politiques.py` réutilisés par l'export | ETL réutilisé ; requêtes de `viz/` à réécrire | requêtes de `viz/` réutilisables derrière une API |
| Neutralité / traçabilité | inchangées | calculs en SQL à l'export, testés en pytest | calculs dans l'interface, tests à doubler | inchangées |

## Décision proposée

**Option B.** L'application Mac (Tauri v2, non signée) affiche des données précalculées par un
script Python d'export, en lecture seule sur la base DuckDB. Le rendu de la carte (point commun aux
options B, C et D) est traité à part : c'est le vrai verrou de la France entière.

1. **Toute agrégation est faite en SQL à l'export**, testée en pytest (somme des voix = exprimés,
   absence = `null` affiché « n.d. », jamais 0). L'interface ne calcule rien d'autre qu'un
   affichage ou une mise en forme.
2. **Découpage** : un fichier par scrutin pour les cartes nationales ; un fichier par département
   pour les fiches territoire et le détail par bureau de vote. Aucun fichier ne dépasse ≈ 8 Mo
   brut. Format : JSON compressé par défaut ; binaire compact (colonnes d'entiers) seulement si le
   prototype A0 montre que le JSON ne tient pas le budget.
3. **Carte** : contours en archive PMTiles portant, par commune, le bloc dominant de chaque scrutin ;
   changement de scrutin par une seule expression de style (`setPaintProperty`), sans boucle par
   commune ; décodage des résultats détaillés dans un Web Worker. **Conditionné au prototype A0** :
   s'il échoue au budget, repli sur des contours par département chargés au zoom (carte nationale
   au niveau département). Le tuilage ajoute un outil externe à l'ETL (tippecanoe, licence BSD-2,
   ou équivalent) : choix d'outil soumis avec le rapport du prototype.
4. **Contrat de données versionné** : `manifest.json` (version de schéma, date d'export, empreinte
   SHA256 de chaque fichier, sources et licences) lu au démarrage.
5. **Détail par candidat** (noms, listes) : hors vague A. Au premier besoin (fiche « élu et son
   élection », vague C), un ADR dédié choisira entre JSON par commune et DuckDB-wasm sur Parquet
   (79 Mo mesurés pour le détail complet au bureau de vote). C'est l'ajustement de l'orientation du
   2026-10-06 (« DuckDB embarqué pour le détail par bureau de vote ») : les mesures montrent que le
   détail **par bloc** au bureau de vote tient en JSON ; c'est le détail **par candidat** qui ne tient
   pas.
6. Le code web vit dans `main` sous `web/` (application) et `web/src-tauri/` (emballage) ; l'export
   sous `scripts/export_web.py` avec sa logique dans `src/ministere_de_l_info/export_web/`.

## Conséquences

### Streamlit pendant la transition
- Gelé : corrections de bugs seulement, aucune nouvelle fonctionnalité (la vague A n'est construite
  que dans `web/`). Il reste l'outil de contrôle des chiffres : chaque page portée est comparée à
  la page Streamlit équivalente (mêmes totaux).
- Retrait page par page à parité, puis suppression de `app.py`, `pages/`, `src/.../pages/`, des
  dépendances `streamlit`, `folium`, `streamlit-folium` et des tests `AppTest`, par une note
  d'exécution de cet ADR (décision structurante soumise à Mathias au moment du retrait).
- `viz/*_queries.py` : les requêtes utiles migrent vers l'export ; le reste disparaît avec Streamlit.

### Installateur et distribution
- `deploy/install.sh` / `update.sh` (v1.0.x) restent la voie Streamlit jusqu'au retrait ; ensuite
  remplacés par le `.dmg`. ADR-0012 (LaunchAgent) devient sans objet à ce moment-là.
- La release de la base (`db-*`, ODbL, SHA256) est conservée pour les réutilisateurs ; les JSON
  exportés sont une base dérivée, également sous ODbL, mention affichée dans l'application.
- Mise à jour des données : nouvelle version de l'application (voir Q4).
- Non signée : ouverture par clic droit › Ouvrir la première fois, documentée dans le guide.

### CI et tests
- CI : nouveau job `web` (Node LTS, `npm ci`, `tsc --noEmit`, `vitest run`, `vite build`,
  `npm audit --audit-level=high`, contrôle du budget de taille de `dist/`) ; actions et images épinglées par SHA (règle J4). La compilation
  Tauri reste locale (Rust, ≈ 2 min, 808 Mo de `target/` sur le disque externe), pas en CI.
- Tests Python : l'export est testé sur l'échantillon (`scripts/export_sample_db.py`) comme le
  reste ; invariants (alignement des codes, sommes, `null` ≠ 0, sources présentes).
- Tests TypeScript : `vitest` sur la logique pure (état d'URL, formatage, recherche) ; un test de
  fumée sur la page compilée. Pas de tests de bout en bout lourds tant que la parité n'est pas
  atteinte.
- Validation visuelle de Mathias obligatoire à chaque page portée (`npm run dev` ou `.app`).

### Positives
- Interactivité instantanée, design system v2 appliqué sans contournement, application autonome.
- Le cœur Python (ETL, classements, licences, tests) est conservé ; les calculs restent en SQL.
- Aucune surface réseau locale.

### Négatives
- Deux langages ; un export à maintenir à côté de l'ETL ; une étape de construction de plus.
- Taille de l'application multipliée par ≈ 40 par rapport au prototype (≈ 130 Mo).
- Toute nouvelle vue demande d'étendre l'export (pas de requête libre).
- Pendant la transition, deux interfaces coexistent (Streamlit gelé).

### Réversibilité
Bonne. L'export est un ajout ; Streamlit reste fonctionnel jusqu'à son retrait. Le passage de B à C
pour une partie des données ne change pas l'interface (même contrat de données en lecture).

## Plan de migration page par page

| Ordre | Page web | Contenu | Remplace | Vague |
|---|---|---|---|---|
| 0 | Prototype de performance | tuiles PMTiles France entière, changement d'année sans boucle, mesures WebKit | — (jalon, branche jetable) | A0 |
| 1 | Socle + Élections (carte nationale, tous scrutins) | navigation 5 entrées, carte par scrutin, légendes et sources | Élections Streamlit (partiel) | A1 |
| 2 | Fiche territoire commune | population, historique électoral par bloc et participation, BV, économie (HdF), élus | — (nouveau) | A3 |
| 3 | Recherche, Méthodologie, exports CSV | | renvois vers `docs/adr/` | A4-A6 |
| 4 | Élections complètes | législatives (circonscriptions), municipales, tableaux, détail BV | Élections Streamlit | après A |
| 5 | Géographie | 6 niveaux, population, évolutions (PuOr) | Géographie | après A |
| 6 | Économie | 4 onglets, classes fixes, nuage économie × élections | Économie | après A |
| 7 | Législatif | filtres, élus, activité, historique (sans « Top 20 » nominatif) | Législatif | après A |
| 8 | Accueil | tuiles, sources | Accueil | après A |
| 9 | Retrait de Streamlit | note d'exécution, suppression du code | — | à parité |

Effort estimé : vague A 16-25 jours agent (prototype A0 compris) (fiches `.claude/plans/2026-10-07-vague-a-*`), puis
portage des pages restantes 15-22 jours (rapport de la maquette, § 6).

## Questions fermées pour Mathias

- **Q1** — Adopter l'option B (JSON précalculés, aucun moteur de base dans l'application ; détail
  par candidat reporté à un ADR dédié) : oui / non (non = option C, DuckDB-wasm dès la vague A).
- **Q2** — Streamlit pendant la transition : (a) gelé, corrections de bugs seulement, retiré page par
  page à parité ; (b) maintenu en parallèle avec les nouvelles fonctionnalités.
- **Q3** — Carte France entière : (a) prototype A0 d'abord (tuiles PMTiles, changement d'année en
  une instruction, budget < 100 ms en WebKit) comme jalon bloquant avant le socle, avec l'ajout d'un
  outil de tuilage à l'ETL ; (b) directement des contours par département chargés au zoom (carte
  nationale au niveau département), sans prototype ni outil supplémentaire.
- **Q4** — Mise à jour des données : (a) nouvelle version de l'application (`.dmg`) à chaque
  mise à jour ; (b) paquet de données séparé téléchargé depuis une release GitHub (SHA256 vérifié).
- **Q5** — Architecture cible : (a) arm64 seul (Apple Silicon) ; (b) binaire universel (Intel
  + Apple Silicon, compilation deux fois plus longue).
