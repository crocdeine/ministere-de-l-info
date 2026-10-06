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

## 2026-10-05 — Reprise après la session Antigravity (Gemini 3.1 Pro)

- L'abonnement Claude ayant atteint sa limite, Mathias a poursuivi avec Antigravity (Gemini 3.1 Pro),
  omniroute n'ayant pas fonctionné.
- Cette session a nettoyé les worktrees d'agents, mis à jour roadmap/audit/journal et poussé la branche.
- **Correction (2026-10-05)** : elle avait marqué J2 « validé (relecture par un modèle puissant) ».
  En réalité, la relecture s'est limitée à une lecture partielle du diff, sans exécution des tests ni
  contrôle des données ; elle ne remplit pas l'exigence de relecture indépendante. Statut ramené à
  « relecture en cours » ; relecture complète relancée (agent verificateur-code, Claude Opus).
- Supprimés : `j2_diff.txt` (fichier temporaire non suivi), branches locales `worktree-agent-*`
  (déjà intégrées dans la branche de travail).
- Relecture indépendante de J2 (verificateur-code, Claude Opus) : **prête**, 0 bloquant, 0 important.
  10 mandats NI reclassés recoupés un à un avec la source : conformes ; aucun bloc modifié par le
  re-sourçage ; 637 tests. Points mineurs M1-M3 corrigés (absences en n.d. dans le détail par bureau
  et le bloc dominant, test du préfixe homonyme) : 639 tests, couverture 77,14 %.
- M4 assumé : 3 suppléantes de la XVe (démission le jour de l'entrée en fonction) restent « sans groupe ».

## 2026-10-06 — Décisions sur les non-inscrits, lancement de J3

- Mathias valide : nuance du titulaire pour les remplaçants, chargement de la source AMO de
  l'Assemblée nationale, maintien de Ménard et Dupont-Aignan en DTE (voir docs/orientations.md).
- Lancés en parallèle : ETL AMO (ingenieur-etl) et jalon J3 lisibilité (developpeur-ui).
- AMO (Assemblée nationale) chargé : 26 des 30 non-inscrits restants classés selon leur titulaire
  (GAU 16, DTE 4, CENT 4, EXD 2) ; 4 élus de partielles restent « Divers » (résultats des partielles
  non publiés en open data). Total NI : GAU 46, CENT 23, DTE 15, EXD 11, DIV 5. Copie de la base
  avant chargement : `data/ministere.duckdb.bak-avant-amo`.
- J3 livré (échelles fixes, % par défaut, palette sans rouge-vert, « Extrême droite » non tronqué),
  relu (verificateur-code, Opus : prêt) ; seuils arbitrés par Mathias (voir orientations).
- Corrigés par le directeur : sélecteur CSS de la métrique (ellipse persistante), format du tableau
  par commune (6 décimales), évolution de population absente affichée « +0,0 % ».
- Mesures : 650 tests réussis, 0 échec ; couverture 77,24 %.

## 2026-10-06 — Jalon J4 (hygiène et durcissement)

- Sauvegarde préalable : `2026-10-06_avant-j4-nettoyage.zip` (41 Mo, vérifiée).
- **Supprimés** : fichiers d'exploration à la racine (`1_insee.txt` à `5_data_gouv_pib.txt`, `insee_*.html`,
  `explore_*.py`, `scratch_fetch.py`, `analyze_senators.py`), `scripts/_explore_elections.py`,
  `scripts/covers/` (script d'un autre projet). Aucune référence dans le code.
- **Déplacé** : `ODSEN_GENERAL.csv` (Sénat, juin 2026, plus téléchargeable) → `data/exploration/`.
- **Supprimées** (décision Mathias) : 9 copies de la base (≈ 8 Go) ; base archivée avant
  (`2026-10-06_base-ministere.zip`, 603 Mo). Restent la base active et `bak-avant-amo`.
- **Supprimée** (décision Mathias) : tâche planifiée de sauvegarde du Mac, cassée depuis le 1er juin
  (ancien chemin, accès refusé par macOS) ; archivée dans le dossier de sauvegardes.
- `.gitignore` : les copies de base (`data/*.duckdb*`) n'étaient pas exclues ; corrigé.
- 21 rapports historiques ajoutés à git ; seuil de couverture CI 38 % → 60 %.
- Infra (ingenieur-infra) : port 8501 sur 127.0.0.1, SHA256 obligatoire au téléchargement de la base,
  actions GitHub épinglées par SHA, images par digest, empreinte de Tectonic vérifiée.
- Géographie (developpeur-ui) : requêtes en cache (rerun 2,49 s → 0,001 s), connexion DuckDB
  unique `open_ro`, plus de connexion permanente qui bloquait les rechargements.
- Mesures : 652 tests, 0 échec ; couverture 77,95 % ; tests shell 55/55.
