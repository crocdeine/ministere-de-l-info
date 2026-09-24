# 0012 — Exécution native sur le Mac mini (uv + LaunchAgent)

Date : 2026-09-24
Statut : Accepté
Décideurs : Mathias (décision du 2026-09-24, lot 6 : « on met l'app directement sur le Mac »)
Révise partiellement : le choix de la phase B (application servie par Docker/OrbStack sur
le Mac mini). Ne remplace pas l'image Docker, conservée en repli et pour la distribution.

Sources : `reports/rd-execution-mac-2026-09-24.md` (étude comparative, recommandation
option B), `reports/infra-2026-09-24.md`.

## Contexte

Depuis la phase B, l'application « de tous les jours » tourne dans un conteneur Docker
exécuté par OrbStack (petite machine virtuelle Linux) sur le Mac mini M4, alors que l'ETL,
les tests et le développement tournent déjà nativement sur le Mac avec uv.

Constats (rapport R&D) :

- Trois environnements à maintenir cohérents (Mac, conteneur Debian, CI Ubuntu) et deux
  Dockerfiles divergents ; trois incidents de la phase B venaient de cet écart (`pages/`
  absent de l'image, extension spatial absente, uv non figé).
- L'application n'utilise ni GeoPandas ni GDAL à l'exécution ; toutes ses dépendances
  (DuckDB, extension `spatial`, pyarrow, polars) existent en version officielle macOS arm64.
- La sauvegarde automatique copiait un volume Docker qui n'était pas forcément la base
  réellement utilisée, vers le même disque.
- Le port Docker `8501:8501` exposait l'application sur le réseau local.
- Un seul utilisateur : Mathias.

## Décision

1. **L'application tourne nativement sur macOS**, lancée par un LaunchAgent
   (`com.crocdeine.ministere-info.native` : `RunAtLoad`, `KeepAlive`), avec le Python de
   l'environnement uv du projet (`.venv/bin/python -m streamlit run app.py`), sans
   `uv run` au démarrage.
2. **Depuis le dossier du projet** de Mathias (`~/Documents/Docker/ministere-de-l-info`,
   paramétrable par `install-native.sh --projet`). Le rechargement automatique est
   désactivé : le code modifié est pris en compte au redémarrage (`start.sh`).
3. **Écoute sur `127.0.0.1` uniquement.**
4. **Chemin de la base par variable d'environnement** `MINISTERE_DB_PATH` (défaut
   `<projet>/data/ministere.duckdb`), lue par `src/ministere_de_l_info/config.py`.
5. **Sauvegarde quotidienne de ce même fichier** (`scripts/backup_db.sh`) : copie sous
   verrou partagé DuckDB, vérifiée, rotation 7 jours, destination paramétrable hors du
   disque interne (disque externe ou iCloud Drive).
6. **Transition** : double fonctionnement de deux semaines (natif sur 8502, Docker sur
   8501), puis point d'arrêt et validation de Mathias, puis arrêt de Docker et passage
   du natif sur 8501. OrbStack reste installé un mois de plus. Procédure :
   `docs/deployment.md` §3.

Outillage : `deploy/native/` (`install-native.sh`, `start.sh`, `stop.sh`, `status.sh`,
`uninstall-native.sh`, modèle `ministere-info.plist`), tests simulés
`deploy/tests/test_native.sh` et `deploy/tests/test_backup_db.sh`.

### Pourquoi le dossier du projet plutôt qu'une copie séparée

| Critère | Dossier du projet (retenu) | Copie séparée (`~/Library/Application Support/…`, mise à jour sur tag) |
|---|---|---|
| Nombre d'exemplaires du code, de `.venv`, de la base | 1 | 2 (ou base partagée entre deux codes) |
| Mise à jour | `git pull` + `install-native.sh` | script de publication/copie à écrire et maintenir |
| ETL | écrit directement la base lue par l'app | copie ou chemin croisé à gérer |
| Risque « code en cours de développement visible dans l'app » | réel, limité par l'absence de rechargement automatique (effet au redémarrage seulement) | nul |

Pour un utilisateur unique qui développe et consulte sur la même machine, la simplicité
l'emporte ; le risque résiduel est maîtrisé par `start.sh` explicite. Si un besoin de
stabilité apparaît, `--projet` permet de pointer vers un clone dédié sans changer les
scripts.

### Pourquoi cette méthode de sauvegarde

- Copie de fichier sous verrou partagé : l'app (lectrice) continue ; un ETL (écrivain) ne
  peut pas démarrer pendant la copie et, s'il écrit déjà, la sauvegarde s'abandonne
  (vérifié par test avec un vrai DuckDB). La copie est rouverte et comparée à l'original.
- `EXPORT DATABASE` écarté : plus lent, restauration en plusieurs étapes, dépendante de
  l'extension spatial pour les géométries.
- Copie brute sans verrou (ancienne méthode) écartée : incohérente si un ETL écrit.

## Alternatives considérées

| Option | Raison du rejet |
|---|---|
| A. Statu quo Docker/OrbStack | Trois environnements, machine virtuelle, chaîne de mise à jour longue (image de juin sans le design system), sauvegarde peu lisible. Note R&D 49/70 contre 58/70 pour le natif. Conservé en repli. |
| C. Application Mac empaquetée (PyInstaller, py2app, Briefcase, pywebview) | Streamlit se prête mal au gel, reconstruction complète à chaque correction, signature et notarisation Apple payantes. |
| C'. stlite / Pyodide | Non faisable : extensions binaires (DuckDB spatial) et base de 900 Mo incompatibles. |
| D. Hébergement (Streamlit Community Cloud, VPS, NAS) | Contraire au choix « local, fichier unique, sans serveur » (ADR-0001, ADR-0002) ; authentification et maintenance. |

## Conséquences

Positives :

- Un seul environnement (uv + `uv.lock`) pour le Mac, la CI et les sessions cloud.
- Démarrage en quelques secondes, pas de machine virtuelle ; base visible dans le Finder.
- Sauvegarde de la base réellement utilisée, hors du disque interne si configuré.
- Application invisible depuis le réseau local.

Négatives :

- Pas d'isolation : l'app tourne avec les droits de la session de Mathias (dépendances
  figées par `uv.lock`).
- Une montée de version de DuckDB impose de réinstaller l'extension spatial
  (`install-native.sh` le fait ; Internet requis ce jour-là).
- L'ETL impose d'arrêter l'app (`stop.sh`) : DuckDB n'accepte aucun écrivain pendant
  qu'un lecteur a la base ouverte.
- `docs/deployment.md` décrit désormais deux modes ; l'image GHCR n'est plus le chemin
  principal et peut vieillir.

## Réversibilité

Élevée, à tout moment :

- Retour à Docker : `deploy/native/uninstall-native.sh`, réactivation du LaunchAgent
  `com.ministere-info`, `docker compose up -d` (`docs/deployment.md` §3, « Retour arrière »).
- La bascule ne modifie ni la base ni l'installation Docker ; aucun fichier Docker n'est
  supprimé par cette décision.
- Coût du retour : si Docker lit une autre base que celle du projet, les mises à jour
  faites en natif entre-temps doivent y être recopiées.

## Points ouverts

- Sort de l'image GHCR et du workflow `docker-publish.yml` après la transition
  (conserver pour la distribution, ou mettre en sommeil) : dépend de l'existence d'autres
  utilisateurs d'`install.sh` (question 1 du rapport R&D).
- Job CI macOS arm64 (optionnel, étape 7 du plan R&D) non créé.
- Mesures réelles (mémoire, temps de démarrage) à relever pendant le double
  fonctionnement ; celles du rapport R&D viennent d'un conteneur Linux sans base.
