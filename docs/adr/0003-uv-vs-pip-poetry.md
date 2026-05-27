# 0003 — uv plutôt que pip / poetry

Date : 2026-05-27
Statut : Accepté

## Contexte

Le projet nécessite un gestionnaire de paquets Python capable de :

- Résoudre et installer les dépendances de façon reproductible (lock file)
- Fonctionner rapidement en CI (les jobs GitHub Actions doivent rester sous 2 minutes)
- Gérer les groupes de dépendances (production vs dev)
- Fonctionner sans activation manuelle d'un virtualenv dans les commandes (`uv run`)

Les alternatives classiques sont `pip` (outil standard sans lock file natif), `poetry`
(gestionnaire complet mais lent et parfois capricieux sur les résolutions), et `uv`
(outil Astral, écrit en Rust, apparu en 2024).

## Décision

Utiliser `uv` comme gestionnaire de paquets unique. Toutes les commandes d'installation,
d'exécution et de lock sont préfixées `uv` ou `uv run`. `pip` et `poetry` sont
explicitement interdits dans `CLAUDE.md`.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|-----------------|
| **pip + requirements.txt** | Pas de lock file avec hashes, résolution non déterministe, pas de groupes dev/prod natifs, lenteur relative |
| **pip + pip-tools** | Meilleure résolution, mais deux outils à maintenir ; pas d'intégration `pyproject.toml` aussi fluide |
| **poetry** | Lock file solide, mais lenteur notoire (résolution SAT), conflits fréquents avec les virtualenvs système, binaire non portable |
| **conda / mamba** | Écosystème data science, pas adapté à un projet web Python pur ; gestion des channels complexe ; pas de lock file compatible PyPI |

## Conséquences

### Positives

- **Vitesse** : installation 10–100× plus rapide que pip/poetry (Rust, cache global, résolution parallèle)
- **`uv.lock`** : lock file déterministe avec hashes SHA256, reproductible en CI sans `--no-cache`
- **`uv run`** : exécution directe sans activation du venv (`uv run python`, `uv run pytest`, `uv run streamlit run app.py`)
- **`uv sync --frozen`** en CI : installation exacte du lock file, aucune résolution — rapide et fiable
- **Groupes de dépendances** : `[dependency-groups] dev = [...]` dans `pyproject.toml`, isolés de la prod
- **Binary unique** : pas de dépendance Python pour installer uv lui-même (`curl | sh` ou `brew install uv`)
- **Compatible `pyproject.toml` standard** : pas de format propriétaire

### Négatives

- **Outil récent (2024)** : moins de ressources communautaires que pip/poetry ; comportements edge case moins documentés
- **Non universel** : les contributeurs qui ne connaissent pas uv doivent l'installer (trivial, mais étape supplémentaire)
- **Pas de gestion des environnements Conda** : si une dépendance requiert des binaires natifs non disponibles sur PyPI, uv ne résout pas via conda-forge

### Réversibilité

Facile. `uv export --format requirements-txt` génère un `requirements.txt` compatible
pip. Un `pyproject.toml` standard est lisible par poetry ou pip-tools sans modification.
La décision de révision serait motivée par un bloquer sur un paquet non disponible sur
PyPI ou par une contrainte institutionnelle (conda imposé).
