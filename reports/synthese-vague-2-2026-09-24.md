# Synthèse — Vague 2 d'agents (2026-09-24)

**Directeur** : Claude Code (session cloud) — **Décideur** : Mathias
**Branche** : `claude/exciting-dirac-8mogwe` (non fusionnée dans `main`)

## Résumé exécutif

- Les 8 lots de décisions de la vague 1 sont appliqués (sauf lot 2, en attente de la vérification Mac).
- 7 agents livrés, tout est fusionné sur la branche : 185 tests réussis, 0 échec (sans base ni réseau), CI verte sur les commits vérifiés.
- Nouveaux ADR : 0010 (révision des nuances), 0011 (Législatif par législature), 0012 (exécution native Mac).
- La liste `reports/a-faire-sur-le-mac.md` est complète : étapes 0 à 5 prêtes, 6 après les sénatoriales, 7 après fusion dans `main`.
- Restent : 7 lots de décisions secondaires (§3), aucune urgente, et la fusion dans `main` (§4).

## 1. Livrables

| Agent | Lot | Livrable | Vérification directeur |
|---|---|---|---|
| Classements électoraux | 1, 3, 5 | 18 reclassements, codes officiels 2020/2026 complétés, ADR-0010, `docs/schema-elections.md` à jour | Tests nuances verts ; CLAUDE.md gotcha 11 corrigé |
| Législatif | 4 | `leg_groupes_blocs` (groupe, législature), `leg_mandats`, migration 0008, groupes non classés signalés (plus de DIV silencieux), fiche député, ADR-0011 | 56 tests en mémoire verts |
| Qualité | 7 | `config.py` (`MINISTERE_DB_PATH`, 15 chemins en dur supprimés), échantillon Parquet (script), marqueur `network`, CI sur `claude/**` + pyright non bloquant | Suite verte ; CI verte (runs 36045104612, 36045445925) |
| Mac natif | 6 | `deploy/native/*` (LaunchAgent, 127.0.0.1, port 8502), sauvegarde corrigée (bonne base, vérification, disque externe), bascule en 8 étapes, ADR-0012 | 105 + 46 + 51 tests shell verts |
| Interface | 8 | 11 quick wins : contraste WCAG, message « données indisponibles », participation pondérée, onglets paresseux, tableau Géographie complet, croisement éco T1, libellés | 26 tests verts |
| Tokens | — | Contexte fixe 20,5 → 18,6 Ko ; 4 agents en `sonnet` ; skill `economie-tokens` ; index `reports/README.md` ; proposition de CLAUDE.md allégé (−66 %) | Permissions ajoutées relues : tests et lint uniquement |
| Catalogue de sources | — | `reports/catalogue-sources-2026-09-24.md`, 10 sources prioritaires (statut « déclaré », à explorer sur le Mac) | — |

## 2. Cas tranchés par interprétation (à confirmer si désaccord)

- **CPNT 2002/2007** maintenu **DIV** (la grille 2020 le range DVD à cause de son alliance avec LR après 2010).
- **ECO 2022** maintenu **GAU** (fragile : les candidats EELV étaient nuancés NUP) — point ouvert ADR-0010.
- **LFI-NFP (XVIIe)** = **GAU** (grille 2023 en vigueur à l'élection de 2024).
- **Les Indépendants (Sénat)** = **CENT** (grilles 2020 et 2023 concordantes).

## 3. Décisions secondaires pour Mathias — 7 lots

| Lot | Sujet | Recommandation du directeur |
|---|---|---|
| **A** | **Législatif** : UC au Sénat CENT (en attendant une source datée) ; EDS (XVe) → CENT ; RDSE maintenu DIV ; instruire le chargement des sources officielles datées AN (AMO) et Sénat pour un vrai historique par législature | Oui à tout |
| **B** | **Interface** : taux RSA pour 1 000 habitants (population légale la plus proche) ; carte municipale : bloc dominant calculé parmi les seules listes nuancées ; 1er tour par défaut dans le croisement | Oui à tout |
| **C** | **Qualité** : la CI doit échouer si l'extension spatial ne s'installe pas ; job hebdomadaire des tests réseau ; garder pyright | Oui, oui, pyright |
| **D** | **Mac** : destination des sauvegardes ; avenir de l'image Docker publique après la transition ; job CI macOS | Disque externe ; garder l'image pour la distribution tant que install.sh existe ; pas de job macOS pour l'instant |
| **E** | **Outillage** : supprimer les skills tiers `canvas-design` (5,5 Mo), `frontend-design`, `skill-creator` ; appliquer le CLAUDE.md allégé (−66 % de contexte à chaque échange) après correction du gotcha « connexion DuckDB → cache_resource » qui contredit le code | Oui (le directeur relira le CLAUDE.md allégé ligne à ligne avant application) |
| **F** | **Sources** : CNCCFP (comptes de campagne) autorisée ; remplacer les circonscriptions non officielles par le jeu Etalab ; délinquance SSMSI au niveau commune ; licences ODbL au cas par cas avec ADR ; première source Économie : IRCOM | Oui ; oui après comparaison ; commune ; cas par cas ; IRCOM (continuité de série) |
| **G** | **Fusion dans `main`** par une PR (règle CLAUDE.md : squash-merge) après les étapes 2-3 du Mac | Oui — ouvrir la PR maintenant, fusionner après ton contrôle visuel |

## 4. Suite proposée (vague 3)

1. Après ton retour de l'étape 1 (Mac) : appliquer le lot 2 (codes 2008).
2. Fondations UX validées (lot 8) : URL partageables → page Méthodologie / glossaire → fiche commune.
3. Pyright : réduire les 178 erreurs (111 viennent d'un seul motif).
4. Sources : exploration sur le Mac des sources validées au lot F.
