# Point de reprise — à lire en premier par toute nouvelle session

Dernière mise à jour : 2026-10-06 (fin J4), branche `claude/exciting-dirac-8mogwe`.
Lire ensuite : `docs/orientations.md`, `docs/journal.md` (dernières entrées), `docs/roadmap.md`.

## Où on en est

- Phase 0, J1, J2, J3, J4 : terminés (2026-10-06). Base publiée : `db-2026-10-04` ; la base locale
  contient en plus J2, AMO et nuances des non-inscrits (non publiés).
- Sauvegardes : le directeur en est garant (règles dans `../ministere-de-l-info-backups/BACKUPS.md`).
- En attente de Mathias : contrôle visuel de J3 ; question Dependabot (oui / non).

## Prochaines étapes, dans l'ordre

1. J5 : fusion de `claude/exciting-dirac-8mogwe` dans `main` par PR squash (accord de Mathias),
   CI verte sur la PR, puis mise à jour de CLAUDE.md (état des modules, dernier rapport).
2. Republication de la base quand les groupes du Sénat seront connus (voir ci-dessous) ;
   zip de la base avant tout rechargement.

## En attente d'un événement extérieur

- **Groupes du Sénat après le renouvellement du 27/09** : tâche planifiée quotidienne
  « veille-groupes-senat » (`scripts/veille_groupes_senat.py`). Quand elle signale que tous les
  sénateurs ont un groupe : remettre le fichier d'octobre en cache
  (`data/raw/legislatif/senat-odsen-general.csv`, puis `load_legislatif.py --source senat --force`,
  `datan`, `overrides`, `nuances`), vérifier les WARNING « groupe non classé » (décision Mathias),
  republier la base (`scripts/publish_db.sh`, nouvelle release `db-AAAA-MM-JJ`, tag hors `v*`).
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
