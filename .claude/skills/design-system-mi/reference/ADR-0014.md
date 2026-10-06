# 0014 — Design system v2 : direction éditoriale

Date : 2026-10-04 (appliqué sur la base J1-J4 le 2026-10-06)
Statut : Proposé (en attente de validation visuelle par Mathias) — révise l'[ADR-0009](0009-design-system-et-navigation.md)
Décideurs : Mathias (supervision)

## Contexte

Le design system v1 (août 2026, [ADR-0009](0009-design-system-et-navigation.md), rapport
`session-2026-08-19_design-system-cloture.md`)
reprend les codes du DSFR : fond gris clair, cartes blanches arrondies avec
ombre, titres en Spectral (serif), callouts colorés. Le rendu est propre mais
proche d'un site administratif générique.

Mathias souhaite une identité plus moderne et plus affirmée. Référence fournie :
le modèle Wix « Artiste (typographie en gras) » — grotesque très gras en
capitales, noir et blanc, beaucoup de blanc, grille asymétrique, boutons à
contour fin, flèche diagonale comme signe. Une proposition a été maquettée dans
un canvas Claude Design (« Ministère de l'Info — Direction éditoriale » :
planches Fondations, Composants, Exemple d'accueil).

## Décision

Adopter une **direction éditoriale** pour l'interface, en conservant l'ancrage
républicain et toutes les palettes de données :

- **Couleur** : interface en noir (`#0a0a0a`) et blanc (`#ffffff`). Le Bleu France
  marque l'action et la sélection (survol des boutons, focus, champ actif, export
  CSV). Le Rouge Marianne est réservé aux alertes et limites. Palettes de
  nuances politiques et de choroplèthes **inchangées** (voir « Écarts » : la
  palette d'évolution reste la palette accessible de J3).
- **Typographie** : une seule famille d'interface, Hanken Grotesk (400 → 900) ;
  titres en capitales, graisse 900, approche serrée (−0,045 em). IBM Plex Mono
  pour les données et repères de section. **Spectral est retiré.**
- **Forme** : aucune ombre, aucun arrondi sur les surfaces ; 8 px sur les
  contrôles ; filets d'un pixel comme structure (au-dessus des cartes, des
  métriques, des sections, des alertes).
- **Contrôles** : hauteur minimale 44 px ; champs soulignés ; libellés en
  capitales 12 px.
- **Graphiques** : template Plotly `mdi` enregistré par défaut (même police,
  fond blanc, filets encre, info-bulle noire).
- **Emoji** : les pages restent nommées avec emoji (nom de fichier), mais
  l'interface utilise Material Symbols et une numérotation « 01 — ».

Implémentation : `custom.css` réécrit (les **noms** de tokens v1 sont conservés
comme alias pour ne rien casser), `_theme.py` (en-tête éditorial,
`render_overline`, template Plotly), `.streamlit/config.toml` (fond blanc,
encre), page Accueil.

Ce qui ne change pas par rapport à l'ADR-0009 : routeur `st.navigation()` /
`st.Page()`, injection unique dans `app.py`, source unique des couleurs de blocs
(`_blocs_politiques.py`), sélecteurs `data-testid` uniquement.

## Écarts par rapport à la proposition initiale (décidés le 2026-10-06)

Décidés par le directeur de projet et validés par Mathias lors de l'application
du patch sur la base J1-J4 :

1. **Palette d'évolution de population** : la proposition reprenait RdYlGn
   (rouge → vert, `#d73027 … #1a9850`). Elle est **écartée** au profit de la
   palette accessible daltonisme adoptée en J3 à la demande de Mathias (PuOr,
   `_COULEURS_EVOLUTION5` dans `viz/_display.py` : `#e66101 #fdb863 #f7f7f7
   #b2abd2 #5e3c99`). Le skill `design-system-mi` (`SKILL.md`, `tokens.css`,
   `tokens.json`, `streamlit/custom.css`) est aligné sur ces valeurs, ainsi
   que sur la couleur « n.d. » (`#5F6368`), la couleur de classe zéro
   (`COULEUR_ZERO`) et l'échelle de score de bloc 0-100 %.
2. **Numéro d'ADR** : la proposition était numérotée 0007, numéro déjà pris par
   l'ADR du module Législatif ; elle devient 0014.

Les acquis J1-J4 sont conservés : affichage « n.d. », légendes de classement des
blocs par scrutin, mentions de licence, tableau « Sources, licences et dates » de
l'Accueil, fond de carte Plan IGN, classes fixes et classe « 0 », métriques
longues non tronquées.

## Alternatives considérées

- **Garder la v1 et ajuster** : ne répond pas à la demande d'une identité plus
  affirmée.
- **Garder Spectral pour les titres** : contredit la grammaire swiss
  (tout en grotesque) ; réintroductible pour les grands chiffres si besoin.
- **Reproduire la grille en quinconce dans toutes les pages** : impossible
  proprement avec `st.columns` ; réservée aux maquettes / à l'Accueil.

## Conséquences

- ✅ Identité distinctive, lisibilité accrue des chiffres (métriques en très grand corps).
- ✅ Aucun changement de données ni de logique ; compatibilité des tokens v1.
- ✅ Graphiques Plotly harmonisés sans toucher aux pages.
- ⚠️ Cartes Folium (iframe) et cellules de `st.dataframe` (canvas) non stylables en CSS — inchangées.
- ⚠️ Sélecteurs `data-testid` dépendants de Streamlit 1.57 : à revérifier à chaque montée de version.
- ↩️ Réversible : revenir au commit précédent de `custom.css`, `_theme.py`, `config.toml`.
