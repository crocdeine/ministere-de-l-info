# 0016 — Couleur d'interface : palette « Papier »

Date : 2026-10-07
Statut : Accepté (Mathias, 2026-10-07) — complète l'[ADR-0014](0014-design-system-direction-editoriale.md)
Décideurs : Mathias (supervision)

## Contexte

Mathias souhaite davantage de couleur dans l'interface sans perdre la direction éditoriale de
l'ADR-0014 (noir et blanc, Bleu France = action, Rouge Marianne = alertes). La recherche
(`reports/recherche-ui-couleur-2026-10-07.md`) montre qu'aucune teinte franche n'est politiquement
neutre en France (rouge/rose : gauche ; bleu/marine : droite et extrême droite ; jaune : centre ;
vert : écologistes ; brun, violet, noir : connotation extrême droite documentée). Une couleur
d'interface ne doit ni suggérer une préférence ni concurrencer les couleurs des blocs sur les cartes.

## Décision

1. **Palette « Papier »** : la couleur entre par les surfaces, en neutres chauds repris du DSFR.

   ```css
   :root {
     --papier-50:  #f9f6f2; /* fond de section */
     --papier-100: #f3ede5; /* en-tête de module, ligne survolée */
     --papier-200: #eee4d9; /* sélection de ligne de tableau */
     --sable-700:  #6a6156; /* métadonnées sur fond papier */
     --surface-section: var(--papier-50);
     --surface-header:  var(--papier-100);
     --text-meta-warm:  var(--sable-700);
   }
   ```

   Contrastes : encre sur `#f9f6f2` 18,4:1 ; gris des légendes 6,2:1 ; `#6a6156` sur `#f9f6f2` 5,6:1
   (tous ≥ AA). Bleu France et Rouge Marianne inchangés.
2. **Jamais de fond papier sous une carte ou un graphique partisan** : plaque blanche fixe
   (CENT et DIV perdent du contraste sur papier).
3. **Pas de code couleur par module** (collision avec les blocs) : numérotation « 0X — » et pictogramme.
4. **Palettes écartées** : « Bleu France étendu » en fond (écho droite/extrême droite) ; sarcelle
   « Archipel » pour les graphiques non partisans (évocation écologiste).
5. **Mode sombre** (future application web uniquement) : valeurs sombres officielles du DSFR ; cartes
   et graphiques partisans sur plaque blanche fixe (EXD et EXG tombent sous 2:1 sur fond sombre).
6. **Étiquette de méthode** sur chaque visualisation : « Grille officielle » ou « Reconstruit »,
   ouvrant le panneau Méthodologie.

## Conséquences

- Tokens ajoutés à `tokens.css` de la future interface (vague A, lot A1) ; Streamlit étant gelé
  (ADR-0015), il n'est pas retouché sauf correction.
- Skill `design-system-mi` à compléter (section couleur) lors du lot A1.
- Couleurs de blocs inchangées (source unique : `_blocs_politiques.py` ; la skill
  `data-viz-politique` est réalignée sur cette source).
