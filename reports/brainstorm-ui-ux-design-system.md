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

## 5. Exploration visuelle (2026-08-05)

Capture de l'app en cours d'exécution (`localhost:8501`, thème appliqué). Constat détaillé sur l'Accueil — les 4 autres pages restent à confirmer visuellement (analyse basée sur la lecture du code, section 1).

**Accueil (`app.py`)** — c'est le point le plus faible de l'app actuellement :
- Le contenu de la page est un écran de diagnostic technique (versions Streamlit/DuckDB/Polars, test DuckDB dans un expander, message "Stack opérationnelle") — utile en développement, mais ce n'est pas une page d'accueil pour un visiteur. Rien n'indique de quoi parle l'app tant qu'on n'a pas cliqué dans la sidebar.
- Pas de point d'entrée visuel vers les 4 modules (Géographie, Élections, Législatif, Économie) — juste une phrase texte "Utilisez le menu de navigation à gauche". Une vraie page d'accueil institutionnelle attendrait des cartes/tuiles cliquables résumant chaque module (chiffre clé + lien), à la manière du composant "data-box" du DSFR (§2).
- Le drapeau 🇫🇷 en emoji à côté du titre tranche avec le reste, plus sobre — cohérent avec la décision actée de basculer vers des icônes vectorielles (§4).
- Rien ne distingue visuellement "Accueil" des 4 pages fonctionnelles alors que son rôle (page de garde) est différent — pas de bandeau, pas de mise en avant.

**Géographie, Élections, Législatif, Économie** — capturées via Chrome (extension connectée). Un problème systémique ressort, plus grave que les incohérences de structure du §1 :

### Bug racine : `.streamlit/config.toml` forçait le thème sombre

`.streamlit/config.toml` existe bien (monté par `docker-compose.yml`), mais contenait `[theme]\nbase = "dark"` — un réglage antérieur au design system, resté en place. Notre `custom.css` force des fonds clairs sur les conteneurs via des sélecteurs `data-testid`, mais ne change rien à la résolution de thème interne de Streamlit — donc tout composant qui lit directement les variables de thème Streamlit (plutôt que le DOM stylé par notre CSS) restait en mode sombre, en clash total avec le reste de la page :

- **`st.dataframe`** (Géographie, tableau des régions) : le canvas `glide-data-grid` s'affiche entièrement en noir/blanc, alors que la page autour est claire.
- **`st.plotly_chart`** (Législatif, camemberts composition AN/Sénat) : fond noir. Cause précise : `st.plotly_chart(fig)` utilise par défaut `theme="streamlit"`, qui fait hériter le graphique du thème Streamlit résolu — donc sombre ici.
- **Texte des `st.radio` horizontaux** (Élections, ligne de sélecteurs Tour/Zone/Mode de carte) : quasi invisible, texte clair sur fond clair. Même mécanisme que le bug de contraste de la sidebar déjà corrigé (§ précédente) — sauf que celui-ci touche le contenu principal, pas seulement la sidebar.

