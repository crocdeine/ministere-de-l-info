# Index des rapports

Point d'entrée unique de `reports/`. Lire cet index, puis le **résumé exécutif** en tête du
rapport utile (`head -n 20 reports/<fichier>.md`) ; ne lire le détail que pour la section utile.

## Convention (à partir du 2026-09-24)

1. **Nom** : `<type>-<sujet>-YYYY-MM-DD.md` (types : `session`, `synthese`, `audit`,
   `verification`, `recherche`, `etl`, `ui`, `infra`, `documentation`, `restructuration`,
   `outillage-claude`, `rd`). Les récapitulatifs de phase gardent
   `session-YYYY-MM-DD_<phase>-recap.md`.
2. **En-tête** : titre, date, agent, périmètre, puis un bloc **Résumé exécutif** de
   **10 lignes au plus** : constat principal, livrables (branche, commits), vérifications,
   décisions attendues de Mathias (questions fermées), suite proposée.
3. **Corps** : détail, preuves (`fichier:ligne`, commandes et résultats), limites.
4. **Index** : ajouter une ligne dans le tableau ci-dessous (le plus récent en haut de
   sa section). Un rapport remplacé est marqué « remplacé par … », jamais supprimé.

Les rapports antérieurs à cette convention n'ont pas de résumé exécutif : lire leur
sommaire (`grep -n '^## ' <fichier>`) avant d'ouvrir une section.

## Suivi courant

| Fichier | Objet | Taille |
|---|---|---|
| [a-faire-sur-le-mac.md](a-faire-sur-le-mac.md) | Liste tenue à jour des tâches à exécuter sur le Mac (base, réseau ministère) | 3 Ko |
| [synthese-vague-2-2026-09-24.md](synthese-vague-2-2026-09-24.md) | Synthèse de la vague 2 : lots appliqués, décisions secondaires A-G | 5 Ko |
| [synthese-vague-1-2026-09-24.md](synthese-vague-1-2026-09-24.md) | Synthèse de la vague 1 d'agents, décisions regroupées en lots | 8 Ko |
| [session-2026-09-24_etat-des-lieux.md](session-2026-09-24_etat-des-lieux.md) | État des lieux complet du projet (dette, écarts doc ↔ code) | 14 Ko |

## Vague d'agents du 2026-09-24

| Fichier | Agent | Objet | Taille |
|---|---|---|---|
| [optimisation-tokens-2026-09-24.md](optimisation-tokens-2026-09-24.md) | outilleur-claude | Réduction de la consommation de tokens (skills, agents, CLAUDE.md) | 12 Ko |
| [claude-md-allege-propose.md](claude-md-allege-propose.md) | outilleur-claude | Proposition de CLAUDE.md allégé, diff commenté (non appliquée) | 13 Ko |
| [outillage-claude-2026-09-24.md](outillage-claude-2026-09-24.md) | outilleur-claude | Agents, skills mis à jour, hook SessionStart cloud | 10 Ko |
| [audit-code-2026-09-24.md](audit-code-2026-09-24.md) | vérification du code | Audit de correction du code (src, pages, scripts, deploy, tests) | 37 Ko |
| [verification-nuances-2026-09-24.md](verification-nuances-2026-09-24.md) | recherche de données | Classements nuances → blocs, dossier pour décision | 31 Ko |
| [catalogue-sources-2026-09-24.md](catalogue-sources-2026-09-24.md) | chercheur-donnees | Catalogue des sources fiables hors data.gouv/INSEE | 47 Ko |
| [infra-2026-09-24.md](infra-2026-09-24.md) | ingenieur-infra | Docker, CI, publication de la base | 22 Ko |
| [ux-2026-09-24.md](ux-2026-09-24.md) | expérience utilisateur (lecture seule) | Audit d'expérience utilisateur | 33 Ko |
| [rd-feuille-de-route-2026-09-24.md](rd-feuille-de-route-2026-09-24.md) | R&D | Veille technique, pistes de feuille de route | 48 Ko |
| [rd-execution-mac-2026-09-24.md](rd-execution-mac-2026-09-24.md) | R&D | Mode d'exécution de l'application sur Mac (Docker vs natif) | 20 Ko |

## Récapitulatifs de phase (historique)

| Fichier | Objet |
|---|---|
| [session-2026-08-19_design-system-cloture.md](session-2026-08-19_design-system-cloture.md) | Clôture du chantier design system et UI/UX |
| [session-2026-06-22_phase-f-cloture.md](session-2026-06-22_phase-f-cloture.md) | Clôture Phase F — module Législatif |
| [session-2026-06-17_phase-eplus-plus.md](session-2026-06-17_phase-eplus-plus.md) | Phase E++ — contexte macro Eurostat |
| [session-2026-06-14_phase-eplus.md](session-2026-06-14_phase-eplus.md) | Phase E+ — enrichissement Économie (CNAF, DREES, URSSAF) |
| [session-2026-06-12_phase-e-cloture.md](session-2026-06-12_phase-e-cloture.md) | Clôture Phase E — module Économie |
| [session-2026-06-10_phase-d-clôture.md](session-2026-06-10_phase-d-clôture.md) | Clôture Phase D — module Élections complet |
| [session-2026-06-01_phase-c-recap.md](session-2026-06-01_phase-c-recap.md) | Phase C — présidentielles |
| [session-2026-05-27_phase-b-recap.md](session-2026-05-27_phase-b-recap.md) | Phase B — conteneurisation et déploiement |
| [session-2026-05-27_phase-a-recap.md](session-2026-05-27_phase-a-recap.md) | Phase A — qualité du module Géographie |
| [session-2026-05-21_recap.md](session-2026-05-21_recap.md) | Bouclage du module Géographie |
| [session-2026-05-18_recap.md](session-2026-05-18_recap.md) | Session 2026-05-18/19 |

## Documents de travail thématiques

| Fichier | Objet |
|---|---|
| [mapping-nuances-legislatives-validated.md](mapping-nuances-legislatives-validated.md) | Classement nuance × année → bloc, législatives (VALIDÉ 2026-06-01) |
| [mapping-nuances-municipales-validated.md](mapping-nuances-municipales-validated.md) | Classement municipales (VALIDÉ 2026-06-09) |
| [mapping-nuances-municipales-proposed.md](mapping-nuances-municipales-proposed.md) | Proposition municipales (remplacé par la version validée) |
| [exploration-elections-legislatives.md](exploration-elections-legislatives.md) | Exploration des données législatives (Phase D1.1) |
| [brainstorm-ui-ux-design-system.md](brainstorm-ui-ux-design-system.md) | Brainstorm UI/UX après intégration du design system |
| [prompt-gemini-ui-ux-optimisation.md](prompt-gemini-ui-ux-optimisation.md) | Prompt externe (Gemini) d'optimisation UI/UX |
| [research-streamlit-css-selectors.md](research-streamlit-css-selectors.md) | Sélecteurs CSS de Streamlit 1.57 |
| [etl_health_report.md](etl_health_report.md) | Rapport d'intégrité ETL (ancien) |
| [cleanup_report.md](cleanup_report.md) | Rapport de nettoyage (ancien) |

Dossiers : `templates/` (modèles, vide à ce jour), `output/` (sorties générées, vide).
