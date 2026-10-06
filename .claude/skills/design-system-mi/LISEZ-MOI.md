# Design system Ministère de l'Info — v2 « direction éditoriale »

Ce dossier est un **skill Claude Code** : une fois copié dans le projet, Claude Code
le charge automatiquement dès qu'il travaille sur l'interface.

## Installation (une fois)

Copier ce dossier dans le projet, sous `.claude/skills/` :

```
ministere-de-l-info/
└── .claude/skills/design-system-mi/   ← ce dossier
    ├── SKILL.md
    ├── tokens.css
    ├── tokens.json
    ├── streamlit/   (custom.css, _theme.py, config.toml)
    └── reference/   (ADR-0014, aperçu)
```

Ou demander simplement à Claude Code :

> Copie le dossier `~/Documents/thème MI/design-system-mi` dans `.claude/skills/design-system-mi`
> du projet, puis applique le design system décrit dans son SKILL.md
> (si le patch `design-system-v2.patch` n'est pas encore appliqué, applique-le d'abord).

## Contenu

| Fichier | Rôle |
|---|---|
| `SKILL.md` | Les règles : principes, couleurs, typo, espacements, composants, usage Streamlit, rédaction, checklist. |
| `tokens.css` | Toutes les variables CSS, utilisables dans n'importe quelle page HTML. |
| `tokens.json` | Les mêmes valeurs en JSON (pour scripts, exports, autres outils). |
| `streamlit/` | Implémentation de référence pour l'app (identique au patch). |
| `reference/` | Décision (ADR-0014) et aperçu de l'accueil. |
