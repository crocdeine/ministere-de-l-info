# Point de reprise — à lire en premier par toute nouvelle session

Dernière mise à jour : 2026-10-04 (fin de soirée), branche `claude/exciting-dirac-8mogwe`.
Lire ensuite : `docs/orientations.md`, `docs/journal.md` (dernières entrées), `docs/roadmap.md`.

## Où on en est

- Phase 0 (audit) : validée. Jalon J1 (conformité) : fait, base publiée (`db-2026-10-04`, ODbL).
- **Jalon J2 (exactitude) : code terminé et commité, PAS ENCORE RELU ni rapporté à Mathias.**
  - Chômage RP 2015-2016 reconstitué par sexe (`68e7687`).
  - Valeurs absentes affichées « n.d. », carte déserts médicaux à 3 états (`5e80ebd`).
  - Non-inscrits AN classés selon leur nuance préfectorale d'élection : 69 mandats reclassés,
    30 non retrouvés laissés en DIV (`ea2b2f7`, `1e6edd0`, rapport `reports/etl-non-inscrits-2026-10-04.md`).
  - Sources officielles des classements, groupes historiques du Sénat (`b7c51cd`, rapport
    `reports/verification-classements-j2-2026-10-04.md`).
  - Base locale rechargée (Législatif, RP) ; copie avant J2 : `data/ministere.duckdb.bak-avant-j2`.
  - Mesures : 637 tests réussis, 0 échec ; couverture 76,83 %.

## Prochaines étapes, dans l'ordre

1. **Relecture indépendante de J2** (agent `verificateur-code`, modèle le plus puissant) : diff
   `94a0d15..HEAD`. Tâche critique (classement politique) : **ne pas confier à un modèle faible**.
2. Pousser la branche, vérifier la CI du commit poussé (règle CLAUDE.md).
3. Rapport à Mathias en langage simple, avec 3 questions fermées issues de l'agent ETL :
   remplaçants (nuance du titulaire ?), source AMO de l'AN pour les 30 cas non résolus,
   confirmation que Ménard et Dupont-Aignan restent DTE (application stricte de sa règle).
4. Mettre à jour `docs/journal.md`, `docs/roadmap.md` (J2 fait), `docs/audit-2026-10-04.md` (statuts).
5. Nettoyer les worktrees d'agents (`.claude/worktrees/agent-*`) après fusion.

## En attente d'un événement extérieur

- **Groupes du Sénat après le renouvellement du 27/09** : tâche planifiée quotidienne
  « veille-groupes-senat » (`scripts/veille_groupes_senat.py`). Quand elle signale que tous les
  sénateurs ont un groupe : remettre le fichier d'octobre en cache
  (`data/raw/legislatif/senat-odsen-general.csv`, puis `load_legislatif.py --source senat --force`,
  `datan`, `overrides`, `nuances`), vérifier les WARNING « groupe non classé » (décision Mathias),
  republier la base (`scripts/publish_db.sh`, nouvelle release `db-AAAA-MM-JJ`, tag hors `v*`).
- Fichier Sénat d'octobre mis de côté : `data/raw/legislatif/senat-odsen-general-2026-10-04.csv`.

## Règles pour une session via omniroute (modèle non Claude ou moins puissant)

- Autorisé : documentation, tests, nettoyage technique, mise à jour du journal.
- **Interdit** (mettre en attente) : tout classement politique, toute relecture de neutralité ou
  de conformité juridique, validation finale de données, publication, fusion dans `main`.
- Ne jamais envoyer `.env` ni aucun secret au modèle.
- Noter la bascule dans `docs/modeles.md` (journal des bascules).
