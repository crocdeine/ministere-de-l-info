# À faire sur le Mac — liste tenue à jour par le directeur

Dernière mise à jour : 2026-09-25 (constat réel du Mac : pas de Docker installé, projet sur disque externe)

Ce fichier regroupe tout ce qui ne peut être fait que sur le Mac mini : la session cloud n'a ni la base de données, ni accès aux sites officiels. **Suivre les étapes dans l'ordre.**

> **État au 2026-09-25** : étapes 0 à 4 faites par Mathias. Prochaine étape : **4 bis** (correctifs issus de ce retour), puis 5.

## Comment procéder (le plus simple)

Pour chaque étape, ouvrir le Terminal dans le dossier du projet, lancer Claude Code, et lui écrire simplement :

```
Exécute l'étape N de reports/a-faire-sur-le-mac.md, puis donne-moi le résumé à transmettre au directeur.
```

(remplacer N par le numéro). Claude Code local fait les commandes, vérifie les résultats et s'arrête s'il y a un problème. Il termine par un **résumé de 5 lignes à copier-coller dans la conversation avec le directeur**. Les commandes sont aussi détaillées ci-dessous pour qu'on puisse les suivre ou les faire à la main.

Dossier du projet : `/Volumes/le gros stockage/ministere-de-l-info` (disque externe — **toujours entre guillemets** dans les commandes, le chemin contient des espaces). Exemple pour se placer dedans :

```bash
cd "/Volumes/le gros stockage/ministere-de-l-info"
```

---

## Étape 0 — Récupérer la branche de travail ✅ Prête

```bash
cd "/Volumes/le gros stockage/ministere-de-l-info"
git fetch origin
git switch claude/exciting-dirac-8mogwe
git pull
uv sync --frozen --group etl
```

Vérification : `git log --oneline -1` affiche un commit du 2026-09-24.

---

## Étape 1 — Vérifier les codes de nuances 2008/2014 ✅ Prête

Dans Claude Code, taper :

```
/verifier-nuances-2008-2014
```

Claude Code vérifie tout seul sur le site d'archives du ministère, mesure le poids de chaque code dans la base (sans rien modifier) et envoie le résultat sur GitHub. **Copier la phrase « Message à transmettre au directeur »** et la coller dans la conversation avec le directeur.

---

## Étape 2 — Appliquer les corrections à la base ✅ Prête

Ce que cela applique : correctifs des bugs critiques (nuances municipales effacées, corrections ignorées, listes fusionnées), 18 reclassements de nuances (ADR-0010), classement des groupes parlementaires par législature (ADR-0011).

1. **Arrêter l'application si elle tourne déjà** (DuckDB n'accepte qu'un seul écrivain) :
   - Si l'étape 5 (installation native) a déjà été faite : `./deploy/native/stop.sh`.
   - Sinon (cas du 25/09, aucune installation encore en place) : rien à faire, aucun programme ne lit la base.
2. **Copie de sécurité de la base** :
   ```bash
   cp data/ministere.duckdb data/ministere.duckdb.bak-2026-09-24
   ```
3. **Appliquer** :
   ```bash
   uv run python scripts/init_elections_schema.py
   uv run python scripts/load_elections_municipales.py
   uv run python scripts/migrations/0007_add_municipales_views.py
   uv run python scripts/migrations/0008_legislatif_groupes_par_legislature.py
   uv run python scripts/load_legislatif.py --source datan
   uv run python scripts/load_legislatif.py --source overrides
   ```
4. **Contrôler** :
   ```bash
   uv run pytest -q
   uv run pytest tests/test_elections_municipales.py tests/test_elections_legislatives.py tests/test_legislatif.py -q
   ```
   Et dans DuckDB (Claude Code peut les lancer) :
   - `SELECT annee, COUNT(*) FROM nuances_harmonisees GROUP BY 1 ORDER BY 1;` → total **226** (municipales : 2008=12, 2014=17, 2020=23, 2026=25)
   - aucun doublon de liste : requête « doublons » de l'annexe A de `reports/synthese-vague-1-2026-09-24.md` → 0 ligne
   - aucun groupe parlementaire sans bloc (requêtes de contrôle de `docs/adr/0011-legislatif-groupes-par-legislature.md`)
   - noter tout message « WARNING groupe non classé » affiché au chargement
5. **Redémarrer l'application si elle avait été arrêtée à l'étape 1** : `./deploy/native/start.sh`.

À signaler au directeur : tout test en échec, tout WARNING, et le test `test_lille_2020_t1_blocs_cohérents` s'il échoue (cas prévu, à analyser).

---

## Étape 3 — Vérifier visuellement l'application ✅ Prête

Ouvrir http://localhost:8501 et contrôler :

- **Accueil** : chaque tuile indique son périmètre (Hauts-de-France ou France) et sa période.
- **Géographie** : Communes + département Nord → environ 648 lignes (plus de limite à 200), tri par colonne, bouton d'export CSV ; Départements filtrés sur la région Hauts-de-France → 5 lignes seulement.
- **Élections** : la participation Hauts-de-France a changé de valeur (elle est désormais pondérée) ; zone « 21e circonscription du Nord — Valenciennes » ; passer d'un onglet à l'autre puis revenir : les sélections restent en place ; municipales : nouveaux blocs visibles (ex. listes PCF en gauche, UDI au centre).
- **Économie** : chômage 2015/2016 affiché (plus de carte grise) ; encadré explicatif RSA ; croisement économie × élections : 1er tour par défaut, seules les années exploitables sont proposées.
- **Législatif** : l'onglet Activité s'affiche sans avoir à choisir la chambre ; recherche d'un député précis ; groupes LFI 2017-2024 en gauche.
- **Libellés** des chiffres clés plus foncés et lisibles.

