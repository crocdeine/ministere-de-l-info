# Mission : vague A, lot 1 — socle de l'application web dans `main` et pipeline de données

**Agent** : developpeur-ui + ingenieur-etl (export) + ingenieur-infra (CI, Tauri) · **Branche** : feat/web-socle
**Base** : origin/main (sha au lancement) · **Complexité** : L (4-6 jours)
**Décision d'origine** : ADR-0015 (Proposé) ; orientations du 2026-10-06 (cible option 2)
**Dépendances** : ADR-0015 accepté ; A0 terminé (format des données et outil de tuilage décidés).
**Débloque** : A2, A3, A5.

## Objectif
Faire entrer dans `main` l'application web (Vite + React + TypeScript, MapLibre, Observable Plot)
et son emballage Tauri, avec un export Python qui produit des données précalculées France entière
et un contrat de données versionné. Premier écran : la carte Élections, tous scrutins chargés.

## Hors périmètre
- Fiche territoire, recherche, URL d'état, Méthodologie, CSV (lots A2-A6).
- Toute modification de Streamlit (gelé, ADR-0015) sauf bug avéré.
- Détail par candidat ; DuckDB-wasm ; signature Apple ; mise à jour automatique.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Export | `origin/poc/interface-web:scripts/export_web.py` | `open_ro`, SQL, JSON compact, `null` ≠ 0 |
| Tests d'export | `origin/poc/interface-web:tests/test_export_web.py` | invariants sur la base échantillon, marqueur `spatial` |
| Couleurs, légendes | `src/ministere_de_l_info/_blocs_politiques.py:29,50` | `couleurs_traits`, `legende_classement_blocs` |
| Sources | `src/ministere_de_l_info/sources.py:129` | `mention(cle)` sous chaque visualisation |
| Lecture seule | `src/ministere_de_l_info/viz/_queries.py:28` | `open_ro(db_path)` |
| n.d. | `src/ministere_de_l_info/viz/_display.py:27` | `COULEUR_ND` |
| Design | skill `design-system-mi`, ADR-0014 | tokens, capitales 900, filets 1 px |
| Tauri | `origin/poc/tauri:web/src-tauri/` | crate minimal sans plugin, CSP |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `src/ministere_de_l_info/export_web/` | créer | logique d'export (agrégats, découpage, manifeste), typée et testée |
| `scripts/export_web.py` | créer | CLI mince (`--db`, `--out`, `--departements` pour l'échantillon) |
| `web/` | créer depuis `poc/interface-web` | application ; navigation 5 entrées (pages non portées : lien « disponible dans la version Streamlit ») |
| `web/src-tauri/` | créer depuis `poc/tauri` | emballage ; identifiant de bundle selon décision |
| `.github/workflows/ci.yml` | modifier | job `web` : `npm ci`, `tsc`, `vitest run`, `vite build`, `npm audit`, budget de taille ; actions par SHA |
| `tests/test_export_web.py` | créer | invariants de l'export |
| `.gitignore` | modifier | `web/node_modules/`, `web/dist/`, `web/public/data/`, `web/src-tauri/target/` |
| `docs/architecture.md`, `web/README.md`, `docs/deployment.md` | modifier | nouvelle couche, commandes, distribution `.dmg` |

## Tâches
### 1. Contrat de données
- **Action** : `manifest.json` = version de schéma, date d'export, SHA256 et taille de chaque
  fichier, sources et licences (registre `sources.py`), mention ODbL de la base dérivée ; un type
  TypeScript unique le décrit ; l'interface refuse une version de schéma inconnue (message clair).
- **Valider** : `uv run pytest tests/test_export_web.py -q`
### 2. Export France entière
- **Action** : par scrutin (carte) ; par département (communes et bureaux de vote, tous scrutins) ;
  tuiles selon A0 ; méta (blocs, couleurs, légendes par scrutin, écarts de chargement).
  Agrégats en SQL ; participation = Σ votants / Σ inscrits (même formule que Streamlit).
- **Valider** : totaux nationaux d'un scrutin = page Streamlit ; aucun fichier > 8 Mo brut ; durée d'export journalisée (`logging`).
### 3. Application et carte
- **Action** : reprendre la maquette, carte nationale tous scrutins (type, année, tour), légende
  « grille officielle » ou « reconstruction » selon `legende_classement_blocs`, égalité en couleur neutre.
- **Valider** : `cd web && npm run build && npx vitest run`
### 4. CI et Tauri
- **Action** : job `web` ; `npm run tauri:build` local (cargo sur le disque externe) ; mesure du budget.
- **Valider** : CI verte sur la branche ; `.app` ouvert, budget ADR-0015 relevé dans le rapport.

## Garde-fous de neutralité
Méthode et source sous chaque visualisation (garde-fou 1) ; rupture de grille signalée en légende
quand le type de scrutin change (2) ; vocabulaire neutre, libellés de blocs uniquement (6).

## Contraintes du projet
- Base : copie dans `/Volumes/le gros stockage/outils/tmp/`, jamais la base réelle.
- Disque interne : caches npm/cargo/uv sur le disque externe.
- Commits tôt et souvent ; ne jamais pousser.
- Aucune décision structurante : identifiant de bundle, nom de l'app = questions fermées.
- Réflexe documentation ; économie de jetons.

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check .
uvx pyright@1.1.408
uv run pytest -m "not slow and not network"
cd web && npx tsc --noEmit && npx vitest run && npm run build && npm audit --audit-level=high
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Écart de chiffres avec Streamlit | moyenne | test de parité sur 3 scrutins (pres, legi, muni) |
| Taille de l'app (≈ 130 Mo estimés) | moyenne | mesurer ; BV en option si dérive |
| Temps de compilation Tauri en CI | élevée | build Tauri local uniquement |

## Acceptation
- [ ] `main` contient `web/`, l'export, les tests, le job CI ; Streamlit inchangé
- [ ] Budget de performance de l'ADR-0015 tenu (ou écart documenté)
- [ ] Validation visuelle de Mathias (`.app`)
- [ ] Documentation à jour ; questions fermées listées
- [ ] Rapport `reports/vague-a-socle-…md` (résumé ≤ 10 lignes)

## Si l'option B n'est pas retenue
Option C (DuckDB-wasm) : l'export produit des Parquet (≈ 60 Mo mesurés pour les agrégats par bloc)
au lieu de JSON ; ajouter `@duckdb/duckdb-wasm`, ouvrir `wasm-unsafe-eval` dans la CSP ; les
requêtes passent en SQL côté TypeScript (tests doublés). Option A (statu quo) : fiche sans objet.