Le correctif ponctuel déjà appliqué à la sidebar (forcer `color` en CSS avec `!important`) était un pansement, pas la résolution du problème racine. **Corrigé** : `.streamlit/config.toml` passé à `base = "light"` avec les couleurs du design system (`primaryColor = "#000091"`, `backgroundColor = "#f7f7f7"`, `secondaryBackgroundColor = "#ffffff"`, `textColor = "#242424"`) — ça corrige d'un coup le dataframe, les graphiques Plotly (`theme="streamlit"`) et les widgets natifs (radio, checkbox, etc.), sans CSS supplémentaire. À valider visuellement après redémarrage de l'app (nécessite un redémarrage complet du process Streamlit, pas juste un refresh navigateur — un changement de `[theme]` n'est pas pris en compte à chaud).

### Autre problème relevé

- **Troncature des labels de métriques** (Législatif, onglet Composition politique) : 6 colonnes de métriques ("Extrême gauche", "Gauche", "Divers", "Centre", "Droite", "Extrême droite") sont trop étroites pour leurs libellés — affichage coupé en "EXTRÊM...", "EXTRÊM D...". À revoir avec moins de colonnes ou des libellés raccourcis (EXG/GAU/DIV/CENT/DTE/EXD, cohérent avec la nomenclature déjà utilisée ailleurs dans le projet — cf. ADR-0005).

### Vérification technique des sélecteurs proposés par Gemini

Avant d'implémenter les CSS fournis par Gemini (voir `prompt-gemini-ui-ux-optimisation.md`), vérification directe dans le bundle JS de Streamlit 1.57.0 installé (`.venv/.../streamlit/static/`, recherche exhaustive sur les 241 fichiers statiques) :

| Sélecteur proposé par Gemini | Verdict | Réalité vérifiée |
|---|---|---|
| `[data-testid="stVerticalBlockBorderWrapper"]` | ⚠️ Absent du bundle 1.57.0 | N'existe dans aucun fichier statique de cette version — probablement un testid d'une version antérieure de Streamlit (discussions communautaires datées). À vérifier en DevTools au moment de l'implémentation plutôt que de faire confiance à ce nom. |
| `[data-testid="baseButton-secondary"]` | ❌ Incorrect | Le vrai format est `data-testid="stBaseButton-${variant}"` (préfixe `st` manquant dans la proposition de Gemini). |
| `[data-testid="stAppViewBlockContainer"]` | ❌ Incorrect | Le vrai testid du conteneur principal est `stMainBlockContainer` (classe `block-container` en complément). |
| `[data-testid="stMetric"]`, `stMetricValue`, `stMetricLabel`, `stSidebarNav` | ✅ Corrects | Confirmés à la fois dans le bundle et par capture live. |

Conclusion : les recommandations de fond de Gemini (structure, motion, iconographie Material Symbols, accessibilité) restent solides, mais certains extraits CSS ne sont pas fiables tels quels sur la version Streamlit du projet — à corriger avant implémentation.

## 6. Implémenté (2026-08-05)

Passe validée par Mathias, périmètre volontairement limité (pas de repositionnement des filtres — cf. §1/§4, gardé pour une itération séparée) :

- **Icônes Material Symbols Outlined** (police chargée dans `_theme.py::inject_css()`) à la place des emojis, sur les titres de page et le favicon (`page_icon=":material/xxx:"`).
- **Nouveau composant réutilisable** `_theme.py::render_page_header(icon, title, subtitle)` : remplace les `st.title`/`st.header` préfixés d'emoji sur les 5 pages, rend un H1 Spectral + icône + sous-titre cohérents.
- **Accueil refondu en hub** : bandeau titre + 4 tuiles cliquables (`st.page_link` dans `st.container(border=True)`) vers les modules, écran de diagnostic technique déplacé dans un `st.expander` en bas de page (gardé, utile en dev, plus mis en avant).
- **Micro-animations CSS** (tokens `--duration-*`/`--ease-*` déjà définis, enfin utilisés) : fade-in du contenu principal au chargement, hover-lift sur les cartes de synthèse et les métriques, feedback d'appui sur les boutons.
- **Style des cartes de synthèse** (`st.container(border=True)`) : sélecteur `[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]`, **vérifié par inspection DOM live** (pas par supposition) — cf. tableau §5, `stVerticalBlockBorderWrapper` n'existe pas dans cette version.

**Limitation architecturale découverte, non contournée dans cette passe** : dans le système classique `pages/` (celui utilisé par le projet), les icônes de la **sidebar de navigation** sont dérivées du nom de fichier (emoji dans le nom), pas de `st.set_page_config(page_icon=...)` — confirmé dans la documentation officielle Streamlit. Nos icônes Material s'appliquent donc au favicon et aux titres de page, mais pas à la sidebar (qui garde les emojis 📍🗳️🏛️📊). Basculer la sidebar en Material nécessiterait de migrer vers `st.navigation()` + `st.Page(icon=...)` — changement d'architecture de navigation plus profond, semi-irréversible sans redémarrage complet de l'app selon la doc Streamlit, à cadrer séparément si souhaité.

**Autre divergence relevée en cours de route** (non corrigée, hors périmètre) : les couleurs de nuances codées en dur dans `src/ministere_de_l_info/pages/legislatif.py` (`_COULEURS_BLOCS`, ex. `GAU = "#DD0000"`) ne correspondent pas aux tokens `--nuance-*` de `data-viz.css` (`--nuance-gau = "#e84c61"`) — confirme le risque déjà identifié en §3. À réconcilier dans un prochain passage (source unique de vérité pour les couleurs de nuances).

## Sources
- [Streamlit — App design concepts and considerations](https://docs.streamlit.io/develop/concepts/design)
- [10 Streamlit design tips for dashboards (Medium)](https://medium.com/data-science-collective/wait-this-was-built-in-streamlit-10-best-streamlit-design-tips-for-dashboards-2b0f50067622)
- [DSFR-chart (GouvernementFR)](https://github.com/GouvernementFR/dsfr-chart)
- [Système de Design de l'État](https://www.systeme-de-design.gouv.fr/)
- [DataJournalism.com — The Big Board for Election Results](https://datajournalism.com/read/handbook/one/case-studies/the-big-board-for-election-results)
- [Flourish — Visualize elections](https://flourish.studio/resources/elections/)
