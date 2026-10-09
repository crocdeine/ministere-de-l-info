# Vague A, lot A5 — Méthodologie et glossaire (application web)

Date : 2026-10-09 — Agent : developpeur-ui (worktree) — Branche : `feat/web-methodologie` (non poussée)
Fiche : `.claude/plans/2026-10-07-vague-a-5-methodologie-glossaire.plan.md`

## Résumé exécutif

- Texte source unique `docs/methodologie.md` : sept parties (règles de présentation, sources, blocs, calculs, valeurs absentes, ruptures, limites) et un glossaire. Chaque section se termine par sa ligne « Source(s) : » (ADR, circulaires archivées, registre `sources.py`, schéma de la base). **Version lisible pour la relecture de Mathias : ce fichier (rendu Markdown du dépôt) et les captures `docs/captures/a5/`.**
- Panneau Méthodologie : fenêtre `<dialog>` native par-dessus la page. Il s'ouvre depuis l'étiquette « Grille officielle » / « Reconstruit » (devenue bouton), le lien « Méthode » sous la légende et « Ruptures entre scrutins » dans la mention « Limite ». Ancres stables (`#methode`, `#blocs`, `#ruptures`…), hash de page inchangé.
- Tables générées, jamais recopiées : sources depuis `sources.py`, correspondances → bloc depuis la base (`methodologie.json.gz`, empreinte vérifiée). Table consultable avec un filtre par année.
- Mesure en base (2026-10-09, lecture seule) : 384 correspondances nuance → bloc (172 codes distincts) et 57 classements individuels. CLAUDE.md (« 229 ») et la fiche corrigés.
- Correction de libellé : « vérification code par code en cours » retiré des légendes des municipales 2020/2026. Vérification terminée selon l'ADR-0010 § d, le rapport `verification-classements-j2-2026-10-04.md` § 3 et le test `test_referentiel_identique_a_la_grille` ; les 48 lignes citent leur circulaire.
- L'interface web ne renvoie plus vers `docs/adr/` (renvoi retiré des légendes à l'export ; Streamlit, gelé, le garde).
- Vérifications : tsc, vitest (20 tests), build, budget (388,5 Ko gzip de JS initial, chunk Méthodologie 7,9 Ko chargé à la demande), fumée WebKit `npm run mesure` (0 erreur), captures WebKit sans fenêtre, pytest export + conformité (24 réussis), ruff.
- Décisions attendues : 3 questions fermées (§ 4).

## 1. Commits

| Commit | Objet |
|---|---|
| `12188ec` | fix(elections) : légende 2020/2026 sans « vérification code par code en cours » ; renvoi ADR isolé (`RENVOI_METHODE`) |
| `0b6d76a` | feat(web) : export `methodologie.json.gz` + test |
| `1bafaab` | docs(methodologie) : texte source |
| `598d252` | feat(web) : panneau, liens « Méthode », analyseur Markdown minimal, tests |
| (dernier) | docs : CLAUDE.md, fiche, architecture, guide, README web, captures, ce rapport |

## 2. Choix techniques (sans décision de fond)

- Pas de bibliothèque Markdown : `web/src/markdown.ts` lit un sous-ensemble (titres `{#ancre}`, listes, tableaux, gras, code, liens, insertions `{{sources}}` / `{{correspondances}}`). Rendu en éléments React, sans HTML injecté.
- Panneau rendu par portail dans `document.body` (un `<dialog>` ne peut pas être imbriqué dans le paragraphe de légende). Fermeture : bouton, Échap, clic sur le fond.
- Fichiers de l'agent A2 non touchés (`App.tsx`, `PageElections.tsx`, `styles.css`) : styles dans `methodologie.css`, manifeste relu par le panneau.
- Panneau sur plaque blanche (tables avec carrés de couleur de bloc, ADR-0016 point 2).
- Tables d'échantillon : 252 correspondances dans la base d'échantillon (plus ancienne) ; la base réelle en compte 441 (384 + 57).

## 3. Points d'attention pour la relecture

- Glossaire et calculs citent le code électoral, art. L. 65 et L. 66 (blancs et nuls décomptés à part). Cette référence ne figure dans aucun document du projet : à confirmer.
- « EPCI » et « code INSEE » renvoient aux définitions de l'INSEE, sans lien précis.
- La note de bas de carte de `PageElections.tsx` (bloc en tête, n.d.) ne renvoie pas encore au panneau : fichier du lot A2. Après fusion de A2, une ligne suffit : `<LienMethode ancre="bloc-en-tete" …>` (ancres `bloc-en-tete` et `valeurs-absentes` déjà définies et testées).
- Mots proscrits du garde-fou 6 : présents seulement dans l'énoncé de la règle (testé).

## 4. Questions fermées

1. Le texte de `docs/methodologie.md` est-il validé tel quel ? (oui / non, avec corrections)
2. Garder la référence « code électoral, art. L. 65 et L. 66 » ? (oui / non : retirer et citer seulement le schéma de la base)
3. Ajouter une entrée « Méthodologie » dans la navigation, en plus du panneau ? Ce serait un changement de navigation. (oui / non)
