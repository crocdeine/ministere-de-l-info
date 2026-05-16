---
name: latex-rapport-fr
description: Génération de rapports LaTeX professionnels en français selon la charte orthotypographique du Journal officiel (DILA, 2021). Couvre le préambule type avec babel/siunitx/biblatex, les règles d'écriture (guillemets, abréviations, majuscules, exposants, dates, heures), les graphies officielles des départements et régions, la structure des annexes et notes, et le workflow Jinja2 → Tectonic → PDF.
---

# Rapports LaTeX en français (charte JORF)

Source de référence : **Charte orthotypographique du Journal officiel — Lois et décrets** (Direction de l'information légale et administrative, Janvier 2021). PDF archivé dans `references/typographie/2021-01_DILA_charte-orthotypographique-JORF.pdf`.

Cette charte est le référentiel typographique de l'État français. Tous les rapports générés doivent la respecter pour un rendu administratif et académique conforme.

## 1. Préambule LaTeX type

Document de base pour rapports analytiques :

```latex
\documentclass[a4paper,11pt,french]{article}

% Encodage et langue
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{csquotes}

% Mise en page
\usepackage[a4paper,margin=2.5cm,headheight=14pt]{geometry}
\usepackage{fancyhdr}
\usepackage{setspace}

% Tableaux et figures
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{tabularx}
\usepackage{array}
\usepackage{graphicx}
\usepackage{float}

% Nombres et unités (CRITIQUE : locale FR)
\usepackage{siunitx}
\sisetup{
  locale = FR,
  group-separator = {\,},
  output-decimal-marker = {,},
  group-minimum-digits = 4,
  detect-all
}

% Couleurs et graphiques
\usepackage{xcolor}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

% Bibliographie
\usepackage[backend=biber,style=authoryear-comp,sorting=nyt,language=french]{biblatex}

% Listes
\usepackage{enumitem}
\setlist{nosep,leftmargin=*}

% Liens (TOUJOURS en dernier dans le préambule)
\usepackage[hidelinks,colorlinks=false,pdfencoding=auto]{hyperref}

% Métadonnées PDF
\hypersetup{
  pdftitle={Titre du rapport},
  pdfauthor={Auteur},
  pdfsubject={Rapport analytique},
  pdfkeywords={politique, élections, France}
}
```

## 2. Règles typographiques fondamentales

### 2.1 Guillemets (3 niveaux)

- **Niveau 1** : guillemets français « ... » avec **espace insécable** à l'intérieur
- **Niveau 2** : guillemets anglais "..."
- **Niveau 3** : retour aux français « ... »

En LaTeX, utiliser `csquotes` :
```latex
\enquote{Citation niveau 1 avec \enquote{niveau 2 imbriqué}}
```

### 2.2 Espaces insécables (CRITIQUES)

À placer **avant** :
- les deux-points `:`
- les point-virgules `;`
- les points d'interrogation `?`
- les points d'exclamation `!`
- l'unité dans `52,3 %` ou `12 kg`
- l'année dans `n° 2026-1303`

Babel français gère automatiquement les espaces avant `;:?!`. Pour les autres cas, utiliser `~` ou `\,` (espace fine).

### 2.3 Nombres, durées, heures

- **Décimale** : virgule, jamais point → `12,5` et non `12.5`
- **Séparateur de milliers** : espace insécable → `12 345` et non `12,345` ou `12.345`
- **Pourcentages** : `52,3 %` avec espace insécable (utiliser `\SI{52.3}{\percent}` avec siunitx)
- **Heures** : `12 h 30`, `13 h` (h sans point, abréviation conventionnelle)
- **Durées** : en chiffres → "5 ans", "2 ans 3 mois"
- **Âges** : en lettres → "trente ans" (cas particulier)
- **Numéros de page/référence** : pas d'espace → `Page 3258`, `n° 00152358942`

### 2.4 Abréviations

**Grammaticales** (point à la place d'une voyelle) :
- `art.` (article), `chap.` (chapitre), `fig.` (figure), `vol.` (volume), `parag.` (paragraphe)

**Conventionnelles** (sans point) :
- `bd` (boulevard), `fg` (faubourg), `h` (heure), `m` (mètre), `kg` (kilogramme)
- `av.` (avenue) — exception avec point

**Civilités** :

| Singulier | Abrév. | Pluriel | Abrév. |
|---|---|---|---|
| Monsieur | M. | Messieurs | MM. |
| Madame | Mme | Mesdames | Mmes |
| Professeur | Pr | Professeurs | Prs |
| Docteur | Dr | Docteurs | Drs |
| Maître | Me | Maîtres | Mes |

⚠️ "Mademoiselle/Mlle" n'a plus court dans les textes administratifs (circulaire n° 5121/SG du 16/12/2005).

### 2.5 Acronymes et sigles

- **Toujours en majuscules sans points** : SNCF, INSEE, AFNOR, INSERM
- **Développé** : majuscule au premier mot, minuscules ensuite
  - `Société nationale des chemins de fer (SNCF)`
  - `Institut national de la statistique et des études économiques (INSEE)`

### 2.6 Exposants

- `1er` (premier), **jamais** `1ier`
- `2e` (deuxième), **jamais** `2ème` ou `2ième`
- `XVIIIe siècle`, `XXe siècle` — siècles en **petites majuscules** romaines

En LaTeX : `1\textsuperscript{er}`, `2\textsuperscript{e}`, ou `\ier`, `\ieme` avec le package babel français.

### 2.7 Majuscules et minuscules

**Entités à échelle nationale** → majuscule initiale :
- `Le Président de la République` (mais : "la présidence de la République")
- `Le Gouvernement`
- `Le Premier ministre` (Premier en majuscule, ministre en minuscule)
- `Le Collège de France`, `l'Institut`, `l'Académie`

**Décorations** :
- `ordre national du Mérite`
- `croix de chevalier de la Légion d'honneur`
- `Croix de guerre`, `Palmes académiques`

**À mettre EN MINUSCULES (erreurs fréquentes)** :
- `ministre de l'agriculture` (et non "Ministre de l'Agriculture")
- `ministère du logement`
- `maire`, `préfet`, `direction`, `délégation`
- `code` (le code civil, le code électoral)
- `licence`, `master`, `doctorat`

**Points cardinaux** :
- **Adjectif** → minuscule : `latitude sud`, `Atlantique nord`
- **Nom propre géographique** → majuscule : `pôle Nord`, `département du Nord`
- **Direction** → minuscule : `vent du sud`, `direction nord-est`
- **Nom propre** → majuscule : `gare du Nord`, `mer du Nord`

### 2.8 Titres d'œuvre

En **italique** avec majuscule initiale :
- *La Légende des siècles* de Victor Hugo
- *Le Monde*, *Libération*

### 2.9 Trait d'union et tiret cadratin

- **Trait d'union `-`** : mots composés (`procès-verbal`), noms de voies (`rue du Général-de-Gaulle`), noms géographiques (`Lot-et-Garonne`)
- **Tiret cadratin `—`** : énumérations, incises, liaisons (`Paris—New York` aérien)
- **Tiret d'incise `–`** : proposition indépendante (`Le préfet — en accord avec les autorités — détermine...`)

## 3. Graphies officielles des territoires

### 3.1 Régions (13 actuelles)

`Auvergne-Rhône-Alpes`, `Bourgogne-Franche-Comté`, `Bretagne`, `Centre-Val de Loire`, `Corse`, `Grand Est`, `Guadeloupe`, `Guyane`, `Hauts-de-France`, `Ile-de-France` (sans accent sur le I capital selon JORF), `La Réunion`, `Martinique`, `Mayotte`, `Normandie`, `Nouvelle-Aquitaine`, `Occitanie`, `Pays de la Loire`, `Provence-Alpes-Côte d'Azur`.

### 3.2 Articles d'usage des départements (extraits critiques)

| Département | Article |
|---|---|
| Ain, Aisne, Allier, Ardèche, Ariège, Aube, Aude, Aveyron | de l' |
| Alpes-de-Haute-Provence, Hautes-Alpes, Alpes-Maritimes, Ardennes, Bouches-du-Rhône | des |
| Calvados, Cantal, Cher, Doubs, Finistère, Gard, Gers, Jura, Loiret, Lot, Morbihan, Nord, Pas-de-Calais, Puy-de-Dôme, Bas-Rhin, Haut-Rhin, Rhône, Tarn, Var, Territoire de Belfort, Val-de-Marne, Val-d'Oise | du |
| Charente, Charente-Maritime, Corrèze, Corse-du-Sud, Haute-Corse, Côte-d'Or, Creuse, Dordogne, Drôme, Haute-Garonne, Gironde, Loire, Haute-Loire, Loire-Atlantique, Lozère, Manche, Marne, Haute-Marne, Mayenne, Meuse, Moselle, Nièvre, Sarthe, Savoie, Haute-Savoie, Seine-Maritime, Somme, Vendée, Vienne, Haute-Vienne, Seine-Saint-Denis, Guadeloupe, Martinique, Guyane | de la |
| Côtes-d'Armor, Landes, Pyrénées-Atlantiques, Hautes-Pyrénées, Pyrénées-Orientales, Yvelines, Deux-Sèvres, Vosges, Hauts-de-Seine | des |
| Eure-et-Loir, Ille-et-Vilaine, Indre-et-Loire | d' |
| Loir-et-Cher, Lot-et-Garonne, Maine-et-Loire, Meurthe-et-Moselle, Paris, Saône-et-Loire, Seine-et-Marne, Tarn-et-Garonne, Vaucluse, La Réunion, Mayotte | de |
| Essonne, Oise, Orne, Yonne | de l' |
| Hérault, Indre, Isère | de l' |

⚠️ Erreurs fréquentes : "le préfet de Vaucluse" (et non "du Vaucluse"), "département de Lot-et-Garonne" (et non "du Lot-et-Garonne"), "préfet du Cher" (et non "de Cher").

### 3.3 Collectivités et territoires d'outre-mer

`Nouvelle-Calédonie`, `Polynésie française`, `Saint-Pierre-et-Miquelon`, `Wallis-et-Futuna`, `Terres australes et antarctiques françaises`, `Saint Barthélemy`, `Saint-Martin`.

## 4. Structure d'un rapport type

### 4.1 Articles dans le corps du texte

- En début d'alinéa : `Art. 1er. -`, `Art. 2. -`
- Entre parenthèses : `(chap. III, art. 3)`
- Dans une annexe ou un code : `Article 3` (centré, au long, en romain)

### 4.2 Annexes

- Une seule annexe : `ANNEXE` (en majuscules, centré, avant le contenu)
- Plusieurs annexes : `ANNEXES` (en italique majuscules) puis `ANNEXE I`, `ANNEXE II`...
- Si titre : le centrer en majuscules en dessous de `ANNEXE`

### 4.3 Listes énumératives

- **En tiret** : initiale minuscule, point-virgule en fin, point final pour le dernier item
- **En numéro** (`1°`, `2°`, `3°`) : initiale majuscule, même ponctuation
- **En lettres** (`a)`, `b)`, `c)`) : initiale majuscule, même ponctuation

### 4.4 Notes et nota

- **Notes** : numérotées en chiffres, regroupées en fin de texte, appel collé au texte (avant ponctuation)
- **Nota** : non numérotés, mot `Nota` en italique (locution latine)

### 4.5 Signatures

Ordre protocolaire strict : Président de la République et Premier ministre en tête, puis ministre porteur de l'acte, autres ministres, secrétaires d'État.

## 5. Workflow génération Jinja2 → Tectonic → PDF

### 5.1 Template Jinja2 avec délimiteurs custom

LaTeX utilise `{` et `}`, conflit avec Jinja2 par défaut. Configurer Jinja2 avec délimiteurs custom :

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader("reports/templates"),
    block_start_string="((*",
    block_end_string="*))",
    variable_start_string="(((",
    variable_end_string=")))",
    comment_start_string="((#",
    comment_end_string="#))",
    trim_blocks=True,
    autoescape=False,
)

# Filtre custom pour échapper les caractères LaTeX spéciaux
def latex_escape(s: str) -> str:
    if not isinstance(s, str):
        return s
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return s

env.filters["tex"] = latex_escape
```

### 5.2 Compilation avec Tectonic

```python
import subprocess
from pathlib import Path

def compile_latex(tex_path: Path) -> Path:
    """Compile un .tex en .pdf via Tectonic. Retourne le chemin du PDF."""
    result = subprocess.run(
        ["tectonic", "--keep-logs", "--keep-intermediates", str(tex_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Tectonic a échoué : {result.stderr}")
    return tex_path.with_suffix(".pdf")
```

### 5.3 Empaquetage ZIP

Le livrable final contient :
- `rapport.tex` (source LaTeX)
- `rapport.pdf` (rendu)
- `figures/*.pdf` ou `*.png` (illustrations)
- `biblio.bib` (bibliographie si présente)
- `README.md` (métadonnées : date génération, version skill, sources)

## 6. Citations de sources dans le rapport

Format obligatoire pour chaque donnée :

```latex
\footnote{Source : \emph{Ministère de l'Intérieur} via \href{https://www.data.gouv.fr/datasets/donnees-des-elections-agregees}{data.gouv.fr}, mis à jour le \today.}
```

Pour les nuances politiques : toujours citer la circulaire applicable :
```latex
\footnote{Nuances attribuées selon la circulaire \emph{NOR INTP2602966C} du 2 février 2026 (Ministère de l'Intérieur).}
```

## 7. Pièges fréquents

- **Apostrophe** : utiliser `'` (apostrophe courbe) et non `'` (apostrophe droite) dans le texte affiché → en LaTeX, taper `'` suffit, le rendu est automatique
- **Espaces avant ponctuation** : ne pas oublier, babel français les ajoute automatiquement mais surveiller les nombres et %
- **Majuscules accentuées** : `É`, `À`, `È` doivent être accentuées (sauf textes 100 % majuscules). En LaTeX : `\'E`, `\`A`, `\`E`
- **Sigle** : pas de points entre les lettres (`SNCF` et non `S.N.C.F.`)
- **Pléonasme** : ne jamais écrire `etc...` (toujours `etc.` seul)
- **URL et adresses mél** : conserver la casse exacte, pas de règles typographiques classiques. Mettre en note de bas de page si longue.
- **Numéro/dito** : `n° 1230` (et non `No 1230`), pluriel `nos` (et non `n°s`) — utiliser le "o" en exposant, pas le symbole degré

## 8. Sortie attendue pour un rapport politique

Un rapport généré doit minimalement contenir :
1. Page de titre (titre, sous-titre, auteur/organisation, date)
2. Sommaire automatique (`\tableofcontents`)
3. Introduction
4. Sections analytiques avec figures et tableaux
5. Conclusion
6. Annexes (méthodologie, sources détaillées, tableaux complémentaires)
7. Bibliographie via biblatex (`\printbibliography`)
8. Notes de bas de page systématiques pour les sources
