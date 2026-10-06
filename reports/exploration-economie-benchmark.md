# Benchmark outils datavisualisation économique territoriale

## Tableau comparatif

| Outil | Producteur | Granularité | Indicateurs | Points forts | Manques |
|---|---|---|---|---|---|
| **Statistiques Locales** | INSEE | Région à l'IRIS / Carreaux (200m) | Emploi, chômage, revenus, démographie, entreprises | Richesse des données, maille très fine, comparateur de territoires | Interface austère, impossible de croiser avec des données non-officielles |
| **Observatoire des Territoires** | ANCT | Région au niveau communal | ~700 indicateurs (logement, emploi, transitions) | Cartes interactives puissantes, diagnostics territoriaux complets | Axé institutionnel, plateforme parfois lourde, peu d'infra-communal |
| **Portails Régionaux (ex: data.bretagne.bzh)** | Régions / CCI | Région, EPCI, Bassin d'emploi | Tissu économique, zones d'activités, entreprises | Données ancrées localement, outils spécifiques au tissu régional | Fonctionnement en silos géographiques, qualité d'interface variable |
| **Tableau de bord France Travail** | France Travail | Région, Bassin d'emploi | Demandeurs d'emploi, offres, tension du marché | Données très régulières, reflet direct du marché de l'emploi | Vue grand public peu analytique, centré uniquement sur l'emploi |

## Analyse détaillée des outils principaux

### Statistiques locales (INSEE)
- **URL :** https://statistiques-locales.insee.fr
- **Analyse :** C'est l'outil de référence au niveau national. Il se distingue par son incroyable finesse géographique (jusqu'à l'échelle du quartier via les IRIS ou des carreaux de 200m de côté).
- **Ce qu'on peut faire mieux :** L'interface reste très "statistique" et s'adresse avant tout aux professionnels. Elle manque d'éditorialisation pour guider un utilisateur curieux mais non-expert. De plus, on ne peut y superposer ses propres données facilement sans perdre en fluidité.

### Observatoire des Territoires (ANCT)
- **URL :** https://www.observatoire-des-territoires.gouv.fr
- **Analyse :** Très efficace pour générer des "portraits de territoire" PDF ou interactifs. La plateforme excelle dans l'analyse des politiques publiques et de l'aménagement du territoire (accès aux services publics, vulnérabilités).
- **Ce qu'on peut faire mieux :** L'outil peut être écrasant par la multitude de ses indicateurs (près de 700). Pour *ministere-de-l-info*, il faudra faire un choix fort pour ne pas perdre l'utilisateur avec une "usine à gaz".

### Observatoires Locaux / CCI
- **URL :** ex: https://data.bretagne.bzh ou plateformes DataEco des CCI.
- **Analyse :** Fournissent des jeux de données très précis sur le tissu local, par exemple la consommation foncière des zones d'activités économiques (ZAE) ou l'annuaire des entreprises.
- **Ce qu'on peut faire mieux :** Ces données ouvertes sont souvent livrées brutes ou avec des visualisations basiques. Il y a un vrai travail à faire pour les intégrer dans un outil plus dynamique et esthétique.

### France Travail (ex-Pôle Emploi)
- **URL :** https://www.francetravail.org / Plateformes open data de l'emploi
- **Analyse :** Les tableaux de bord professionnels permettent d'avoir une vision granulaire des bassins d'emploi et des métiers en tension.
- **Ce qu'on peut faire mieux :** L'expérience est cloisonnée. L'intérêt d'un nouvel outil serait de mettre ces chiffres en perspective avec d'autres dimensions sociologiques.

## Outils open source notables

