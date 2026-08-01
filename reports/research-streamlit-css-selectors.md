# Sélecteurs CSS Streamlit — version 1.57.0

## Version Streamlit du projet
La version utilisée dans le projet `ministere-de-l-info` (définie dans `uv.lock`) est **Streamlit 1.57.0**.

## Sélecteurs par composant (table exhaustive)

L'approche moderne et recommandée pour cibler les éléments dans Streamlit consiste à utiliser les attributs `data-testid`, car les classes classiques (ex: `st-emotion-cache-123xyz`) sont générées dynamiquement et changent d'une version à l'autre.

| Composant | Sélecteur CSS (`data-testid` ou classe) | Notes |
| :--- | :--- | :--- |
| **NAVIGATION / SIDEBAR** | | |
| Conteneur sidebar principal | `[data-testid="stSidebar"]` | Englobe tout le panneau latéral. |
| Liens de navigation des pages| `[data-testid="stSidebarNav"]` | Conteneur de la liste des liens de navigation. |
| Lien individuel | `[data-testid="stSidebarNavLink"]` | Chaque lien de page dans la sidebar. |
| Lien actif/sélectionné | `[data-testid="stSidebarNavLink"][aria-current="page"]` | Streamlit utilise ARIA pour indiquer la page active. |
| Logo/titre de l'app | `[data-testid="stSidebarHeader"]` ou `[data-testid="stLogoSpacer"]` | Zone supérieure de la sidebar réservée au logo. |
| **HEADERS / TITRES** | | |
| Titres génériques | `[data-testid="stHeading"]` | Commun à `st.title`, `st.header`, `st.subheader`. |
| `st.header()` | `[data-testid="stHeading"] h2` | Pour cibler précisément le tag HTML généré. |
| `st.subheader()` | `[data-testid="stHeading"] h3` | Pour cibler précisément le tag HTML généré. |
| `st.title()` | `[data-testid="stHeading"] h1` | Pour cibler précisément le tag HTML généré. |
| **MÉTRIQUES** | | |
| Conteneur `st.metric()` | `[data-testid="stMetric"]` | Conteneur global de la métrique. |
| Valeur principale | `[data-testid="stMetricValue"]` | Le grand chiffre affiché. |
| Delta (hausse/baisse) | `[data-testid="stMetricDelta"]` | La petite valeur de changement en vert/rouge. |
| Label de la métrique | `[data-testid="stMetricLabel"]` | Le titre de la métrique. |
| **BOUTONS / CONTRÔLES** | | |
| `st.button()` | `[data-testid="stButton"]` | Conteneur. Le bouton lui-même est un `<button>`. |
| `st.selectbox()` | `[data-testid="stSelectbox"]` | Conteneur. L'input peut être ciblé en descendant dans le DOM. |
| `st.radio()` | `[data-testid="stRadio"]` | Conteneur de la liste de choix radio. |
| `st.tabs()` | `[data-testid="stTabs"]` | Conteneur englobant l'ensemble des onglets. |
| Tab bouton | `[data-testid="stTab"]` | Le bouton cliquable de l'onglet. |
| Tab actif | `[data-testid="stTab"][aria-selected="true"]` | L'onglet actuellement sélectionné. |
| **DATAFRAME** | | |
| `st.dataframe()` | `[data-testid="stDataFrame"]` | Conteneur global (et sa barre d'outils `stElementToolbar`). |
| En-têtes de colonnes | *Inaccessible en CSS* | Voir section "Limitations connues". |
| **LAYOUT** | | |
| Page principale (fond) | `[data-testid="stAppViewContainer"]` ou `[data-testid="stMain"]` | Utile pour changer le fond global de l'app. |
| Colonnes (`st.columns()`) | `[data-testid="stColumn"]` | Contenues dans un parent `[data-testid="stHorizontalBlock"]`. |
| `st.expander()` | `[data-testid="stExpander"]` | Conteneur principal. |
| Contenu expander | `[data-testid="stExpanderDetails"]` | La div qui contient les éléments une fois déplié. |
| **CALLOUTS** | | |
| `st.info()` | `[data-testid="stAlertContentInfo"]` | Message d'information (bleu par défaut). |
| `st.warning()` | `[data-testid="stAlertContentWarning"]` | Message d'avertissement (jaune par défaut). |
| `st.success()` | `[data-testid="stAlertContentSuccess"]` | Message de succès (vert par défaut). |
| `st.error()` | `[data-testid="stAlertContentError"]` | Message d'erreur (rouge par défaut). |
*(Note : tous les callouts sont également enveloppés dans un conteneur générique `[data-testid="stAlert"]`)*.

## Changements récents à surveiller
*   **L'attribut `key` devient un standard de classe CSS :** Dans les versions récentes de Streamlit (incluant la 1.57.0), si vous définissez un argument `key` sur un widget (ex: `st.button("Envoyer", key="btn_submit")`), Streamlit génère automatiquement une classe CSS correspondante : `.st-key-btn_submit`. **C'est la méthode recommandée pour cibler un composant spécifique de manière robuste**, plutôt que d'utiliser `:nth-child()` ou des sélecteurs complexes.
*   Les classes CSS internes (de type `st-emotion-cache-1r4qj8v`) sont générées dynamiquement. Elles changent à chaque redémarrage ou mise à jour mineure de Streamlit. Il ne faut **jamais** les utiliser pour du styling pérenne.

## Projets de référence (theming CSS Streamlit)
Plusieurs projets Open Source illustrent les meilleures pratiques de theming avancé (combiné avec `config.toml`) :
1.  **[microsoft/Streamlit_UI_Template](https://github.com/microsoft/Streamlit_UI_Template)** : Excellent template montrant comment structurer l'injection CSS proprement dans une application d'entreprise.
2.  **[jmedia65/awesome-streamlit-themes](https://github.com/jmedia65/awesome-streamlit-themes)** : Catalogue de thèmes Streamlit configurés prêts à l'emploi.
3.  **[Paldom/streamlit-custom-style](https://github.com/Paldom/streamlit-custom-style)** : Démontre l'encapsulation de styles et l'utilisation de sélecteurs avancés pour surcharger les éléments sans casser le layout responsif.

## Limitations connues
*   **Dataframes & `<canvas>` HTML5 :** Depuis la mise à jour vers `glide-data-grid`, les dataframes (`st.dataframe` et `st.data_editor`) sont dessinés directement dans un élément `<canvas>` (identifié par `[data-testid="data-grid-canvas"]`). Par conséquent, **les cellules individuelles, les lignes et les en-têtes de colonnes n'existent pas dans le DOM HTML**. Il est donc **impossible** de les styliser en CSS (pas de changement de couleur de police, bordures, etc., via CSS). Le styling doit se faire via les options natives (ex: l'objet pandas Styler).
*   **Encapsulation et iframes :** Les composants personnalisés (Streamlit Components créés par la communauté, comme `streamlit-folium`) sont souvent encapsulés dans des `<iframe>`. Le CSS injecté dans l'application principale via `st.markdown("<style>...</style>")` ne se propagera pas à l'intérieur de l'iframe à cause des restrictions de sécurité du navigateur.
*   **Sélecteurs combinés :** Différencier deux `st.header` ou `st.subheader` (qui partagent tous deux `[data-testid="stHeading"]`) demande d'utiliser le pseudo-sélecteur CSS `:has()` ou `.st-key-xxx` si applicable, car les éléments titres n'acceptent pas de paramètre `key`.
