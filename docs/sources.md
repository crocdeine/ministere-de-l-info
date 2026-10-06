# Sources de données — licences et mentions

Registre de conformité. Détails techniques (formats, URL, pièges) : `docs/data-sources.md`.
Vérification : **V** = licence lue dans les métadonnées officielles le 2026-10-04 ; **R** = confirmée par
recherche web, texte intégral non relu ; **D** = déduite, à vérifier.
Cohérence revue le 2026-10-06 avec `src/ministere_de_l_info/sources.py` (12 entrées) et
`LICENSE-DONNEES.md` (12 lignes) : mêmes sources et mêmes licences. Le fond de carte et les
circulaires de nuances ne figurent que dans ce registre (ce ne sont pas des données de la base).

| Source | Producteur / diffuseur | Tables | Licence | Vérif. | Mention obligatoire | Affichée dans l'UI |
|---|---|---|---|---|---|---|
| ADMIN-EXPRESS-COG | IGN (data.geopf.fr) | `geographies_*` (hors circonscriptions) | Licence Ouverte 2.0 (Etalab) | R | « IGN » + date de mise à jour | Oui (Accueil + légendes) |
| Populations légales / historiques | INSEE (Mélodi) | populations | Licence Ouverte 2.0 | R | « Source : Insee » + date | Oui (Accueil + légendes) |
| Filosofi + Recensement (fichier OLAP « RP communal et Filosofi depuis 2015 ») | INSEE, **republié par un particulier** sur data.gouv.fr (id `67289477639527408ae687da`) | `economie_filosofi`, `economie_rp` | Licence Ouverte 2.0 | V | Insee + intermédiaire + date | Oui (Accueil + légendes) |
| RSA par commune | CNAF (data.caf.fr) | `economie_social` | Licence Ouverte 2.0 | V | « CNAF » + date | Oui (Accueil + légendes) |
| APL (accessibilité potentielle localisée) | DREES | `economie_social` | Licence Ouverte 2.0 | V | « DREES » + date | Oui (Accueil + légendes) |
| Établissements et effectifs salariés commune × APE | URSSAF (open.urssaf.fr), modifié le 2026-05-29 | `economie_emploi_urssaf` | **ODbL 1.0** (partage à l'identique) | V | Attribution + mention ODbL + base dérivée sous ODbL | Oui (Accueil + légendes) |
| Chômage BIT régional, PIB/hab. (`lfst_r_lfu3rt`, `nama_10r_2gdp`) | Eurostat | `economie_contexte` | Politique de réutilisation de la Commission (CC BY 4.0) | R | « Source : Eurostat » + codes + signaler les modifications | Oui (Accueil + légendes) |
| Historique des députés, scores d'activité | Datan (association), d'après l'Assemblée nationale | `leg_elus` (AN), `leg_mandats`, `leg_activite` | Licence Ouverte **1.0** | V | « Datan » + date | Oui (Accueil + légendes) |
| Historique des députés, AMO30 (`tous_acteurs_mandats_organes_xi_legislature`, JSON zippé ≈ 14 Mo) : cause du mandat et suppléants, lus en mémoire | Assemblée nationale (data.assemblee-nationale.fr) | `leg_mandats.nuance_*` (remplaçants non inscrits) | Licence Ouverte (page licence du site, texte Etalab 2011, sans numéro de version) | V | « Assemblée nationale » + date | Oui (Accueil) |
| ODSEN_GENERAL | Sénat (data.senat.fr) | `leg_elus` (Sénat) | Licence data.senat.fr (reprend la Licence Ouverte) | R | Producteur + date ; pas d'aval officiel suggéré | Oui (Accueil + légendes) |
| Élections agrégées | data.gouv.fr d'après le ministère de l'Intérieur | `elections`, `resultats_*` ; `leg_mandats.nuance_*` (nuance d'élection des députés non inscrits) | Licence Ouverte 2.0 | V | Producteur + date | Oui (Accueil + légendes) |
| Contours des circonscriptions législatives | **Particulier** (data.gouv.fr, `jerome-desboeufs`), maj 2024-06-13 | `geographies_circonscriptions` | Licence Ouverte 2.0 | V | Auteur + date ; ne pas suggérer un caractère officiel | Oui (Accueil + légendes) |
| Fond de carte Plan IGN (tuiles WMTS de la Géoplateforme, non stockées dans la base) | IGN | — | Licence Ouverte | D | « © IGN » | Oui (« Fond : © IGN — Plan IGN » sur chaque carte) |
| Circulaires de nuances (classement des blocs) | Ministère de l'Intérieur | `nuances_harmonisees`, `blocs_politiques` | Documents administratifs publics | D | Référence NOR | Oui (légende des blocs par scrutin, ADR-0013) |

## Données personnelles (élus et candidats)

- `leg_elus.date_naissance` : **supprimée le 2026-10-04** (non utilisée par l'interface ; ADR-0013).
- `leg_elus.profession` (Sénat) : affichée.
- `resultats_candidats` : nom, prénom, sexe des candidats (publics, issus des résultats officiels).
- Non chargés (minimisation respectée) : courriel, réseaux sociaux, ville de naissance (Datan).

## Décisions (ADR-0013, 2026-10-04)

- Code sous MIT (`LICENSE`), base sous ODbL 1.0 (`LICENSE-DONNEES.md`).
- Registre unique dans le code : `src/ministere_de_l_info/sources.py` → tableau « Sources,
  licences et dates » de l'Accueil et légendes des pages.
- `date_naissance` supprimée de `leg_elus` (base locale migrée le 2026-10-04).

## Points ouverts

- Base republiée sous ODbL, sans `date_naissance` : release `db-2026-10-04` (2026-10-04). Les releases antérieures (`v0.5`, `db-2026-05`) restent en ligne sans mention ODbL (constaté le 2026-10-06) : à retirer ou annoter (décision Mathias).
- Résultats électoraux : date de chargement non tracée dans `_etl_metadata` (constaté le 2026-10-06).
