# Sources de données — licences et mentions

Registre de conformité. Détails techniques (formats, URL, pièges) : `docs/data-sources.md`.
Vérification : **V** = licence lue dans les métadonnées officielles le 2026-10-04 ; **R** = confirmée par
recherche web, texte intégral non relu ; **D** = déduite, à vérifier.

| Source | Producteur / diffuseur | Tables | Licence | Vérif. | Mention obligatoire | Affichée dans l'UI (2026-10-04) |
|---|---|---|---|---|---|---|
| ADMIN-EXPRESS-COG | IGN (data.geopf.fr) | `geographies_*` (hors circonscriptions) | Licence Ouverte 2.0 (Etalab) | R | « IGN » + date de mise à jour | Partiel (nom + année, sans licence) |
| Populations légales / historiques | INSEE (Mélodi) | populations | Licence Ouverte 2.0 | R | « Source : Insee » + date | Partiel |
| Filosofi + Recensement (fichier OLAP « RP communal et Filosofi depuis 2015 ») | INSEE, **republié par un particulier** sur data.gouv.fr (id `67289477639527408ae687da`) | `economie_filosofi`, `economie_rp` | Licence Ouverte 2.0 | V | Insee + intermédiaire + date | Partiel (intermédiaire non cité) |
| RSA par commune | CNAF (data.caf.fr) | `economie_social` | Licence Ouverte 2.0 | V | « CNAF » + date | Partiel |
| APL (accessibilité potentielle localisée) | DREES | `economie_social` | Licence Ouverte 2.0 | V | « DREES » + date | Partiel |
| Établissements et effectifs salariés commune × APE | URSSAF (open.urssaf.fr), modifié le 2026-05-29 | `economie_emploi_urssaf` | **ODbL 1.0** (partage à l'identique) | V | Attribution + mention ODbL + base dérivée sous ODbL | Partiel (sans mention ODbL) — **non conforme dans la base publiée** |
| Chômage BIT régional, PIB/hab. (`lfst_r_lfu3rt`, `nama_10r_2gdp`) | Eurostat | `economie_contexte` | Politique de réutilisation de la Commission (CC BY 4.0) | R | « Source : Eurostat » + codes + signaler les modifications | Oui (modifications non signalées) |
| Historique des députés, scores d'activité | Datan (association), d'après l'Assemblée nationale | `leg_elus` (AN), `leg_mandats`, `leg_activite` | Licence Ouverte **1.0** | V | « Datan » + date | Oui |
| ODSEN_GENERAL | Sénat (data.senat.fr) | `leg_elus` (Sénat) | Licence data.senat.fr (reprend la Licence Ouverte) | R | Producteur + date ; pas d'aval officiel suggéré | Partiel (sans date) |
| Élections agrégées | data.gouv.fr d'après le ministère de l'Intérieur | `elections`, `resultats_*` | Licence Ouverte 2.0 | V | Producteur + date | Partiel |
| Contours des circonscriptions législatives | **Particulier** (data.gouv.fr, `jerome-desboeufs`), maj 2024-06-13 | `geographies_circonscriptions` | Licence Ouverte 2.0 | V | Auteur + date ; ne pas suggérer un caractère officiel | **Non** (légende IGN par défaut) |
| Circulaires de nuances (classement des blocs) | Ministère de l'Intérieur | `nuances_harmonisees`, `blocs_politiques` | Documents administratifs publics | D | Référence NOR | Voir `docs/sources-officielles/nuances/` |

## Données personnelles (élus et candidats)

- `leg_elus.date_naissance` (4 065 élus, toutes renseignées) : publique à la source, **non utilisée par l'interface**.
- `leg_elus.profession` (Sénat) : affichée.
- `resultats_candidats` : nom, prénom, sexe des candidats (publics, issus des résultats officiels).
- Non chargés (minimisation respectée) : courriel, réseaux sociaux, ville de naissance (Datan).

## Points ouverts (voir `docs/audit-2026-10-04.md`)

Licence de la base publiée (ODbL imposée par URSSAF), absence de licence du dépôt, mentions et dates de
mise à jour absentes de l'interface, attribution erronée des circonscriptions, minimisation de
`date_naissance` dans la base publiée.
