# Mission : vague A, lot 0 — prototype de performance de la carte France entière

**Agent** : developpeur-ui (+ ingenieur-etl pour le tuilage) · **Branche** : poc/carte-france-tuiles (jetable, jamais fusionnée)
**Base** : origin/main 3f81863 + `origin/poc/interface-web` · **Complexité** : M (2-4 jours)
**Décision d'origine** : ADR-0015 (Proposé), Q3 ; rapport `reports/recherche-animation-performance-2026-10-07.md` (P1, P2, P6, § 6)
**Dépendances** : ADR-0015 accepté avec Q3 = (a). **Bloque** : A1.

## Objectif
Prouver, mesures à l'appui, que la carte des ~35 000 communes change de scrutin en moins de 100 ms
dans WebKit (Tauri), en portant le bloc dominant de chaque scrutin dans des tuiles vectorielles
PMTiles et en changeant de scrutin par un seul `setPaintProperty`. Le résultat fixe le format des
données et le pipeline de tuilage du socle (A1).

## Hors périmètre
- Aucune fusion dans `main` ; aucun code de production ; aucune page autre que la carte.
- Aucune modification de la base, des classements ou des vues.
- Ni fiche territoire, ni recherche, ni design final.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Export lecture seule | `origin/poc/interface-web:scripts/export_web.py` | `open_ro`, agrégats en SQL, `null` = n.d. |
| Carte | `origin/poc/interface-web:web/src/Carte.tsx` | style initial sans dépendre du fond IGN (`style.load`) |
| Emballage | `origin/poc/tauri:web/src-tauri/tauri.conf.json` | CSP stricte, `data.geopf.fr` seul domaine externe |
| Mesures | `reports/poc-tauri-2026-10-06.md` § 2 | horodatage avant `open -n`, 3 lancements, médiane |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `scripts/export_tuiles.py` (prototype) | créer | communes + bloc dominant par scrutin → GeoJSON séquentiel → PMTiles |
| `web/src/Carte.tsx` | modifier | source PMTiles (`promoteId` = code INSEE), expression de style indexée par scrutin |
| `web/src/worker/` | créer | décodage des résultats détaillés (infobulle) hors thread principal |
| `reports/poc-carte-france-tuiles-2026-10-xx.md` | créer | mesures et recommandation |

## Tâches
### 1. Tuilage
- **Action** : exporter les 34 877 communes (`geometry_simplified_communal`) avec une propriété
  compacte : bloc dominant par scrutin (1 caractère par scrutin, ordre de `elections`), égalité
  codée distinctement (couleur neutre, décision du 2026-10-06), absence ≠ 0. Générer une archive
  PMTiles (tippecanoe BSD-2 ou `ogr2ogr` MVT ; comparer installation, licence, taille).
- **Valider** : taille de l'archive ; tuiles de la vue initiale (France, zoom 5) en Ko.
### 2. Changement de scrutin sans boucle
- **Action** : expression `match`/`slice` sur la propriété, un seul `setPaintProperty` par changement.
  Fondu de 220 ms (`fill-color-transition`) désactivable, 0 ms en `prefers-reduced-motion`.
- **Valider** : Performance API (`mark`/`measure`) clic → image suivante, 20 changements.
### 3. Mesures Chromium et Tauri (WebKit)
- **Action** : mesurer le budget de l'ADR-0015 (ouverture, changement d'année, JS initial, données
  avant 1re carte, mémoire après 50 changements) ; comparer à la boucle `setFeatureState`.
- **Valider** : tableau de mesures dans le rapport, 3 lancements à froid, médianes.
### 4. Format des résultats détaillés
- **Action** : comparer JSON gzip et colonnes d'entiers binaires pour un scrutin France entière
  (taille, temps de décodage dans le worker).
- **Valider** : recommandation chiffrée (JSON par défaut si l'écart n'est pas décisif).

## Contraintes du projet
- Base : copie dans `/Volumes/le gros stockage/outils/tmp/`, jamais la base réelle.
- Disque interne : caches (npm, cargo `target/`, tuiles) sur le disque externe.
- Commits tôt et souvent (WIP accepté) ; ne jamais pousser.
- Aucune décision structurante : choix de l'outil de tuilage et du format = questions fermées.
- Économie de jetons : skill `economie-tokens`.

## Validation finale
```bash
cd web && npm run build && npx tsc --noEmit && npm audit --audit-level=high
uv run ruff check . && uv run ruff format --check .
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Coût reporté dans le worker de tuiles (re-travail à chaque changement) | moyenne | mesurer ; repli `setFeatureState` limité aux communes visibles |
| Protocole PMTiles dans Tauri (lecture par plages, CSP) | moyenne | plugin `pmtiles` (~15 Ko) ; tester `asset://` et `fetch` local |
| Outil de tuilage absent de uv (binaire C++) | élevée | `brew` sur le disque externe, ou `ogr2ogr` ; question fermée |
| Budget non tenu | faible à moyenne | repli de l'ADR : contours par département chargés au zoom |

## Acceptation
- [ ] Budget de l'ADR-0015 mesuré en WebKit (tenu ou non, chiffres à l'appui)
- [ ] Recommandations : outil de tuilage, format des résultats, fondu oui/non
- [ ] Neutralité : légende des blocs par scrutin et source sous la carte ; aucun nom de candidat
- [ ] Questions fermées listées pour Mathias
- [ ] Rapport `reports/poc-carte-france-tuiles-…md` (résumé ≤ 10 lignes)
