# Skills et plugins existants — Pertinence pour ministere-de-l-info

## Skills GitHub directement utilisables
| Nom | URL | Ce que ça fait | Pertinence | Action requise |
| :--- | :--- | :--- | :--- | :--- |
| **data-wrangler-plugin** | [richard-gyiko/data-wrangler-plugin](https://github.com/richard-gyiko/data-wrangler-plugin) | Fournit des instructions pour l'analyse de fichiers CSV/Parquet/JSON en utilisant **DuckDB et Polars**. | Haute | Installer via `/plugin install` et examiner le code. |
| **bauplan-skills** | [bauplan-skills/plugins](https://github.com/bauplan-skills/plugins) | Contient des skills de pipelines de données (ex. `bauplan-data-pipeline/SKILL.md`) qui expliquent les compromis de performance entre Pandas, Polars, et DuckDB. | Haute | Installer pour guider l'agent dans le choix Polars vs DuckDB. |
| **Streamlit Core Skills** | [streamlit/streamlit](https://github.com/streamlit/streamlit) | L'équipe Streamlit maintient des skills (`.claude/skills/`) pour l'architecture, le debug, et l'implémentation de features sur Streamlit. | Haute | Copier `debugging-streamlit/SKILL.md` ou l'architecture pour aider l'agent sur l'UI. |

## Skills GitHub à adapter
| Nom | URL | Ce que ça fait | Adaptation nécessaire |
| :--- | :--- | :--- | :--- |
| **xetrack** | [xdssio/xetrack](https://github.com/xdssio/xetrack) | Recipes et skills pour le tracking d'expériences et l'utilisation de DuckDB. | À adapter pour qu'il cible spécifiquement notre pipeline ETL et l'extension spatial. |
| **Official Anthropic Skills** | [anthropics/skills](https://github.com/anthropics/skills) | Référentiel officiel. Contient des templates et des skills de manipulation de documents (CSV, XLSX). | Utiliser le dossier `template/` pour créer nos propres skills. |
| **sdmx-explorer** | [opensdmx](https://github.com/opensdmx) | Skill mentionnant l'accès aux données d'agences statistiques (INSEE, Bundesbank) via SDMX. | Modifier pour inclure les endpoints API spécifiques à l'INSEE et les formats locaux. |

## Plugins Antigravity pertinents
| Nom | URL | Ce que ça fait | Pertinence |
| :--- | :--- | :--- | :--- |
| **Data Agent Kit** | Antigravity Platform | Plugin complet pour l'orchestration ETL/ELT. Génère, teste et déploie des pipelines de données complexes. | Haute (pour automatiser nos tâches d'ingénierie de données). |
| **DuckDB MCP Server** | Marketplace MCP | Serveur Model Context Protocol permettant à l'agent de requêter directement la base DuckDB locale, comprendre le schéma et valider les requêtes. | Très Haute (indispensable pour l'interaction base de données). |
| **Web Search & Fetch MCP** | Marketplace MCP | Permet à l'agent de lire la documentation officielle à jour de Polars et Streamlit. | Moyenne (utile lors des mises à jour de librairies). |

## Skills à créer (non trouvés ou trop spécifiques)
- **Conventions de chargement données INSEE dans DuckDB du projet** : Il n'existe pas de skill open-source traitant des formats précis de l'INSEE (nomenclatures, codes communes, découpage géographique) couplés à l'extension `spatial` de DuckDB.
- **Schéma DuckDB du projet** : Un skill (ex: `schema-ministere/SKILL.md`) expliquant les tables existantes, les vues, et les conventions de nommage spécifiques à notre entrepôt de données.
- **Conventions de code spécifiques au projet** : L'utilisation de `uv` pour la gestion des paquets Python 3.12 et les normes de commits (Conventional Commits) nécessitent un skill global pour forcer l'agent à les respecter.
- **Optimisation Streamlit & Polars** : Un skill expliquant comment utiliser le `@st.cache_data` spécifiquement avec les lazyframes Polars ou les requêtes DuckDB pour éviter de surcharger la mémoire.
- **Visualisation Cartographique Folium/GeoPandas** : Un skill guidant l'agent sur la façon de convertir des requêtes DuckDB (avec données spatiales) vers des cartes Folium interactives dans Streamlit.

## Recommandations priorisées
1. **Installer le MCP DuckDB** : C'est la priorité numéro 1 pour que l'agent puisse "voir" les données et interagir avec la base locale de manière autonome.
2. **Créer le skill `chargement-insee`** : Développer un `SKILL.md` interne définissant les étapes de nettoyage (Polars) et d'ingestion (DuckDB) des données de l'INSEE.
3. **Installer et étudier `data-wrangler-plugin`** : L'utiliser comme base pour que l'agent génère des requêtes DuckDB et des transformations Polars efficaces.
4. **Adapter les skills `streamlit/streamlit`** : Les inclure dans le dossier `.claude/skills/` du projet pour accélérer le développement de l'interface utilisateur.
5. **Créer un skill d'optimisation UI (Streamlit + DuckDB)** : Documenter comment la donnée doit transiter de la base vers la visualisation (Folium) sans crash mémoire.
