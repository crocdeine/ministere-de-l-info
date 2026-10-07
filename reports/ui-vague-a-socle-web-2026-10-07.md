# Vague A, lot A1 — socle de l'application web et pipeline de données

Date : 2026-10-07 · Agent : developpeur-ui · Branche `feat/web-socle` (worktree, non poussée) · Fiche : `.claude/plans/2026-10-07-vague-a-1-socle-web-et-pipeline.plan.md`

## Résumé exécutif

- Livré : export France entière (`src/ministere_de_l_info/export_web/`, 75 s, 84 Mo, 254 fichiers, manifeste SHA256 versionné), application `web/` (navigation 5 entrées, carte Élections des 48 tours), job CI `web`, documentation.
- Budget ADR-0015 (WebKit Playwright, Mac mini M4 chargé, charge ≈ 3,9) : JS initial **378 Ko** gzip (cible 450, prototype 499) ; données avant la 1re carte **821 Ko** ; ouverture **401-684 ms** ; changement de tour **86-89 ms** (médiane, p90 96-105) ; mémoire 503-651 Mo (cible 600, seuil 900).
- Fondu croisé 220 ms entre deux couches à sources séparées : sans surcoût mesuré (recoloration d'une seule couche dans la même session : 88 ms) ; repli sans fondu au-delà de 100 ms ; aucun fondu avec `prefers-reduced-motion` (vérifié).
- Trois états vides distincts : n.d., non classé, hors périmètre ; égalité en blanc ; étiquette de méthode ; palette Papier hors carte.
- Vérifications : `pytest` export 7/7 (parité des totaux avec les vues Streamlit pour pres, legi, muni), `vitest` 8/8, `tsc`, `npm audit` 0, `ruff`, budget ; fumée WebKit sur l'échantillon.
- Tauri : voir § 6 (WKWebView non mesuré : à faire session ouverte).
- Décisions à soumettre : Q1 à Q5 (§ 8).

## 1. Commits

| Commit | Contenu |
|---|---|
| `154351f` | `feat(export)` : export, manifeste, états, tests ; import du prototype |
| `9787cb7` | `feat(ui)` : application, carte, fondu, worker, tokens Papier, mesures |
| `3a89692` | `ci(web)` : job CI, documentation (`docs/outils.md`, `architecture.md`, `deployment.md`, `web/README.md`, skill) |

## 2. Export et contrat de données

- `scripts/export_web.py` (CLI mince : `--db`, `--out`, `--departements`, `--tippecanoe`, `--sans-tuiles`) → `export_web/export.py`. Lecture seule (`read_only=True`), base réelle ouverte directement (aucune copie de 1,2 Go).
- Agrégats en SQL (`_sql_agregat`) : Σ inscrits, votants, exprimés ; voix par bloc et voix non classées (`NC`) ; `null` si aucune ligne de voix, 0 seulement pour un bloc absent d'une commune qui a voté. Participation = Σ votants / Σ inscrits (formule de `v_participation_commune_pres`). Part du bloc en tête calculée à l'export, `null` si égalité, non classé, exprimés nuls ou somme des voix > exprimés (scrutin plurinominal des petites communes).
- États (propriété `s` des tuiles, un caractère par tour) : `a`-`f` blocs, `=` égalité, `n` non classé (candidats ou listes sans bloc en tête, voix non classées sommées comme un bloc), `.` n.d. (ligne de participation sans voix utilisable, ou département sans aucun résultat pour ce tour), `x` hors périmètre (commune sans aucun résultat alors que son département en a : pas de second tour, municipales 2008 limitées aux communes publiées).
- Fichiers : `communes.pmtiles` (19,7 Mo), `communes.json.gz`, `scrutins/<id>.json.gz` (48 fichiers, 20,8 Mo), `departements/<dep>/{communes,bureaux}.json.gz` (43,6 Mo dont BV 28,7 Mo). Plus gros fichier brut : `departements/59/bureaux.json.gz`, 4,2 Mo (< 8 Mo). Gzip reproductible (`mtime=0`).
- `manifest.json` : schéma 1, date, licence ODbL de la base dérivée, sources (`sources.py`), scrutins (type, année, tour, libellé, `methode`, légende), 8 tours déclarés sans résultats (cantonales 2001-2011), `communes_sans_contour` = 0, empreintes. L'interface refuse un autre schéma (`verifierManifeste`).
- Ajout `methode_classement()` dans `_blocs_politiques.py` (même source que `legende_classement_blocs`, aucun classement modifié).
- Constats : municipales 2020/2026 1er tour, ≈ 31 600 communes « non classé » (petites communes sans nuance) ; 2008 : 2 548 communes seulement.

## 3. Application

- `App.tsx` : navigation 00-04 (hash `#/elections`), pages non portées avec renvoi vers Streamlit. `PageElections.tsx` : type, année, tour (présidentielle 2022 1er tour par défaut), carte, infobulle, légende (10 états), mention de rupture quand le type ou la grille change, source et licence.
- `Carte.tsx` : deux couches de remplissage, chacune sur sa source (mêmes tuiles) ; la couche cachée reçoit le nouveau tour (un `setPaintProperty`), puis fondu des opacités (`--duration-map-fade`). La seconde source est ajoutée après la première carte. Fin de recoloration détectée par `sourcedata` + rendu (sans attendre le fond IGN), `idle` en secours.
- `worker/details.ts` : JSON gzip (`DecompressionStream`), 4 tours en cache ; préchargé après la 1re carte.
- `maplibre.ts` : MapLibre chargé depuis ses fichiers ESM d'origine (`public/vendor/`, copiés par `vite.config.ts`) avec `modulepreload` ; archive lue en mémoire sous `tauri:`.
- Tokens : palette Papier et `--duration-map-fade` ajoutés à `tokens.css` / `tokens.json`. Constat : la coupure `prefers-reduced-motion` du skill couvrait déjà fast, base et slow (le rapport de recherche se trompait) ; le nouveau jeton y est ajouté.
- Observable Plot retiré des dépendances (inutilisé en A1, à réintroduire en A3).

## 4. Mesures (`web/perf/mesure.mjs`, WebKit 26.6 sans fenêtre, 1280×860, France, zoom ≈ 4,6)

| Budget ADR-0015 | Cible / seuil | Mesuré (3 lancements, 30 changements) | Verdict |
|---|---|---|---|
| Ouverture → carte colorée | < 1 s / 1,5 s | 401, 444, 684 ms (navigateur, hors démarrage de l'app) | tenu (WebKit) |
| Changement de tour | < 100 / 150 ms | médiane 86-89, p90 96-105, max 98-224 ms | tenu, marge faible |
| JS initial gzip | < 450 / 550 Ko | 378 Ko (fichiers uniques) ; 814 Ko transférés | tenu (voir limite 2) |
| Données avant 1re carte | < 1,5 / 3 Mo | 821 Ko (5 requêtes) | tenu |
| Mémoire | < 600 / 900 Mo | 503-651 Mo (`footprint`) | à la limite de la cible |

Machine partagée pendant les mesures (charge ≈ 3,9, autres agents) : le prototype A0 mesurait 62 ms ; dans cette session, la recoloration d'une seule couche sans fondu donne aussi 88 ms, donc l'écart vient de l'environnement, pas du fondu.

## 5. CI (job `web`, `.github/workflows/ci.yml`)

Actions par SHA (`setup-node` v7.0.0 `8207627…`) ; tippecanoe compilé au commit `68ab8dcc` (2.79.0) et mis en cache ; base échantillon reconstruite puis exportée ; `npm ci`, `tsc`, `vitest`, build, `perf/budget.mjs` (bloquant), `npm audit --audit-level=high`, Playwright WebKit (`--with-deps`), `mesure.mjs` (fumée : carte, légende, aucune erreur ; données ≤ 1,5 Mo ; temps non bloquants) avec et sans mouvement réduit ; résultats en artefact. Non exécutée sur GitHub (branche non poussée) : à vérifier au premier push.

## 6. Tauri

[À COMPLÉTER]

## 7. Limites

1. Mesures en WebKit Playwright, pas dans WKWebView (Tauri) ; ouverture mesurée depuis le document, sans le démarrage de l'app.
2. Le module partagé de MapLibre est redemandé par chaque worker (814 Ko transférés en local) ; le prototype avait le même schéma (worker empaqueté). Sans effet réseau dans Tauri (fichiers locaux).
3. Une seule vue mesurée (France, zoom ≈ 4,6). DROM hors du cadre initial (accessibles en déplaçant la carte).
4. « Hors périmètre » est défini par les données (aucune ligne alors que le département en a) : une commune absente pour une autre raison serait classée ainsi (0 commune de résultat sans contour constatée).
5. Données embarquées dans l'app (84 Mo) ; le paquet de données séparé (ADR-0015 Q4) n'est pas réalisé.
6. Étiquette de méthode : infobulle seulement ; panneau Méthodologie en A5. Pas de pictogramme de module (ADR-0016 § 3).

## 8. Décisions à soumettre (questions fermées)

- **Q1** Définition de « hors périmètre » (commune sans résultat dans un département couvert) : (a) retenir ; (b) n.d. pour toute commune sans résultat au 1er tour, hors périmètre seulement aux seconds tours.
- **Q2** Scrutin affiché à l'ouverture : (a) présidentielle la plus récente, 1er tour (fait) ; (b) dernier tour chargé (municipales 2026, 2nd tour).
- **Q3** Identifiant de bundle et nom : (a) `fr.ministere-info.desktop`, « Ministère de l'Info » (prototype, conservés) ; (b) autre.
- **Q4** Données dans l'app pour A1 : (a) embarquées (84 Mo) jusqu'au paquet séparé ; (b) paquet séparé dès maintenant.
- **Q5** Bureaux de vote (28,7 Mo) dans l'app avant A3 : (a) oui ; (b) non, export seulement.
