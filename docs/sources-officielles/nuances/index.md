# Circulaires officielles — Nuances politiques et blocs de clivages

Archive des circulaires du Ministère de l'Intérieur relatives à l'attribution des nuances
politiques aux candidats. Ces documents font foi pour le classement des partis et candidats
par bloc de clivage dans le module Élections.

## Contexte

La nuance politique est attribuée par l'administration (préfets) à chaque candidat,
distincte de l'étiquette librement choisie par le candidat. Depuis les sénatoriales 2023,
les nuances sont regroupées en 6 "blocs de clivages" : extrême gauche, gauche, divers,
centre, droite, extrême droite.

**IMPORTANT** : le regroupement officiel en blocs n'existe que depuis 2023. Pour les
scrutins antérieurs, le projet reconstruit le bloc selon la logique officielle
(voir [docs/adr/0005-nuances-et-blocs-officiels.md](../../adr/0005-nuances-et-blocs-officiels.md)).

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
| 2022-legislatives_INTA2212053C.pdf | INTA2212053C | avr. 2022 | Législatives 2022 | 19 | Non | Pas de regroupement en blocs |
| 2023-senatoriales_IOMA2322276J.pdf | IOMA2322276J | 16 août 2023 | Sénatoriales 2023 | 21 | Oui (1re fois) | Naissance des 6 blocs. LFI → gauche. RN → extrême droite |
| 2024-legislatives_IOMA2415630C.pdf | IOMA2415630C | juin 2024 | Législatives 2024 | 24 | Oui | Création nuance UG (union gauche) |
| 2026-municipales_INTP2602966C.pdf | INTP2602966C | 2 fév. 2026 | Municipales 2026 | 26 | Oui | LFI bascule → extrême gauche ; seuil 3 500 hab |

## Circulaires archivées (notes texte — PDF Légifrance non téléchargeable automatiquement)

| Fichier | NOR | Date | Scrutin | Statut |
|---|---|---|---|---|
| 2020-municipales_INTA1931378J_lien.md | INTA1931378J | 3 fév. 2020 | Municipales 2020 | ⚠️ PDF à télécharger manuellement — URL dans le fichier note |

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
- la future table d'extension pour les municipales (mapping 34 nuances muni → blocs — prévu D3.2)
