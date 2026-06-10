# Clôture Phase D — Module Élections complet

**Date** : 2026-06-10
**Périmètre** : Présidentielles + Législatives + Municipales HdF
**Tag git** : v0.4-elections-complet (commit 7f21346)
**Statut** : ✅ Terminée

---

## Synthèse exécutive

La Phase D complète le module Élections en ajoutant les législatives HdF 2002-2024 (D1), le drill-down jusqu'au bureau de vote pour présidentielles et législatives (D2), et les municipales HdF 2008-2026 (D3). Le projet couvre désormais 22 ans de données électorales HdF sur 3 types de scrutin, avec une méthodologie politique sourcée et tracée au niveau de chaque entrée de la base (colonne `source_bloc`), défendue par les circulaires officielles du Ministère de l'Intérieur et validée par des décisions du Conseil d'État.

**Volumes totaux à la clôture :** 162 469 lignes participation (30 scrutins), 1 093 836 lignes candidats, 216 mappings nuances.

---

## Sous-phases

### D1 — Législatives HdF 2002-2024

- D1.1 Exploration (rapport `reports/exploration-elections-legislatives.md`)
- D1.2 Chargement schéma + données (commit `51a6ef5`)
- D1.3 UI Streamlit (commit `909b086`)
- **Volumes :** 72 730 lignes participation, 481 705 lignes candidats, 12 scrutins (24 tours), 50 circos HdF
- **Méthodologie :** ancien découpage 2002/2007 géré via `code_circo` VARCHAR ; nouveau découpage dès 2012 ; 13 communes coupées par deux circos documentées dans ADR-0005

### D2 — Drill-down BV (présidentielles + législatives)

- Commit `4cb0a41`
- 258 tests verts, coverage 76%
- **Décision actée :** dropdown commune pour le drill-down BV — pas de clic carte (st_folium ne retourne pas les properties de feature en version courante)

### D3 — Municipales HdF 2008-2026

- D3.1 Exploration (rapport `reports/exploration-elections-municipales.md`)
- D3.1.2 Mapping nuances + recherche documentaire circulaires + jurisprudence CE
- D3.2 Migration schéma + chargement + 67 mappings + 3 vues SQL (commit `f7e9629`)
- D3.3 UI Streamlit (commit `7f21346`)
- **Volumes :** 8 scrutins (16 tours), 25 861 lignes participation, 159 578 lignes candidats, 67 nuances mappées
- **Méthodologie :** seuils variables (3 500 hab communes > liste nuancée, 1 000 hab pour publication résultats) ; bascule LFI 2020 GAU → 2026 EXG validée CE 27/02/2026 n°512694 ; codes NC/LMAJ/LNC non mappés sur bloc (communes <1 000 hab non nuancées)
- **Lacune source data.gouv.fr 2008 (dept 59)** : seulement 2 communes Nord dans le Parquet 2008, Lille absente — confirmé par requête directe sur le fichier brut sans aucun filtre. Documenté ADR-0005, warning dynamique dans l'UI.

---

## Décisions structurantes (synthèse)

ADR principal : [ADR-0005](../docs/adr/0005-nuances-et-blocs-officiels.md) — étendu 2× en Phase D.

| Section ADR-0005 | Règle |
|---|---|
| § Règle générale | Classement "officiel de l'époque" — un parti est classé selon la nomenclature en vigueur à la date du scrutin |
| § Application aux législatives 2002-2024 | Ancien découpage 2002/2007 ; 111 nuances ; 13 communes multi-circo documentées |
| § Application aux municipales 2008-2026 | Seuils 3500/1000 ; bascule LFI 2020→2026 ; codes non mappés documentés |
| § Limitation source data.gouv.fr 2008 | Lacune Nord (59) confirmée en source, non corrigible sans source alternative |

---

## Sources officielles archivées

Répertoire : `docs/sources-officielles/nuances/` — 7 documents sources + index

