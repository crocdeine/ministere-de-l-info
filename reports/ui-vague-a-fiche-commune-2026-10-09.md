# Vague A, lot A3 : fiche commune (2026-10-09)

## Résumé exécutif
- Page web `#/commune?code=80021`, ouverte par clic sur la carte, par le lien « Ouvrir la fiche » de la commune choisie, ou par URL.
- Sections : chiffres-clés, historique électoral (graphique blocs + participation, tableau triable), bureaux de vote (repliable), élus, territoire, économie, source sous chaque bloc.
- Garde-fous : bandeau « Comparaison limitée » (type, tour, grille, découpage 2010, communes rattachées, seuil de nuançage), lignes interrompues aux ruptures, étiquette de méthode par scrutin, « Inclut les résultats de l'ancienne commune X », aucun qualificatif ni tendance.
- Export : `departements/<dep>/fiches.json.gz` (`export_web/fiches.py`) ; schéma de données 2 → 3 (`ancien_decoupage`, sources supplémentaires).
- Circonscriptions par intersection des contours (≥ 1 % de la surface) : Amiens 80-01 et 80-02, Paris 18. Les résultats ne rattachent chaque commune qu'à une seule circonscription.
- Parité Streamlit : 15/15 (Amiens, Paris, Ajaccio × présidentielles 2002-2022, inscrits, votants, exprimés, participation, bloc en tête).
- Tailles (France entière, sans tuiles) : fiches 1,1 Mo gz au total (max 0,63 Mo brut) ; bureaux max 4,17 Mo brut, communes max 1,57 Mo brut (< 8 Mo).
- Vérifications : ruff, format, pyright (0), pytest 340 passés ; tsc, vitest 24, build, budget 387,5 Ko ; e2e `e2e:fiche` et `e2e:url` OK WebKit + Chromium.
- Non fait : validation visuelle de Mathias ; vérification clavier à la main (seul l'e2e clavier : tri, ouverture des bureaux) ; pas de recompilation Tauri.
- Bug de données trouvé : députés de Corse en `2a`/`2b` dans `v_elus_actuels` (corrigé côté export, pas en base).

## Détail
- Économie : dernière valeur disponible par indicateur (8 indicateurs Filosofi/RP, CNAF, DREES) ; `null` hors Hauts-de-France → phrase « Hauts-de-France uniquement ».
- Seuil de nuançage : détecté dans les données (une ligne où toutes les voix sont non classées), aucun seuil codé en dur.
- Scrutin plurinominal (somme des voix > exprimés) : parts « n.d. » et remarque.
- Données de test : `outils/tmp/a3-ech/data` (dép. 80, 75, 2A, avec tuiles), lien `web/public/data` ; `a1-ech` laissé au schéma 2 (utilisé par un autre agent en parallèle). Export complet de contrôle : `outils/tmp/a3-export`.
- Port 4174 occupé par le serveur d'un autre agent : `captures.mjs` passe sur 4177, `url.mjs` accepte `PORT=` (leçon ajoutée).
- e2e fiche : un échec ponctuel en WebKit (carte non prête en 30 s, charge machine), vert au second passage.
- Captures : `docs/captures/a3/`.

## Questions fermées
1. Noms des anciennes communes : charger `LIBELLE_AV` du fichier COG des mouvements dans `communes_passage` pour afficher « ancienne commune de Yaucourt-Bussus » au lieu du code ? (oui / non)
2. Corriger `code_departement` des députés de Corse en majuscules dans l'ETL législatif (le filtre départemental de Streamlit les manque probablement) ? (oui / non)
3. Type affiché par défaut sur la fiche : présidentielle, 1er tour (choix actuel) ? (oui / non, « tous les types »)
