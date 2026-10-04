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

## 2026-10-04 — Validation de l'audit, jalon J1 (conformité)

- Mathias valide les 5 recommandations de l'audit : base sous ODbL, code sous MIT, retrait de
  `date_naissance`, non-inscrits classés selon leur nuance préfectorale (J2), titres neutres.
- Fait (ADR-0013) : `LICENSE` (MIT), `LICENSE-DONNEES.md` (ODbL + attributions) ; registre
  `sources.py` et tableau « Sources, licences et dates » sur l'Accueil ; légende des blocs par
  scrutin (« grille officielle » seulement pour les municipales 2020 et 2026) ; mentions de
  licence dans les légendes Économie ; circonscriptions attribuées à leur auteur réel ;
  onglet « Désindustrialisation » renommé « Emploi industriel et accès aux médecins », questions
  reformulées sans nommer de parti ; gitleaks + detect-private-key en pre-commit.
- Corrigé au passage : fond de carte CARTO (clé désormais exigée, filigrane « API KEY
  REQUIRED ») remplacé par le Plan IGN atténué.
- **Supprimé** : `etl/loaders/legislatif_clair.py`, `etl/loaders/legislatif_nosdeputes.py` (code
  mort, sources abandonnées par l'ADR-0007, aucun import) ; colonne `leg_elus.date_naissance`
  (schéma, loaders, échantillon de test, base locale). Sauvegarde préalable :
  `2026-10-04_phase0-initial.zip`.
- Scan gitleaks de l'historique : 1 faux positif (exemple dans une skill tierce). La clé GitHub
  de `.env` n'a jamais été commitée.
- Mesures : 570 tests réussis, 1 échec préexistant (mandats sénatoriaux sans bloc, J2) ;
  couverture 75,91 % (référence 75,15 %) ; sans base (conditions CI) : 215 réussis, 0 échec.
- Captures avant/après : `docs/captures/j1/`.

## 2026-10-04 — Envoi de la branche et publication de la base (accord de Mathias)

- La branche distante contenait 14 commits du 2026-09-25 absents de la copie locale : mes
  2 commits ont été rejoués par-dessus (rebase, 3 conflits d'imports résolus), sans écrasement.
  Branche de secours locale : `backup/avant-rebase-j1`. **L'audit du matin portait donc sur
  une version locale en retard** ; les constats restent valables, plusieurs points du Sénat et
  des nuances 2008 étaient déjà corrigés dans ces commits.
- Étape 4 bis de `reports/a-faire-sur-le-mac.md` appliquée (copie `data/ministere.duckdb.bak-2026-10-04`) :
  229 nuances, Sénat d'avant 2002 écarté, RP 2015/2016 rechargé, échantillon régénéré.
- Sénat renouvelé le 27/09 : le fichier officiel du 04/10 laisse 179 sénateurs actifs sans groupe.
  Décision Mathias : publier avec le Sénat d'avant le renouvellement et surveiller. État du jour
  conservé dans `data/ministere.duckdb.senat-2026-10-04-sans-groupes` ; veille quotidienne programmée.
- Test `test_economie_secret_statistique` réécrit : il supposait l'existence de communes sous
  secret, ce qui n'était vrai qu'à cause des faux positifs 2015/2016 corrigés le 25/09.
- Publication : release `db-2026-10-04` (ODbL, sources, limites connues), non marquée « latest »,
  tag hors motif `v*` (pas d'image Docker). Empreinte vérifiée en ligne. CI verte sur `3b669aa`.
- Compatibilité : le code v0.5 lit la nouvelle base (375 tests réussis ; 6 échecs de comptage
  attendus après les reclassements validés).

## 2026-10-04 — Jalon J2 (exactitude des données) validé

- J2 a été développé et validé (relecture de code par un modèle puissant).
- Modifications poussées sur la branche `claude/exciting-dirac-8mogwe`.
- Les CI sont vertes (run de `8d9cf6cf5a03c5e29772a939cc72525a076eae73` en succès).
- Le journal, la roadmap et l'audit ont été mis à jour pour acter la fin de J2.