| Référence | Type | Objet |
|---|---|---|
| INTA1931378J | Circulaire (PDF 1.0M) | Nuances politiques municipales 2020 |
| INTA2212053C | Circulaire (PDF 2.7M) | Nuances politiques législatives 2022 |
| IOMA2322276J | Circulaire (PDF 4.4M) | Nuances sénatoriales 2023 — naissance des 6 blocs officiels |
| IOMA2415630C | Circulaire (PDF 3.6M) | Nuances législatives 2024 — création nuance UG |
| INTP2602966C | Circulaire (PDF 4.9M) | Nuances municipales 2026 — grille 67 nuances, bascule LFI EXG |
| CE 31/01/2020 n°437675 | Décision (MD) | Suspension partielle INTA1931378J |
| CE 27/02/2026 n°512694 | Décision (MD) | Validation LFI → EXG et UDR → EXD |

---

## Métriques techniques

| Métrique | Avant Phase D (Phase C close) | Après Phase D |
|---|---|---|
| Tests | 184 | 331 |
| Coverage | 75.25% | 69.30% |
| Vues SQL électorales | 5 (pres) | 11 (4 pres + 1 commune + 3 legi + 3 muni) |
| Lignes resultats_participation | 63 878 (pres) | 162 469 (pres+legi+muni) |
| Lignes resultats_candidats | 452 553 (pres) | 1 093 836 (pres+legi+muni) |
| Lignes nuances_harmonisees | ~149 | 216 |
| Scrutins chargés (avec données) | 10 (pres) | 30 (10+12+8) |
| Commits Phase D | — | 9 (e99a6b5 → 7f21346) |
| Sources officielles archivées | 0 | 7 documents (5 PDF + 2 MD) |
| ADR mis à jour | 0 | 1 (ADR-0005, étendu 2× : legi + muni) |

---

## Modules accessibles à l'utilisateur final

L'utilisateur peut désormais :

1. **Élections présidentielles HdF** (2002-2022, 10 scrutins) — carte bloc dominant par commune, évolution temporelle, drill-down commune → bureau de vote
2. **Élections législatives HdF** (2002-2024, 12 scrutins) — carte par circonscription, évolution par circo, drill-down commune → BV, gestion ancien/nouveau découpage
3. **Élections municipales HdF** (2008-2026, 8 scrutins) — carte bloc dominant par commune, gestion explicite des communes "Non classé" (<3 500 hab), drill-down par commune avec détail nominatif des listes

Pour les 3 modules : méthodologie politique sourcée et tracée jusqu'au niveau de chaque entrée DB (`source_bloc`).

---

## Limites identifiées et documentées

1. **Source data.gouv.fr 2008 incomplète — dept 59 (Nord)** : 2 communes seulement dans le Parquet brut 2008 (Seclin, Pérenchies), Lille absente. Documenté ADR-0005, warning dynamique dans l'UI.
2. **Hachures Folium non rendues** : communes Non classé 2026 s'affichent en gris uni, pas hachuré. Légende explicite. Non bloquant.
3. **Clic carte non implémenté** : st_folium ne retourne pas les properties de feature en version courante — drill-down via dropdown uniquement. Documenté.

---

## Ouvertures pour la suite

Modules envisagés (CLAUDE.md) :

- **Module Économie** : à cadrer (périmètre, sources, granularité)
- **Polissage UI/UX** : hachures Folium, optimisation chargement, accessibilité
- **Extension géographique** : décision Mathias — maintenir HdF pour cohérence projet

Pas de décision immédiate — à trancher lors d'une session de cadrage.

---

## Tag git associé

`v0.4-elections-complet` posé sur le commit `7f21346` (D3.3 close).

Convention du projet :
- `v0.2` : Module Géographie terminé
- `v0.3-elections-pres` : Présidentielles complètes (Phase C)
- `v0.4-elections-complet` : Module Élections complet (Phase D — pres+legi+muni HdF 2002-2026)
