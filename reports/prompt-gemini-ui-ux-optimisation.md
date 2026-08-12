# Prompt pour Gemini — optimisation UI/UX du design system ministere-de-l-info

Prêt à copier-coller tel quel dans Gemini/Antigravity.

---

## Prompt

Tu es consulté comme expert UI/UX pour une application de data-visualisation politique et électorale française, développée en Python/Streamlit. Le projet s'appelle "ministère de l'info" — un outil personnel long terme, pas un produit commercial, mais avec une exigence de qualité élevée : l'objectif est un rendu crédible, sobre et institutionnel, pas un dashboard générique.

### Identité visuelle déjà posée (à respecter, pas à réinventer)

Un design system existe déjà et vient d'être intégré dans l'app via un fichier CSS unique injecté par `st.markdown`. Tokens actuels :

- **Couleurs** : Bleu France `#000091`, Rouge Marianne `#e1000f`, rampe de gris administratifs froids (`#161616` → `#fbfbfb`), couleurs sémantiques (succès/alerte/erreur/info) classiques.
- **Typographie** : Spectral (serif, titres/display), Hanken Grotesk (sans-serif, corps de texte — substitut libre à Marianne, la police officielle de l'État non redistribuable), IBM Plex Mono (tableaux, codes INSEE, chiffres).
- **Spacing** : grille 4px, radius 6px (contrôles) / 10px (cards) / 16px (grandes surfaces).
- **Élévation** : ombres très douces (`0 1px 3px rgba(22,22,22,.08)` à `0 12px 28px rgba(22,22,22,.12)`), pas de glow ni de couleurs dans les ombres.
- **Motion** : durées 80ms/140ms/220ms/360ms, easing `cubic-bezier(0.2,0,0,1)` (standard) et `cubic-bezier(0.16,1,0.3,1)` (out) — **définis mais quasiment pas utilisés** au-delà des transitions de couleur sur les boutons/liens.
- **Palette nuances politiques** (gauche → droite) : extrême gauche `#8b0000`, gauche `#e84c61`, divers `#9e9e9e`, centre `#f5b800`, droite `#3b7dd8`, extrême droite `#1f3864`.
- Référence de patterns : le Système de Design de l'État (DSFR, systeme-de-design.gouv.fr) et son extension dataviz [dsfr-chart](https://github.com/GouvernementFR/dsfr-chart) — vocabulaire de composants à réutiliser (data-box, tuile, bandeau) même si l'implémentation reste 100% Streamlit.

### Contraintes techniques Streamlit (important, à respecter strictement)

- Le style passe uniquement par du CSS injecté dans une balise `<style>` via `st.markdown(..., unsafe_allow_html=True)`, ciblant les attributs `data-testid` du DOM Streamlit (ex: `[data-testid="stMetric"]`, `[data-testid="stSidebar"]`). **Pas de React, pas de composants JS custom, pas de Vue** — uniquement CSS (+ éventuellement un peu de JS vanilla injecté si strictement nécessaire, à éviter si possible).
- Le contenu de `st.dataframe` est rendu dans un `<canvas>` (glide-data-grid) : impossible à styler en CSS (pas de couleurs de cellule, pas de bordures custom). Toute proposition sur les tableaux doit passer par les options natives (pandas Styler) ou par l'agencement autour du tableau, pas par ses cellules.
- Les composants encapsulés en `<iframe>` (cartes Folium via `streamlit-folium`) n'héritent pas du CSS injecté dans la page principale.
- Layout disponible : `st.columns`, `st.tabs`, `st.expander`, `st.sidebar`, `st.container` — pas de grille CSS libre, la structure DOM est imposée par Streamlit.
- Chaque page du dossier `pages/` est un script Python exécuté indépendamment (pas de SPA, pas de state partagé entre pages sans `st.session_state`).

### État actuel de l'app (diagnostic)

5 pages : Accueil, Géographie (carte choroplèthe multi-niveaux), Élections (présidentielles/législatives/municipales, en onglets), Législatif (Assemblée nationale + Sénat, 4 onglets), Économie (7+ indicateurs socio-économiques, 4 onglets + carte).

Problèmes identifiés :
1. **Page d'accueil sans valeur éditoriale** : elle affiche actuellement un écran de diagnostic technique (versions des librairies, test de connexion base de données) au lieu de présenter l'application. Aucun point d'entrée visuel vers les 4 modules.
2. **Incohérence de placement des filtres** : une page utilise la sidebar de façon extensive, les 3 autres mettent tous les filtres en inline en haut du contenu — pas de convention transversale.
3. **Pas de composant réutilisable** : chaque page réinvente sa mise en page (métriques, cartes, tableaux) au lieu de partager des fonctions communes.
4. **Emojis comme iconographie** (🇫🇷📍🗳️🏛️📊 dans les titres et la nav) — décision déjà prise de basculer vers des icônes vectorielles, mais le choix de la librairie/police d'icônes n'est pas encore fait.
5. **Tokens de motion définis mais inutilisés** : aucune micro-animation (hover, apparition de contenu, transition entre états de filtre) n'exploite `--duration-*` / `--ease-*`.

### Ce qu'on attend de toi

1. **Page d'accueil** : une proposition concrète de structure (bandeau/titre, éventuellement des "tuiles" de synthèse par module façon data-box DSFR, ce qui est réalisable avec `st.columns` + CSS sur des conteneurs). Doit donner envie d'explorer, pas ressembler à un écran de debug.
2. **Convention de layout transversale** aux 4 pages fonctionnelles : ordre des blocs (titre → filtres → contenu → source/métadonnée → détail tabulaire), en tenant compte de la contrainte "sidebar = filtres persistants (niveau territorial, période), inline = filtres contextuels à un onglet" déjà actée.
3. **Un système de "metric row" et de "carte de synthèse"** réutilisable en CSS pur sur les sélecteurs `data-testid` existants (`stMetric`, etc.), cohérent avec les tokens d'élévation/radius déjà définis.
4. **Propositions de micro-animations réalistes en CSS injecté** (pas de librairie JS lourde) : hover sur les cards/liens de nav, transition d'apparition de contenu, feedback de sélection sur la carte choroplèthe — en réutilisant les tokens `--duration-*`/`--ease-*` existants. Sois précis sur la faisabilité technique dans le cadre Streamlit décrit plus haut (ce qui est bloqué par les iframes/canvas, ce qui ne l'est pas).
5. **Recommandation d'une iconographie vectorielle** pour remplacer les emojis (nav sidebar + titres de page), cohérente avec le ton institutionnel (Bleu France/Marianne) et facile à intégrer dans Streamlit (police d'icônes chargée via Google Fonts/CDN + `<span>` unicode, ou SVG inline — pas de librairie React comme lucide-react qui ne fonctionne pas nativement en Streamlit).
6. **Accessibilité** : l'app vise un usage institutionnel — points de vigilance RGAA/WCAG à connaître (contraste, focus visible, tailles de cible) applicables à ce contexte Streamlit.

### Format de réponse souhaité

Recommandations concrètes et priorisées (pas de généralités), si possible avec extraits de CSS ciblant les sélecteurs `data-testid` mentionnés ci-dessus. Précise à chaque fois si la proposition est réalisable uniquement en CSS, ou si elle nécessite du JS injecté (et lequel, en restant minimal).
