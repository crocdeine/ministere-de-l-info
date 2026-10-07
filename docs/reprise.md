# Point de reprise — à lire en premier par toute nouvelle session

Dernière mise à jour : 2026-10-07 (branche `release/v1.0`), `main` à `6768623` (PR #1 à #7 fusionnées).
Lire ensuite : `docs/orientations.md`, `docs/journal.md` (dernières entrées), `docs/roadmap.md`.

## Où on en est

- Phase 0 et jalons J1 à J5 : terminés et fusionnés dans `main` (PR #1, 2026-10-06). Puis :
  design system v2 (PR #2, ADR-0014), petites corrections UI (#3), README refondu (#4),
  refus de la page HTML servie par data.senat.fr (#5), réflexe documentation dans CLAUDE.md
  et modèle de PR (#6), brainstorm fonctionnalités et décisions du 2026-10-06 (#7).
- Documentation de `docs/` revérifiée contre le code et la base le 2026-10-06/07 (branche
  `docs/mise-a-jour-generale`).
- Base publiée : `db-2026-10-04` ; la base locale contient en plus J2, AMO et nuances des
  non-inscrits (non publiés).
- Sauvegardes : le directeur en est garant (règles dans `../ministere-de-l-info-backups/BACKUPS.md`).
- Exécution sur le Mac : native recommandée (ADR-0012) mais non installée (reportée) ; Docker
  non maintenu activement.
- En attente de Mathias : contrôle visuel de J3 ; question Dependabot (oui / non).

## Version 1.0 (branche `release/v1.0`, 2026-10-07)

- Installateur en une commande (`install.sh`, `uninstall.sh`), version 1.0.0, `CHANGELOG.md`,
  brouillon `docs/release-notes-v1.0.md`. Scénario local vert (rapport
  `reports/release-v1-installateur-2026-10-07.md`, avec la liste de publication).
- Base `db-2026-10-07` (vague B) branchée (`DB_TAG`) ; test réel avec téléchargement GitHub vert
  (100 s, 1,9 Go). Reste : PR vers `main`, accord de Mathias pour le tag `v1.0.0`, test via la
  vraie commande `curl | bash` après le tag.

## Prochaines étapes, dans l'ordre

1. **Synthèse du brainstorm** (`reports/synthese-brainstorm-fonctionnalites-2026-10-06.md`) :
   décisions prises le 2026-10-06 (« oui à tout », 4 vagues A à D, six garde-fous) ;
   découper la vague A (socle) en tâches.
2. **Application Mac Tauri** : prototype en cours sur la branche `poc/tauri` (non signée, hors
   ligne ; rapport `reports/poc-tauri-2026-10-06.md` sur cette branche). Non fusionnée.
3. **Maquette web** : branche `poc/interface-web` (rapport `reports/poc-interface-web-2026-10-06.md`
   sur cette branche). Non fusionnée.
4. ADR de révision de l'ADR-0002 (Streamlit → interface web + Tauri) à rédiger et faire valider.
5. Note juridique CNCCFP à ajouter dans `docs/sources.md` avant intégration de la source (vague D).
6. Republication de la base quand les groupes du Sénat seront connus (voir ci-dessous) ;
   zip de la base avant tout rechargement.

## En attente d'un événement extérieur

- **Groupes du Sénat après le renouvellement du 27/09** : tâche planifiée quotidienne
  « veille-groupes-senat » (`scripts/veille_groupes_senat.py`), état non revérifié le 2026-10-07.
  Quand elle signale que tous les sénateurs ont un groupe : remettre le fichier d'octobre en
  cache (`data/raw/legislatif/senat-odsen-general.csv`, puis
  `load_legislatif.py --source senat --force`, `datan`, `overrides`, `nuances`), vérifier les
  WARNING « groupe non classé » (décision Mathias), republier la base (`scripts/publish_db.sh`,
  nouvelle release `db-AAAA-MM-JJ`, tag hors `v*`).
- Fichier Sénat d'octobre mis de côté : `data/raw/legislatif/senat-odsen-general-2026-10-04.csv`.

## Règles pour une session de relais (omniroute, Antigravity ou tout modèle non Claude)

- Autorisé : documentation, tests, nettoyage technique, mise à jour du journal.
- **Interdit** (mettre en attente) : tout classement politique, toute relecture de neutralité ou
  de conformité juridique, validation finale de données, publication, fusion dans `main`.
- Ne jamais envoyer `.env` ni aucun secret au modèle.
- Noter la bascule dans `docs/modeles.md` (journal des bascules).
- Ne jamais écrire « validé », « relu » ou « vérifié » sans avoir exécuté les commandes
  correspondantes (tests, requêtes) et cité leur résultat.
- Terminer en mettant à jour ce fichier : ce qui a été fait, ce qui reste.
