# 0002 — Streamlit plutôt que FastAPI + frontend JS

Date : 2026-05-27
Statut : Accepté

## Contexte

Le projet est une application de data-visualisation interactive développée par un
unique développeur (profil BTS NDRC, débutant en développement logiciel). L'objectif
est de produire des cartes, graphiques et tableaux à partir de données publiques
françaises, avec une interface navigateur utilisable sans compétences techniques.

Trois architectures étaient envisageables :

1. **Streamlit** — framework Python "full-stack" : le code Python génère directement
   l'interface, sans JavaScript ni API séparée
2. **FastAPI + React/Vue** — API REST côté serveur, frontend JavaScript séparé
3. **Dash (Plotly)** — alternative Python à Streamlit, plus configurable mais plus
   verbeuse

## Décision

Utiliser Streamlit comme unique couche d'interface. Aucune API REST n'est exposée ;
les pages Streamlit appellent directement DuckDB et les fonctions `viz/`.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|-----------------|
| **FastAPI + React** | Nécessite de maîtriser deux langages, deux dépôts (ou un monorepo), npm, des mécanismes d'authentification API, du CORS, du state management frontend. Complexité disproportionnée pour un usage local mono-utilisateur. |
| **Dash (Plotly)** | Syntaxe plus verbeuse que Streamlit pour les mêmes résultats. Moins adapté à l'intégration rapide de Folium / streamlit-folium. Écosystème de composants plus restreint. |
| **Jupyter Notebooks** | Non déployable comme application, pas d'interface reproductible, pas de navigation multi-pages. |
| **Application CLI seule** | Pas d'interactivité cartographique, pas de filtres dynamiques. |

## Conséquences

### Positives

- **Productivité maximale** : un seul fichier Python par page, pas de HTML/CSS/JS à écrire
- **Rechargement automatique** en développement (hot reload natif Streamlit)
- **Intégration immédiate** de Folium, Plotly, GeoPandas via les composants Streamlit
- **Courbe d'apprentissage minimale** : un débutant peut lire et modifier une page Streamlit
- **`@st.cache_data` / `@st.cache_resource`** pour la mise en cache des requêtes lourdes sans infrastructure externe
- **Déployable sur OrbStack / Docker** avec un simple `streamlit run app.py`

### Négatives

- **Streamlit relance le script entier à chaque interaction** : tout chargement lourd doit être derrière `@st.cache_data` ou `@st.cache_resource`, sinon l'UX est dégradée
- **Pas d'API REST exposable** : si un futur module doit alimenter un service externe ou une app mobile, il faudra ajouter FastAPI
- **Limitations d'interactivité** : les cas avancés (formulaires multi-étapes, interactions JS custom, websockets temps réel) sont difficiles à implémenter proprement
- **Mono-thread par défaut** : pas adapté si plusieurs utilisateurs accèdent simultanément (non pertinent en usage local)

### Réversibilité

Partielle. La couche `viz/maps.py` et les modules `data_sources/` sont indépendants
de Streamlit — ils pourraient être réutilisés derrière une API FastAPI. Les fichiers
`pages/*.py` seraient à réécrire en endpoints et composants frontend. La décision de
révision serait motivée par un besoin d'API publique ou de déploiement multi-utilisateur.
