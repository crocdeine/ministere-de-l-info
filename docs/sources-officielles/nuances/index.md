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

## Circulaires archivées

| Fichier | NOR | Date | Scrutin | Nuances | Blocs ? | Fait notable |
|---|---|---|---|---|---|---|
| 2022-legislatives_INTA2212053C.pdf | INTA2212053C | avr. 2022 | Législatives 2022 | 19 | Non | Pas de regroupement en blocs |
| 2023-senatoriales_IOMA2322276J.pdf | IOMA2322276J | 16 août 2023 | Sénatoriales 2023 | 21 | Oui (1re fois) | Naissance des 6 blocs. LFI → gauche. RN → extrême droite |
| 2024-legislatives_IOMA2415630C.pdf | IOMA2415630C | juin 2024 | Législatives 2024 | 24 | Oui | Création nuance UG (union gauche) |
| 2026-municipales_INTP2602966C.pdf | INTP2602966C | 2 fév. 2026 | Municipales 2026 | 26 | Oui | LFI bascule → extrême gauche |

## Décisions du Conseil d'État (validations / contentieux)

- CE 21 sept. 2023, n°488379 (référé) et CE 11 mars 2024, n°488378 (fond) : validation
  du classement RN en extrême droite (sénatoriales 2023)
- CE 27 février 2026 : validation du classement LFI en extrême gauche et UDR en extrême
  droite (municipales 2026)
- CE 31 janvier 2020, n°437675 : suspension du classement de Debout la France (DLF) en
  extrême droite pour les municipales 2020 (erreur manifeste d'appréciation) — conforte
  le classement DLF/Dupont-Aignan en bloc DTE (droite) avant 2026

## Usage dans le projet

Ces circulaires alimentent :

- la table `blocs_politiques` (les 6 blocs officiels : EXG, GAU, DIV, CENT, DTE, EXD)
- la table `candidats_presidentielle` (classement sourcé des candidats 2017/2022)
- la table `nuances_harmonisees` (mapping nuance→bloc pour 2002/2007/2012)
- la future table `nuances_blocs` (mapping nuance→bloc daté, pour les scrutins à nuances
  partisanes : legi, euro, regi, muni — prévu en C2c)
