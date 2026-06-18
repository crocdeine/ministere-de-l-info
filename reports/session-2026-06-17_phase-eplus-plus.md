# Phase E++ — Contexte macro Eurostat

**Date** : 2026-06-17
**Statut** : ✅ Terminée

## Données chargées
- economie_contexte : 104 lignes
  - tx_chomage_bit : FRE + FR, 1999-2025 (Eurostat lfst_r_lfu3rt)
  - pib_eur_hab : FRE + FR, 2000-2024 (Eurostat nama_10r_2gdp)

## Valeurs de référence
- Chômage 2020 : HdF 9.0% vs France 8.1% (écart +0.9pt)
- PIB/hab 2020 : HdF ~26 700€ vs France ~34 300€ (écart -7 600€)

## Décisions techniques
- API SDMX Eurostat (TSV) préférée à INSEE IDBank (bloquée anti-bot)
- dataset tgs00005 déprécié → remplacé par nama_10r_2gdp
- Filtres empiriquement vérifiés : isced11=TOTAL, sex=T, age=Y15-74, unit=PC
- Flags Eurostat (u/b/d/p) strippés, ':' → NULL

## UI
- Tab 2 radio : 3e option "Contexte HdF vs France (Eurostat)"
- Line chart HdF (rouge) vs France (bleu), hovermode unified
- st.metric écart HdF-France dernière année disponible

## Commits
- `7a3b74c` feat(economie): add economie_contexte table + Eurostat loader (Phase E++)
- `c9aa17e` fix(economie): fix SyntaxWarning invalid escape in eurostat docstring
- `c8258f8` feat(economie): add Eurostat HdF vs France charts in evolution tab (Phase E++ UI)
- `HEAD`   docs(economie): Phase E++ complete — Eurostat context macro loaded and displayed
