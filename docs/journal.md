# Journal du projet

Une entrée par session ou changement d'orientation : ce qui a été fait, supprimé, déplacé, et pourquoi.
L'historique antérieur au 2026-10-04 est dans `reports/` (voir `reports/README.md`).

## 2026-10-04 — Phase 0 (audit de l'existant)

- Nouvelle consigne de pilotage reçue (équipe d'agents, phases, sauvegardes, contraintes) : résumée dans
  `docs/orientations.md`.
- Sauvegarde initiale : `../ministere-de-l-info-backups/2026-10-04_phase0-initial.zip` (39,3 Mo, vérifiée).
- Outils vérifiés (agent-skills, ponytail, graphify, omniroute : tous déjà installés) → `docs/outils.md`.
- Graphe du code généré par graphify dans `graphify-out/` (exclu de git localement).
- Documents créés : `docs/outils.md`, `docs/equipe.md`, `docs/modeles.md`, `docs/orientations.md`,
  `docs/journal.md`, `docs/roadmap.md`, `docs/sources.md`, `docs/audit-2026-10-04.md`.
- Aucun code ni aucune donnée modifiés. Rien supprimé, rien déplacé (hormis la sortie graphify, générée
  dans `src/` par erreur puis déplacée à la racine).
- Écart signalé : la « première tâche » demandée (design system, `_theme.py`, `inject_css()`) est déjà
  réalisée depuis le 2026-08-19 (ADR-0009).
