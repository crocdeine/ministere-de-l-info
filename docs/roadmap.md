# Feuille de route

Mise à jour : 2026-10-07. Détail des constats : `docs/audit-2026-10-04.md`.

| Jalon | Objet | État |
|---|---|---|
| Phase 0 | Audit de l'existant, outils, sauvegarde, documents de suivi | ✅ validé le 2026-10-04 |
| J1 | Conformité : licences, légendes des blocs, sources affichées, détection de secrets | ✅ fait le 2026-10-04 — base publiée (`db-2026-10-04`, ODbL) |
| J2 | Exactitude : groupes sénatoriaux, non-inscrits, valeurs manquantes, sources des classements (dont 23 codes municipaux 2020/2026 à rattacher ligne à ligne à leur circulaire) | ✅ fait et relu le 2026-10-05 (reports/synthese-j2-2026-10-05.md ; 3 questions à Mathias) |
| J3 | Lisibilité honnête : échelles, municipales en %, palette accessible, indicateur « Bloc majoritaire » tronqué (titres neutres : faits en J1) | ✅ fait et relu le 2026-10-06 — contrôle visuel de Mathias attendu |
| J4 | Hygiène et durcissement : rangement, code mort, cache, infra | ✅ fait le 2026-10-06 (reports/synthese-j4-2026-10-06.md) |
| J5 | Fusion dans `main` | ✅ fait le 2026-10-06 (PR #1, puis design system v2 PR #2) |

Après J5 (état de `main` au 2026-10-07) :

| PR | Objet | État |
|---|---|---|
| #2 | Design system v2 « direction éditoriale » (ADR-0014) | ✅ fusionnée le 2026-10-06 |
| #3 | Petites corrections relevées par la revue fonctionnelle | ✅ fusionnée |
| #4 | README refondu, zone « À propos » GitHub (appliquée) | ✅ fusionnée |
| #5 | Sénat : refus de la page HTML servie à la place d'ODSEN_GENERAL | ✅ fusionnée |
| #6 | Réflexe documentation (CLAUDE.md, modèle de PR) | ✅ fusionnée |
| #7 | Brainstorm fonctionnalités et sources, décisions du 2026-10-06 | ✅ fusionnée |

## Suite (décisions du 2026-10-06, `docs/orientations.md`)

- **Cible de production** : interface web emballée en application Mac (Tauri), non signée,
  public très restreint. Maquette web : branche `poc/interface-web` ; application Mac :
  branche `poc/tauri`. Aucune des deux n'est dans `main`. ADR de révision de l'ADR-0002 à
  rédiger.
- **Feuille de route fonctionnelle en 4 vagues** (`reports/synthese-brainstorm-fonctionnalites-2026-10-06.md`),
  construites dans la nouvelle interface :
  - A — socle : fiche territoire, URL partageables, recherche, page Méthodologie, exports ;
  - B — données : élections France entière, européennes, régionales, départementales,
    candidatures, Filosofi officiel INSEE ;
  - C — analyses : abstention, évolutions, comparaisons, triangulaires, fiche élu, parité ;
  - D — Parlement et argent public : votes nominatifs AN puis Sénat, CNCCFP, OFGL.
- Réduction des erreurs pyright : faite (0 erreur, job bloquant depuis le 2026-10-06).