Noter ce qui semble faux ou étrange et le transmettre au directeur.

---

## Étape 4 — Créer l'extrait de base pour les tests ✅ Prête

Application arrêtée (comme à l'étape 2), puis :

```bash
uv run python scripts/export_sample_db.py
uv run pytest tests/test_sample_db.py -q -rs
git add tests/fixtures/sample/
git commit -m "test: échantillon Parquet de la Somme pour tests hermétiques"
git push
```

Le script refuse de dépasser 5 Mo. Signaler au directeur tout avertissement `EcartSchemaEchantillon`.

---

## Étape 4 bis — Appliquer les correctifs issus du retour du 25/09 ✅ Prête

Correctifs : lot 2 (LMAJ 2008 → droite, LCMD 2008 → centre, 229 nuances), anciens groupes du Sénat d'avant 2002 exclus, chômage RP 2015/2016 (faux secret statistique), échantillon complété avec les tables du Législatif, corrections d'interface.

```bash
cd "/Volumes/le gros stockage/ministere-de-l-info"
git pull
uv sync --frozen --group etl
cp data/ministere.duckdb data/ministere.duckdb.bak-2026-09-25
uv run python scripts/init_elections_schema.py
uv run python scripts/load_elections_municipales.py
uv run python scripts/migrations/0007_add_municipales_views.py
uv run python scripts/load_legislatif.py --source senat
uv run python scripts/load_economie.py --source rp --millesimes 2015,2016
uv run pytest -q
uv run python scripts/export_sample_db.py
git add tests/fixtures/sample/
git commit -m "test: échantillon Parquet régénéré (tables législatives)"
git push
```

Contrôles attendus :
- `SELECT annee, COUNT(*) FROM nuances_harmonisees GROUP BY 1 ORDER BY 1;` → municipales 2008=15, 2014=17, 2020=23, 2026=25 ; **total 229**.
- LMAJ 2008 en DTE (43 communes, 114 281 voix au 1er tour) ; LCMD 2008 en CENT (6 communes).
- `test_aucun_mandat_non_classe` passe. S'il échoue encore, **noter les sigles des groupes restants** (3 groupes du Sénat pouvaient manquer à la liste) et les transmettre.
- Le chargement RP affiche un avertissement listant les clés manquantes par millésime : **le copier dans le résumé** (il dira si la donnée chômage 2015/2016 existe sous un autre nom).
- Revérification à l'écran : Économie (plus d'erreur `isnan`, années sans chômage non proposées), Présidentielles (le bouton Zone reste cohérent après changement d'onglet), Législatif (participation en %).

---

## Étape 5 — Installer l'application en direct sur le Mac (pas de Docker) ✅ Prête — avec POINT D'ARRÊT

Constat du 25/09 : aucun conteneur ni image Docker sur le Mac. Il n'y a rien à comparer
ni à basculer entre deux versions : l'installation se fait directement sur le port 8501.
Procédure complète dans `docs/deployment.md` §3 (ADR-0012 et son addendum du 25/09). À
faire de préférence avec Claude Code : « Exécute l'étape 5 de reports/a-faire-sur-le-mac.md
en suivant docs/deployment.md §3, étape par étape, en t'arrêtant au POINT D'ARRÊT ».

En résumé (`PROJET="/Volumes/le gros stockage/ministere-de-l-info"`) :
1. Constater l'absence de conteneur Docker (`docker ps`).
2. Copie de sécurité de la base.
3. Code à jour et `uv` installé.
4. Vérifier que le port 8501 est libre.
5. `./deploy/native/install-native.sh` → l'app native tourne directement sur le **port 8501**.
   Le script détecte et désactive proprement l'ancien agent de sauvegarde en échec
   (`com.crocdeine.ministere-info.backup`, plist rangé dans
   `~/Library/LaunchAgents/desactives/`, rien n'est supprimé).
6. Régler la sauvegarde vers un disque différent de celui du projet (`--sauvegarde-vers`),
   puis tester `./scripts/backup_db.sh` et une restauration à blanc.
7. Redémarrer le Mac → `./deploy/native/status.sh` doit dire OK sans rien relancer à la
   main (le disque externe doit être monté ; voir la limite documentée en `docs/deployment.md` §1).

**POINT D'ARRÊT avant l'étape 5.5** (désactivation de l'ancien agent de sauvegarde) :
vérifier le contenu de `~/Library/LaunchAgents/desactives/` et ne rien supprimer
manuellement sans validation explicite de Mathias en chat.

---

## Étape 6 — Recharger le Sénat après les sénatoriales du 27/09 ⏳ Après mise à jour de data.senat.fr

```bash
cp data/ministere.duckdb data/ministere.duckdb.bak-avant-senat-2026
uv run python scripts/load_legislatif.py --source senat --force
uv run python scripts/load_legislatif.py --source datan
uv run python scripts/load_legislatif.py --source overrides
uv run pytest tests/test_legislatif.py tests/test_legislatif_memoire.py -q
```

Contrôles : 348 sénateurs actifs, aucun groupe sans bloc. **Tout WARNING « groupe non classé » (nouveau groupe issu du renouvellement) doit être transmis au directeur avant toute publication de la base.** Vérifier aussi les nouveaux sénateurs RN éventuellement non-inscrits (overrides).

---

## Étape 7 — Tester la mise à jour de la base ⏳ Après fusion dans `main`

Les scripts d'installation et de mise à jour des utilisateurs sont lus depuis `main`. Après fusion : lancer `deploy/update.sh` → un retéléchargement unique attendu (dernière fois), puis une seconde exécution doit afficher « déjà à jour ».
