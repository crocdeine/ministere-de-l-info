# 0013 — Licences du projet et mentions des sources

- **Date** : 2026-10-04
- **Statut** : accepté (décision Mathias du 2026-10-04, recommandations de l'audit Phase 0)
- **Contexte** : `docs/audit-2026-10-04.md`, constats B1, B2, B3, I3, I4, I5

## Contexte

Le dépôt est public et la base `ministere.duckdb` est publiée dans les releases GitHub.
L'audit du 2026-10-04 a établi que :

1. la base contient les données URSSAF, sous **ODbL 1.0** : toute base dérivée doit être
   rediffusée sous ODbL (partage à l'identique) ; aucune licence n'était déclarée ;
2. le dépôt n'avait aucune licence ;
3. l'interface n'affichait ni licence ni date, et attribuait à l'IGN des contours de
   circonscriptions publiés par un particulier ;
4. les pages Élections présentaient comme « nomenclature officielle » des classements de
   blocs reconstruits par le projet (ADR-0010) ;
5. `leg_elus.date_naissance` était publiée sans être utilisée.

## Décision

1. **Code sous MIT** (`LICENSE`), **base sous ODbL 1.0** (`LICENSE-DONNEES.md`), les contenus
   gardant la licence de leur producteur, liste des attributions dans `LICENSE-DONNEES.md`.
2. **Registre unique des sources** : `src/ministere_de_l_info/sources.py` (producteur, licence,
   lien, tables). Il alimente le tableau « Sources, licences et dates » de l'Accueil (date =
   dernier chargement lu dans `_etl_metadata`) et les légendes via `mention()`. Le détail et
   l'état de vérification restent dans `docs/sources.md`.
3. **Légende des blocs par scrutin** : `legende_classement_blocs()` dans `_blocs_politiques.py`
   indique « grille officielle » pour les seules municipales 2020 et 2026, « reconstruction par le
   projet » avec la grille de référence sinon.
4. **Minimisation** : colonne `leg_elus.date_naissance` supprimée (schéma, loaders, échantillon de
   test) ; migration idempotente dans `create_legislatif_schema()`.
5. **Fond de carte** : Plan IGN (Géoplateforme, Licence Ouverte, sans clé) atténué à 35 %, via
   `viz._display.nouvelle_carte()`, à la place de CARTO (clé désormais exigée, filigrane
   « API KEY REQUIRED ») et d'OpenStreetMap.

## Conséquences

- La prochaine release de la base doit porter la mention ODbL et la liste des sources, et être
  générée sans `date_naissance` (publication soumise à l'accord de Mathias).
- Les releases déjà publiées (dont `v0.5-economie-legislatif`) contiennent encore
  `date_naissance` et aucune mention de licence ; l'échantillon de test commité le 2026-09-25
  contient des dates de naissance dans l'historique git (données publiques à la source).
  Les retirer suppose de modifier des publications ou de réécrire l'historique : décision
  Mathias.
- Toute nouvelle source doit être ajoutée à `sources.py`, `docs/sources.md` et
  `LICENSE-DONNEES.md` ; le test `tests/test_conformite.py` vérifie licence et lien.
