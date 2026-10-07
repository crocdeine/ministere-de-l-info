# Mission : vague A, lot 6 — exports CSV avec source, licence et date

**Agent** : developpeur-ui · **Branche** : feat/web-exports-csv
**Base** : origin/main (après A3) · **Complexité** : S-M (1-2 jours)
**Décision d'origine** : feuille de route, vague A ; ADR-0013 (licences et mentions)
**Dépendances** : A1, A3 (tableaux de la fiche), A5 (lien vers la méthode).

## Objectif
Chaque tableau affiché (carte par scrutin, fiche commune, bureaux de vote, recherche d'élus)
s'exporte en CSV ouvrable dans un tableur français, accompagné de sa source, de sa licence, de
la date des données et de la méthode, pour qu'une réutilisation reste traçable et conforme à l'ODbL.

## Hors périmètre
- Export Excel, PDF ou image ; export de la base entière (déjà en release `db-*`).

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Mentions | `src/ministere_de_l_info/sources.py:129` | `mention(cle)`, exportée dans le manifeste (A1) |
| Licences | `LICENSE-DONNEES.md`, ADR-0013 | base ODbL, sources sous leur licence |
| Absences | `viz/_display.py:43` `fmt_nd` | cellule vide (pas 0) et colonne documentée |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `web/src/export-csv.ts` (+ test) | créer | sérialisation sans dépendance : UTF-8 avec BOM, séparateur `;`, échappement RFC 4180 |
| composants tableau | modifier | bouton « Télécharger (CSV) » |
| `web/src-tauri/` | modifier si nécessaire | téléchargement dans l'app (lien `blob:` ou plugin `dialog`/`fs` minimal, CSP) |

## Tâches
### 1. Format
- **Action** : en-tête de commentaire (`# Source : …`, `# Licence : …`, `# Données du : …`,
  `# Export du : …`, `# Méthode : …`) puis tableau ; codes INSEE en texte ; décimales à virgule ;
  absences = cellule vide ; nom de fichier `ministere-info_{vue}_{identifiant}_{date}.csv`.
  Variante si les lignes `#` gênent les tableurs : fichier `…-LISEZMOI.txt` à côté (question fermée).
- **Valider** : `npx vitest run export-csv` (guillemets, `;` dans un nom, `01001` conservé).
### 2. Téléchargement dans Tauri
- **Action** : vérifier que le téléchargement fonctionne dans le `.app` (WebKit) ; sinon plugin
  officiel minimal, permission limitée au dossier Téléchargements.
- **Valider** : fichier ouvert dans Numbers et LibreOffice, accents corrects.

## Garde-fous de neutralité
Le CSV contient les mêmes colonnes et libellés neutres que l'écran ; la légende de classement du
scrutin (officielle ou reconstruction) figure dans l'en-tête.

## Contraintes du projet
Communes aux fiches.

## Validation finale
```bash
cd web && npx tsc --noEmit && npx vitest run && npm run build && npm audit --audit-level=high
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Téléchargement bloqué dans WebKit/Tauri | moyenne | plugin officiel, permission minimale |
| Codes INSEE convertis en nombres par le tableur | élevée | colonne texte documentée ; test d'ouverture manuel |

## Acceptation
- [ ] Tout tableau exportable, avec source, licence, dates, méthode
- [ ] Ouverture correcte dans un tableur français
- [ ] Rapport court

## Si l'option B n'est pas retenue
Option C : `COPY … TO` côté DuckDB-wasm possible, même en-tête. Option A : `st.download_button`.
