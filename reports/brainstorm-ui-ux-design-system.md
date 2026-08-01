# Brainstorm UI/UX — passer du prototype fonctionnel à une app soignée

Date : 2026-08-01
Contexte : le design system (tokens CSS) est posé et injecté sur les 5 pages. Objectif de cette note : dépasser le thème seul et cadrer l'UI/UX de l'app dans son ensemble, maintenant que les modules fonctionnels (Géographie, Élections, Législatif, Économie) sont en place mais ont été construits page par page sans convention transversale.

## 1. Diagnostic — état actuel

Inventaire des patterns UI réellement utilisés (lecture de `pages/` et `src/ministere_de_l_info/pages/`) :

| Page | Filtres | Structure | `set_page_config` |
|---|---|---|---|
| Accueil (`app.py`) | — | Titre, métriques stack, alertes | Oui |
| Géographie | Sidebar (niveau, année, comparaison, département, région, mode) | Carte → métadonnée → tableau | Oui |
| Élections | Inline (dans chaque onglet) | 3 onglets (Présidentielles/Législatives/Municipales), carte + tableau par onglet | Oui |
| Législatif | Inline | 4 onglets (composition, élus, activité, évolution) | **Non** |
| Économie | Inline (`st.columns` pour indicateur + année) | 4 onglets (carte, évolution, croisement, industrie) + expander drill-down | **Non** |

Trois incohérences concrètes ressortent, indépendamment du thème :

1. **Filtres à deux endroits différents** : Géographie utilise la sidebar de façon extensive, les 3 autres pages mettent tous les filtres inline en haut du contenu. Un utilisateur qui navigue entre pages doit réapprendre où chercher les contrôles à chaque fois.
2. **`st.set_page_config` absent sur 2 pages sur 4** (Législatif, Économie) — l'onglet du navigateur affiche le titre par défaut Streamlit au lieu de "Législatif" / "Économie", et le `layout="wide"` n'est pas garanti.
3. **Pas de composant de synthèse réutilisable** : chaque page réinvente sa mise en page (métriques, cartes, tableaux) sans fonction commune — la cohérence visuelle qu'on vient d'apporter via `custom.css` reste donc fragile : le prochain onglet ajouté a de bonnes chances de repartir sur un pattern différent si rien ne structure ça au niveau du code.

## 2. Ce que dit la recherche

**DSFR (Système de Design de l'État)** — le projet emprunte déjà sa palette officielle (Bleu France, Rouge Marianne). Le DSFR a une extension dédiée à la dataviz, [dsfr-chart](https://github.com/GouvernementFR/dsfr-chart) (composants Vue, donc pas réutilisable telle quelle en Streamlit, mais le vocabulaire et les patterns sont transposables) : cartes de France par région/département, jauges, et surtout un composant **"data-box"** — un bloc de synthèse chiffrée en tête de page, avant le détail. Le DSFR documente aussi une mise en page "optimisée pour la lecture de données" : titre → bloc de synthèse → visualisation → détail tabulaire. C'est exactement le pattern déjà utilisé sur Géographie — à généraliser aux 3 autres pages.

**Bonnes pratiques Streamlit (dashboards pro)** — deux recommandations qui recoupent le diagnostic ci-dessus :
- Minimalisme progressif : la page doit répondre à la question principale immédiatement (un chiffre clé, une carte), le détail va derrière des `expander`/`tabs`, pas à plat.
- Le choix sidebar vs barre horizontale pour les filtres est un vrai arbitrage UX, pas un détail : la sidebar encaisse plus de filtres sans surcharge visuelle, mais les utilisateurs la remarquent moins (elle est perçue comme "hors sujet" par rapport au contenu principal) — d'où l'intérêt de réserver la sidebar aux filtres qui structurent toute la page (niveau territorial, période) et de garder en inline les filtres secondaires/contextuels à un onglet précis.
[Streamlit design docs](https://docs.streamlit.io/develop/concepts/design) · [tips dashboards pro](https://medium.com/data-science-collective/wait-this-was-built-in-streamlit-10-best-streamlit-design-tips-for-dashboards-2b0f50067622)

**Dashboards électoraux (data journalism)** — le motif qui revient systématiquement : carte → clic/sélection → détail (drill-down), avec un minimum de clics. Le "Drill-down commune" déjà présent dans Économie va dans ce sens ; il vaudrait la peine de généraliser ce geste (sélectionner une entité sur la carte ou dans le tableau → voir son détail) plutôt que de le traiter au cas par cas par page.
[Datajournalism.com — Big Board](https://datajournalism.com/read/handbook/one/case-studies/the-big-board-for-election-results) · [Flourish — visualiser des élections](https://flourish.studio/resources/elections/)

## 3. Pistes concrètes (par ordre d'impact / effort)

**Rapide, faible effort :**
- Ajouter `st.set_page_config` sur Législatif et Économie (incohérence pure, aucune décision requise).
- Généraliser le pattern déjà présent sur Géographie : titre + sous-titre → filtres → contenu → métadonnée source → tableau détaillé, sur les 3 autres pages.

**Effort moyen, gain de cohérence fort :**
- Extraire un composant Python réutilisable pour la "metric row" (les `st.metric` en tête de page), avec le style déjà défini dans `custom.css` (`[data-testid="stMetric"]`) — évite que chaque page réinvente sa disposition.
- Trancher une convention filtres unique (sidebar pour les filtres qui structurent toute la page type niveau territorial/période, inline pour le contextuel à un onglet) et l'appliquer aux 4 pages.
- Vérifier que la palette de nuances politiques (`--nuance-*` dans `data-viz.css`) est bien la même source que celle codée dans `schema_elections.py` / `_display.py` (risque de divergence à deux endroits).

**Structurant, à cadrer avant de généraliser :**
- Un pattern de drill-down commun (sélection sur carte/tableau → détail), au lieu d'un `expander` ad hoc par page.
- Décision éditoriale sur les emojis (🇫🇷📍🗳️🏛️📊) en titres/icônes de nav : les garder (lisible, décontracté) ou basculer vers des icônes vectorielles cohérentes avec le ton "institutionnel" du design system.

## 4. Décisions actées (validées par Mathias, 2026-08-01)

- **Filtres** : convention mixte — sidebar pour les filtres qui structurent toute la page (niveau territorial, période), inline pour le contextuel à un onglet précis. À appliquer progressivement lors de l'uniformisation des 4 pages.
- **Icônes** : bascule des emojis vers des icônes vectorielles pour un rendu plus institutionnel. Reste à choisir la librairie/police d'icônes et le point d'intégration (nav sidebar + titres de page) — chantier distinct, pas encore cadré.
- **Priorité immédiate** : uniformiser l'existant avant de construire de nouveaux composants. Première passe : `st.set_page_config` ajouté sur Législatif et Économie (fait, cf. commit à venir). Reste à généraliser la structure titre/filtres/contenu/table sur Élections, Législatif, Économie.

## Sources
- [Streamlit — App design concepts and considerations](https://docs.streamlit.io/develop/concepts/design)
- [10 Streamlit design tips for dashboards (Medium)](https://medium.com/data-science-collective/wait-this-was-built-in-streamlit-10-best-streamlit-design-tips-for-dashboards-2b0f50067622)
- [DSFR-chart (GouvernementFR)](https://github.com/GouvernementFR/dsfr-chart)
- [Système de Design de l'État](https://www.systeme-de-design.gouv.fr/)
- [DataJournalism.com — The Big Board for Election Results](https://datajournalism.com/read/handbook/one/case-studies/the-big-board-for-election-results)
- [Flourish — Visualize elections](https://flourish.studio/resources/elections/)
