# Synthèse — Jalon J3 (lisibilité honnête) et AMO des non-inscrits

Date : 2026-10-06 — Directeur : Claude Code — Décideur : Mathias — Branche : `claude/exciting-dirac-8mogwe`

## Résumé exécutif

- J3 livré et relu (verificateur-code, Opus : prêt, 0 bloquant) : classes de couleur fixes par
  indicateur, score de bloc 0-100 %, évolutions en % des exprimés par défaut, palette sans rouge-vert,
  métrique « Bloc majoritaire » non tronquée, classe « 0 » distincte, n.d. homogène.
- AMO (Assemblée nationale) : 26 des 30 non-inscrits restants classés selon leur titulaire ; 4 élus
  de partielles restent « Divers » (résultats non publiés en open data).
- Seuils arbitrés par Mathias le 2026-10-06 (docs/orientations.md).
- Mesures : 650 tests réussis, 0 échec ; couverture 77,24 % ; CI verte sur `c43fede`.
- Attendu : contrôle visuel de Mathias dans l'application.

## Livrables

| Lot | Agent | Commits | Rapport |
|---|---|---|---|
| J3 lisibilité | developpeur-ui + directeur | `924c5cc`, `b8897b8`, dernier `feat(ui)` | `reports/ui-lisibilite-j3-2026-10-06.md` |
| AMO non-inscrits | ingenieur-etl | `36f2e0c`, `314afcc` | `reports/etl-non-inscrits-2026-10-04.md` (§ 2026-10-06) |

## Points assumés

- Les 4 élus de partielles (Edmond-Mariette, Souchet, Poursinoff, Vuibert) restent « Divers » :
  pas de source officielle ouverte de leur nuance.
- Pas d'étiquettes directes sur les courbes (la légende nomme chaque série).