Sur GitHub, la communauté Python et Data Science regorge d'initiatives pour exploiter ces données (recherches autour de *INSEE data streamlit* et *données locales visualisation python*) :
- **Streamlit + API INSEE :** De nombreux projets utilisent des wrappers Python (ex: `api_insee`) couplés à **Streamlit**. Streamlit est idéal pour *ministere-de-l-info* car il permet de créer des interfaces de dataviz interactives, faciles à packager avec Docker.
- **PyGWalker :** Une bibliothèque en plein essor qui transforme n'importe quel DataFrame Pandas en une interface d'exploration visuelle similaire à "Tableau Software" (glisser-déposer de variables). Parfait pour l'exploration libre.
- **Plotly & Dash :** Le standard open source pour la création de cartes choroplèphes interactives fluides. De nombreux dépôts montrent comment lier les données économiques aux GeoJSON des communes françaises.

## Visualisations inspirantes (avec URLs)

- **The New York Times - Scrollytelling et personnalisation :**
  Le NYT est le maître pour rendre la macroéconomie humaine. Leur visualisation historique *"Unemployment Rate For People Like You"* permettait à l'utilisateur de filtrer le chômage selon son âge, son sexe ou sa région, rendant la donnée très personnelle.
  *(Analyse technique via FlowingData : https://flowingdata.com)*
- **Bloomberg - Densité assumée et contextuelle :**
  Bloomberg excelle dans la création de tableaux de bord financiers et économiques denses. Ils utilisent souvent des cartes thématiques pour superposer des évolutions de l'emploi avec des secteurs industriels précis.
  *(URL : https://www.bloomberg.com/graphics/)*
- **Le Monde (Les Décodeurs) - Fracture territoriale et politique :**
  Ils utilisent brillamment les cartes choroplèphes (nuances de couleurs) pour illustrer les inégalités régionales (ex: revenus, chômage des jeunes) et expliquer l'impact des réformes territoriales de manière très didactique.
  *(URL : https://www.lemonde.fr/les-decodeurs/)*

## Positionnement différenciant de ministere-de-l-info

Face à ces acteurs institutionnels ou grands médias, *ministere-de-l-info* possède des atouts majeurs, particulièrement pour un public ciblé et curieux (amis non-techniques) :

1. **Le Croisement Inédit "Élections vs Économie" :**
   C'est le *killer feature*. L'INSEE ou l'ANCT ne croiseront jamais la donnée économique (chômage, pauvreté) avec le vote RN, LFI ou Renaissance. *ministere-de-l-info* peut le faire, permettant d'étudier visuellement si la désindustrialisation d'un bassin de vie des Hauts-de-France se traduit par des dynamiques électorales spécifiques.
2. **Performance et Hyper-focalisation Régionale :**
   Les outils nationaux rament souvent à cause du poids des données de toute la France. En pré-calculant les données uniquement pour les Hauts-de-France et en tournant en local (Docker), l'outil sera ultra-fluide et réactif.
3. **Approche "Opinionated" (Parti pris éditorial) :**
   Là où l'État doit être exhaustif (700 indicateurs), l'outil doit faire le tri. Proposer une interface simple, qui va droit au but avec les métriques qui intéressent réellement le citoyen.

## Recommandations éditoriales pour le module Économie

Pour implémenter ce module efficacement, voici les recommandations issues du benchmark :
- **Sélection drastique d'indicateurs :** Se concentrer sur 4 ou 5 variables majeures : Taux de chômage, Évolution de l'emploi industriel, Revenu médian, Taux de pauvreté. Rien de plus pour commencer.
- **Granularité communale ou par Canton :** Le département est trop vaste pour analyser des dynamiques locales. Il faut viser l'échelle de la commune ou du bassin d'emploi pour superposer avec les bureaux de vote.
- **Fonctionnalité d'écran scindé (Split Screen) :** Développer une interface permettant d'avoir la carte économique à gauche et la carte électorale à droite, avec un survol synchronisé (survoler une commune à gauche affiche ses données sur les deux cartes simultanément).
- **Esthétisme et accessibilité :** Utiliser des palettes de couleurs accessibles (comme *viridis* ou *magma* dans Plotly/Matplotlib) pour garantir une bonne lisibilité des cartes choroplèphes.
