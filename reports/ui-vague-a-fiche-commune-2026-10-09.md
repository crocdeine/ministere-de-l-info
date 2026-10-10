# Vague A, lot A3 : fiche commune (2026-10-09)

## Résumé exécutif
- Page web `#/commune?code=80021`, ouverte par clic sur la carte, par le lien « Ouvrir la fiche » de la commune choisie, ou par URL.
- Sections : chiffres-clés, historique électoral (graphique blocs + participation, tableau triable), bureaux de vote (repliable), élus, territoire, économie, source sous chaque bloc.
- Garde-fous : bandeau « Comparaison limitée » (type, tour, grille, découpage 2010, communes rattachées, seuil de nuançage), lignes interrompues aux ruptures, étiquette de méthode par scrutin, « Inclut les résultats de l'ancienne commune X », aucun qualificatif ni tendance.
- Export : `departements/<dep>/fiches.json.gz` (`export_web/fiches.py`) ; schéma de données 2 → 3 (`ancien_decoupage`, sources supplémentaires).
- Circonscriptions par intersection des contours (≥ 1 % de la surface) : Amiens 80-01 et 80-02, Paris 18. Les résultats ne rattachent chaque commune qu'à une seule circonscription.
- Parité Streamlit : 15/15 (Amiens, Paris, Ajaccio × présidentielles 2002-2022, inscrits, votants, exprimés, participation, bloc en tête).
- Tailles (France entière, sans tuiles) : fiches 1,2 Mo gz au total (max 0,67 Mo brut) ; bureaux max 4,17 Mo brut, communes max 1,57 Mo brut (< 8 Mo).
- Vérifications (2026-10-10, après fusion de main) : ruff, format, pyright (0), pytest 346 passés ; tsc, vitest 31, build, budget 397,3 Ko ; e2e `e2e:fiche` et `e2e:url` OK WebKit + Chromium.
- Non fait : validation visuelle de Mathias ; vérification clavier à la main (seul l'e2e clavier : tri, ouverture des bureaux) ; pas de recompilation Tauri.
- Suites (décisions du directeur) : noms des anciennes communes (`communes_passage.libelle_ancien`), codes Corse corrigés dans le chargeur Datan ; base réelle à recharger (commandes ci-dessous).

## Détail
- Économie : dernière valeur disponible par indicateur (8 indicateurs Filosofi/RP, CNAF, DREES) ; `null` hors Hauts-de-France → phrase « Hauts-de-France uniquement ».
- Seuil de nuançage : détecté dans les données (une ligne où toutes les voix sont non classées), aucun seuil codé en dur.
- Scrutin plurinominal (somme des voix > exprimés) : parts « n.d. » et remarque.
- Données de test : `outils/tmp/a3-ech/data` (dép. 80, 75, 2A, avec tuiles), lien `web/public/data` ; `a1-ech` laissé au schéma 2 (utilisé par un autre agent en parallèle). Export complet de contrôle : `outils/tmp/a3-export`.
- Port 4174 occupé par le serveur d'un autre agent : `captures.mjs` passe sur 4177, `url.mjs` accepte `PORT=` (leçon ajoutée).
- e2e fiche : un échec ponctuel en WebKit (carte non prête en 30 s, charge machine), vert au second passage.
- Captures : `docs/captures/a3/`.

## Suite du 2026-10-10 (relectures et décisions du directeur)
- Décisions : (a) noms des anciennes communes : oui ; (b) Corse corrigée à la source : oui ; (c) présidentielle 1er tour par défaut : oui.
- Relecture React : cache des fichiers par département, état indexé par département (pas d'éclair « commune inconnue »), garde du chargement des bureaux de vote, choix du bureau remis à zéro par commune, tri mémoïsé, mouvement réduit.
- Relecture export : `elus_hors_perimetre` = 37 et `economie_communes_anciennes` = 7 (27 codes dans `economie_rp`, dont 20 déjà écartés par la vue) dans `manifest.perimetre` + avertissement ; repli des circonscriptions sur les derniers résultats législatifs (975, îles) ; 975 nommé « Saint-Pierre-et-Miquelon ». Documentés dans `docs/methodologie.md` (limites) et `docs/schema-elections.md`.
- Fusion de main (Méthodologie #21) : navigation Méthodologie conservée, `PAGES_URL` avec `methodologie` et `commune`, schéma de données 3 (fiches + `methodologie.json.gz`). La fiche ouvre le panneau Méthodologie (ruptures, bloc en tête, valeurs n.d., limites ; ancre `limites` ajoutée).
- Données de test : copie de la base (`outils/tmp/a3-base`) avec `communes_passage` rechargée ; la base réelle n'est pas modifiée.
- e2e fiche : un échec ponctuel en WebKit (page lente sous charge), vert au second passage.

## Base réelle : commandes à lancer (non exécutées)
```bash
# Noms des anciennes communes (fichier COG en cache, sans re-téléchargement)
uv run python scripts/load_communes_passage.py
# Codes Corse : recharge Datan (et nuances des non-inscrits, incluses), puis les overrides
uv run python scripts/load_legislatif.py --source datan
uv run python scripts/load_legislatif.py --source overrides
# Puis réexport web
uv run python scripts/export_web.py --tippecanoe /chemin/vers/tippecanoe
```
`--source all` recharge aussi le Sénat (depuis le cache sans `--force`) : inutile pour ces deux corrections.
