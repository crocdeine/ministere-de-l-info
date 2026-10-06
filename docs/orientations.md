# Orientations de Mathias

Résumé des grandes décisions et préférences. À relire avant tout travail important.
Les décisions techniques détaillées sont dans `docs/adr/` ; les décisions de vague dans `reports/synthese-*`.

## Mission et ton

- Outil professionnel de data-visualisation politique et électorale, construit sur le long terme, exigence
  de qualité élevée. L'outil **informe, il ne plaide pas**.
- Communication en français, langage simple, sans jargon non expliqué, comptes rendus courts.

## Pilotage (consigne du 2026-10-04)

- Mathias donne les orientations ; le directeur traduit, décide du technique, documente.
- Agir sans demander : petit, réversible, technique, couvert par les tests.
- Agir puis informer : changements moyens multi-fichiers.
- Attendre l'accord : architecture majeure, ajout/remplacement de source importante, juridique (RGPD,
  licences, personnes), publication, irréversible ou coûteux, neutralité, suppression de données non
  régénérables.
- Une seule question courte à la fois, avec des choix simples, seulement si l'erreur serait coûteuse.

## Contraintes permanentes

- Chaque source : licence et provenance dans `docs/sources.md`, mentions affichées dans l'interface.
- RGPD : seulement des données publiques et officielles sur les élus.
- Corrections manuelles documentées, justifiées, sourcées.
- Aucun secret dans le dépôt, détection automatique en pre-commit.
- Tests jamais dégradés : couverture stable ou en hausse, CI verte.
- Git : branches, Conventional Commits ; fusion dans `main`, push, release seulement avec accord.
- Sauvegardes zip vérifiées dans `../ministere-de-l-info-backups/` avant tout nettoyage.

## Décisions antérieures toujours en vigueur (rappel)

- Stack non négociable (CLAUDE.md) ; nomenclature officielle des blocs (ADR-0005 révisé par ADR-0010) ;
  Législatif par législature (ADR-0011) ; exécution native sur Mac (ADR-0012).
- Décisions de la vague 2 en attente (lots A à G) : voir `reports/synthese-vague-2-2026-09-24.md` §3.

## Décisions du 2026-10-04 (validation de l'audit)

- Base de données publiée sous **ODbL** ; code sous **MIT** (ADR-0013).
- **Minimisation** : pas de date de naissance des élus dans la base.
- **Non-inscrits** : classés selon la nuance attribuée par la préfecture à leur élection
  (et non « Divers » par défaut) — à appliquer en J2.
- **Neutralité des titres** : pas de parti nommé dans les questions éditoriales ; on raisonne
  par blocs ; pas d'intitulé qui présuppose une conclusion (« Désindustrialisation » → « Emploi
  industriel et accès aux médecins »).
- Une classification reconstruite par le projet n'est jamais présentée comme officielle.

## Décisions du 2026-10-06 (non-inscrits, suite de J2)

- **Remplaçants** (suppléants devenus députés) : reçoivent la nuance préfectorale d'élection de leur
  titulaire.
- **Source officielle des mandats de l'Assemblée nationale (AMO)** : autorisée, pour identifier
  élus, élus de partielles et remplaçants.
- **Ménard et Dupont-Aignan** : classés Droite (DTE), application stricte de la nuance préfectorale ;
  la règle s'applique sans exception.

## Décisions du 2026-10-06 (seuils des cartes, J3)

- Score d'un bloc : échelle fixe **0-100 %** à tous les scrutins et tours.
- Taux de pauvreté : classes **10 / 15 / 20 / 25 %**.
- Niveau de vie médian : euros courants, **mention « non corrigés de l'inflation »** en légende.
- Indicateurs à zéros fréquents (logements sociaux, emploi industriel, RSA) : **classe « 0 » distincte**.
- Principe : classes fixes, identiques pour toutes les années ; absence de donnée toujours « n.d. ».

## Décisions du 2026-10-06 (J4)

- Copies de la base : seules la base active et la dernière copie de sécurité restent dans `data/`.
- **Sauvegardes** : la tâche planifiée du Mac est supprimée ; le directeur de projet en est garant
  (zip vérifié du projet à chaque grande étape ; zip de la base avant toute écriture importante ou
  publication ; registre `../ministere-de-l-info-backups/BACKUPS.md`).

## Décisions du 2026-10-06 (mode d'exécution, fusion)

- Docker n'est plus la manière recommandée de faire tourner l'application sur le Mac : l'exécution
  native (ADR-0012, `deploy/native/`) est la cible. Les fichiers Docker sont conservés pour une
  éventuelle distribution, sans maintenance active.
- Installation native sur le Mac : **reportée** (décision Mathias) ; à proposer de nouveau plus tard,
  avec l'option `--sans-sauvegarde` (le directeur est garant des sauvegardes).
- Le projet reste sur le disque externe : le disque interne est plein à 97 % (6,2 Go libres).
- Fusion dans `main` : seulement après correction des erreurs de typage (pyright à 0, rendu bloquant).

## Décisions du 2026-10-06 (cible de production, design system v2)

- **Cible de production : option 2** — interface web moderne, emballée en application Mac (Tauri),
  publiable à un **public très restreint**. Le cœur de données (ETL Python, DuckDB, classements,
  tests, licences) est conservé. Révisera l'ADR-0002 (Streamlit) par un nouvel ADR. Étape suivante :
  maquette d'une page avant toute réécriture.
- **Design system v2 « direction éditoriale »** (fourni par Mathias) adopté : skill
  `.claude/skills/design-system-mi`, ADR-0014 (révise l'ADR-0009). Écarts validés : palette
  d'évolution accessible conservée (J3) ; ADR renuméroté 0014 (0007 = Législatif).
- La fusion dans `main` (PR #1) est faite le 2026-10-06 après mise à 0 des erreurs de typage.
