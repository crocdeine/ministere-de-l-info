# Journal des modifications

Toutes les évolutions notables de ministere-de-l-info. Format :
[Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions
[SemVer](https://semver.org/lang/fr/). Les bases de données sont publiées à part, sous des tags
`db-AAAA-MM-JJ`.

## [Non publié]

## [1.0.0] — date de publication à fixer

Première version de production : l'application Streamlit complète, installée sur un Mac par une
seule commande.

### Ajouts
- Installateur en une commande pour macOS (`install.sh`) : télécharge l'application et la base
  (empreinte SHA-256 vérifiée, reprise d'un téléchargement interrompu, base conservée si inchangée),
  installe Python 3.12 et les dépendances avec uv, crée l'icône « Ministère de l'Info » dans
  `~/Applications`. Sans `sudo` ni jeton GitHub. Désinstallation par `uninstall.sh`.
- Licences : code sous MIT, base sous ODbL (`LICENSE-DONNEES.md`), registre des sources et de leurs
  mentions (`docs/sources.md`, ADR-0013), fond de carte Plan IGN.
- Design system v2 « direction éditoriale » (ADR-0014) : noir et blanc, titres en capitales,
  filets fins, Bleu France pour les actions, Rouge Marianne pour les alertes, template Plotly unifié.
- Législatif : non-inscrits rattachés au bloc de leur nuance d'élection (ou de celle de leur
  titulaire pour un remplaçant).
- Économie : déserts médicaux à trois états (désert, hors désert, sans donnée), classes fixes par
  indicateur.
- Élections : légende du classement propre à chaque scrutin ; « grille officielle » réservée aux
  municipales 2020 et 2026 (ADR-0010).
<!-- Directeur : ajouter ici les apports de la vague B (élections France entière, etc.) s'ils sont
     fusionnés avant la publication, et la base `db-AAAA-MM-JJ` retenue. -->

### Modifications
- Absences de données affichées « n.d. » au lieu de 0 % ; évolutions en % des exprimés par
  défaut ; score de bloc sur une échelle fixe de 0 à 100 %.
- Libellés corrigés : « circonscriptions en tête » (et non « gagnées ») au 1er tour ; seuil
  municipal de 9 000 habitants « suspendu » (et non « annulé ») par le Conseil d'État.
- Sécurité de déploiement : serveur limité à 127.0.0.1, empreinte SHA-256 obligatoire au
  téléchargement de la base, actions GitHub et images Docker épinglées.

### Retraits
- Date de naissance des parlementaires (ADR-0013).

### Corrections
- Refus de la page HTML servie par data.senat.fr à la place du fichier attendu.
- Correctifs de la revue fonctionnelle (commune conservée d'un scrutin à l'autre, attribution des
  géométries de circonscriptions, tableau de démonstration retiré de l'accueil).

## [0.5-economie-legislatif] — 2026-06-25

Modules Économie (Filosofi, recensement, CNAF, DREES, URSSAF, Eurostat) et Législatif (députés et
sénateurs, groupes classés par législature). Voir `reports/` pour le détail.

[Non publié]: https://github.com/crocdeine/ministere-de-l-info/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/crocdeine/ministere-de-l-info/compare/v0.5-economie-legislatif...v1.0.0
[0.5-economie-legislatif]: https://github.com/crocdeine/ministere-de-l-info/releases/tag/v0.5-economie-legislatif
