# Circulaires officielles — Nuances politiques et blocs de clivages

Archive des circulaires du Ministère de l'Intérieur relatives à l'attribution des nuances
politiques aux candidats. Ces documents font foi pour le classement des partis et candidats
par bloc de clivage dans le module Élections.

## Contexte

La nuance politique est attribuée par l'administration (préfets) à chaque candidat,
distincte de l'étiquette librement choisie par le candidat. Depuis les municipales 2020
(circulaire INTA1931378J, annexe 3), les nuances sont regroupées en 6 "blocs de clivages" :
extrême gauche, gauche, divers (nommé `AUT` en 2020, « Autres » en 2023), centre, droite,
extrême droite.

**IMPORTANT** : trois circulaires seulement contiennent une grille de blocs : INTA1931378J
(municipales 2020), IOMA2322276J (sénatoriales 2023) et INTP2602966C (municipales 2026).
Les circulaires législatives 2022 et 2024 n'en contiennent pas. Pour un scrutin sans grille,
le projet applique la doctrine de
l'[ADR-0010](../../adr/0010-revision-nuances-et-blocs.md) : grille la plus proche dans le
temps (antérieure de préférence) si le code y désigne la même famille politique, sinon
classement reconstruit justifié (voir aussi
[l'ADR-0005](../../adr/0005-nuances-et-blocs-officiels.md)).

**Circulaires législatives 2002-2017 non archivables** : les circulaires de nuançage de ces
scrutins sont des documents internes du Ministère, **non publiés au Journal officiel**. Elles
ne peuvent donc pas être archivées ici. Le classement de leurs nuances est reconstruit selon
la logique officielle datée de l'[ADR-0005](../../adr/0005-nuances-et-blocs-officiels.md)
(§ « Application aux législatives 2002-2024 »). Le détail des 111 nuances législatives validées
(2002-2024) figure dans
[reports/mapping-nuances-legislatives-validated.md](../../../reports/mapping-nuances-legislatives-validated.md).

## Circulaires archivées (PDF)

| Fichier | NOR | Date | Scrutin | Nuances | Blocs ? | Fait notable |
|---|---|---|---|---|---|---|
| 2020-municipales_INTA1931378J.pdf | INTA1931378J | 3 fév. 2020 | Municipales 2020 | 23 (grille des listes) | **Oui (1re grille)** — annexe 3 p. 10, individuelles et listes ; bloc « divers » nommé `AUT` | Nuançage des listes dans les communes de 3 500 hab et plus et les chefs-lieux d'arrondissement ; circulaire postérieure à l'ordonnance CE n°437675 |
| 2022-legislatives_INTA2212053C.pdf | INTA2212053C | avr. 2022 | Législatives 2022 | 19 | Non | Pas de regroupement en blocs ; ECO inclut EELV (pas de code VEC) |
| 2023-senatoriales_IOMA2322276J.pdf | IOMA2322276J | 16 août 2023 | Sénatoriales 2023 | 21 | Oui — colonne « Bloc » des annexes 1 et 2 (p. 6-7) | LFI → gauche. RN → extrême droite. UDI → **droite** (centre en 2020 et 2026). ECO → « Autres » |
| 2024-legislatives_IOMA2415630C.pdf | IOMA2415630C | juin 2024 | Législatives 2024 | 24 | **Non** (annexe 1 = liste des nuances, sans bloc) | Création nuance UG (union gauche) ; VEC et ECO distincts |
| 2026-municipales_INTP2602966C.pdf | INTP2602966C | 2 fév. 2026 | Municipales 2026 | 26 individuelles, 25 de listes | Oui — annexe 3 p. 11 (individuelles) et p. 12 (listes) | LFI bascule → extrême gauche ; seuil 3 500 hab |

Note sur INTA1931378J (PDF de 10 pages, archivé en Phase D3, commit `f7e9629`) : l'annexe 3 (p. 10, « Grilles de regroupement des nuances politiques par blocs de clivages ») répartit les nuances individuelles et de listes en 6 blocs (EXG, GAU, AUT, CENT, DTE, EXD). C'est la première grille officielle de blocs, antérieure à IOMA2322276J ; l'affirmation contraire de l'ADR-0005 est corrigée par l'[ADR-0010](../../adr/0010-revision-nuances-et-blocs.md) (vérification sur rendu image, 2026-09-24).

## Décisions du Conseil d'État (archivées en texte intégral)

| Fichier | N° | Date | Objet |
|---|---|---|---|
| 2020-CE_decision_437675.md | 437675 | 31 janv. 2020 | Suspension circulaire 10/12/2019 muni 2020 — seuil 9 000 hab + LDVC + DLF/EXD annulés |
| 2026-CE_decision_512694.md | 512694 | 27 fév. 2026 | Rejet recours LFI + UDR contre INTP2602966C — LFI→EXG et UDR→EXD validés |

## Décisions du Conseil d'État (citées, non archivées séparément)

- CE 21 sept. 2023, n°488379 (référé) et CE 11 mars 2024, n°488378 (fond) : validation
  du classement RN en extrême droite (sénatoriales 2023)

## Lois citées

| Référence | Légifrance | Objet |
|---|---|---|
| Loi n°2013-403 du 17 mai 2013 | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000027414225 | Abaisse le seuil du scrutin proportionnel de liste de **3 500 à 1 000 habitants** (applicable aux municipales 2014). N'affecte pas le seuil de nuançage du Ministère (maintenu à 3 500 hab). |

## Usage dans le projet

Ces circulaires alimentent :

- la table `blocs_politiques` (les 6 blocs officiels : EXG, GAU, DIV, CENT, DTE, EXD)
- la table `candidats_presidentielle` (classement sourcé des candidats 2017/2022)
- la table `nuances_harmonisees` (mapping nuance→bloc pour présidentielles et législatives)
- les entrées municipales de `nuances_harmonisees` (77 entrées 2008-2026 : 67 chargées en D3.2, voir ADR-0005 § « Application aux municipales 2008-2026 », révisées et complétées par l'ADR-0010)
