# Design system v2 — direction éditoriale

> **Remplacé par** [`ui-design-system-v2-2026-10-06.md`](ui-design-system-v2-2026-10-06.md) : patch appliqué sur la base J1-J4 ; l'ADR « 0007 » cité ici est devenu l'ADR-0014, et la palette d'évolution RdYlGn est remplacée par la palette accessible PuOr (décision J3).

**Date** : 2026-10-04
**Périmètre** : application du canvas Claude Design « Ministère de l'Info — Direction éditoriale » à l'app Streamlit
**Statut** : 🟡 Implémenté, en attente de validation visuelle (ADR-0007 « Proposé »)
**Branche** : `feat/ds-direction-editoriale`

---

## Synthèse

Nouvelle direction visuelle inspirée d'une grammaire swiss/éditoriale : noir et
blanc, grotesque très gras en capitales, filets d'un pixel, aucune ombre, Bleu
France réservé à l'action. Palettes de données inchangées. Décision : ADR-0007.

## Fichiers

| Fichier | Changement |
|---|---|
| `src/ministere_de_l_info/custom.css` | Réécrit. Tokens v2 (`--ink`, `--paper`, `--rule`, échelle typographique `clamp()`), alias v1 conservés. Couche Streamlit : sidebar en liste capitales (page active = encre pleine), titres H1/H2/H3 en capitales (H2 précédé d'un filet), métriques sans carte (filet + chiffre 900), boutons contour/encre (survol Bleu France, export CSV en Bleu France), champs soulignés, onglets capitales, alertes sans fond coloré, cartes `st.container(border=True)` = filet au-dessus. |
| `src/ministere_de_l_info/_theme.py` | Police Spectral retirée, Hanken Grotesk 900 ajoutée. `render_page_header()` : sur-titre + titre géant + sous-titre décalé avec flèche ↘ (paramètres `eyebrow`, `display`, HTML échappé). Nouveau `render_overline()`. Template Plotly `mdi` activé par défaut dans `inject_css()`. |
| `.streamlit/config.toml` | Fond `#ffffff`, fond secondaire `#f2f2f2`, texte `#0a0a0a`. |
| `pages/0_🏠_Accueil.py` | Titre display, modules numérotés « 01 — » à « 04 — », ligne de sources. |
| `tests/test_theme.py` | 7 tests (tokens, alias v1, absence d'`@import`, polices, template Plotly, échappement HTML). |
| `docs/adr/0007-…` + index | ADR de la décision. |

## Vérification

- `ruff format --check` / `ruff check` : propres sur `src`, `pages`, `app.py`, `tests/test_theme.py`.
- `pytest tests/test_theme.py` : 7/7.
- Suite complète exécutée dans un environnement **sans base ni réseau** : résultats identiques avant / après le changement (les échecs viennent de l'absence de DB / d'accès réseau, pas du thème). **À relancer sur le Mac mini** avec la base.
- Rendu Accueil vérifié en navigateur headless (1440 px et 390 px).

## À faire (validation Mathias)

1. Lancer `uv run streamlit run app.py` et parcourir les 5 pages.
2. Points à regarder : lisibilité des métriques en 6 colonnes (Législatif), graphiques Plotly avec le nouveau template, contraste des légendes.
3. Si validé : ADR-0007 → « Accepté », PR squash-merge.
