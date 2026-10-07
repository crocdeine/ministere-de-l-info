# Mission : vague A, lot 3 — fiche territoire « commune »

**Agent** : ingenieur-etl (export) + developpeur-ui · **Branche** : feat/web-fiche-commune
**Base** : origin/main (après A1, A2) · **Complexité** : L (4-6 jours)
**Décision d'origine** : feuille de route, vague A ; `reports/synthese-brainstorm-fonctionnalites-2026-10-06.md` § 2
**Dépendances** : A1, A2. **Débloque** : A4 (destination de la recherche), A6 (exports de la fiche).

## Objectif
Une page par commune qui répond à « que sait-on de ce territoire ? » : identité (département,
EPCI, circonscription), population 2013/2018/2023, historique électoral de tous les scrutins
chargés (participation et voix par bloc, en % des exprimés), détail par bureau de vote,
économie (Hauts-de-France seulement, mention « n.d. » ailleurs) et élus (députés et sénateurs
du territoire).

## Hors périmètre
- Fiche circonscription (vague A, lot ultérieur à planifier) ; fiche département/région.
- Détail par candidat ou par liste (ADR-0015, point 5) ; comparaison avec d'autres territoires (vague C).
- Toute estimation, tendance calculée ou commentaire rédigé.

## Motifs à reproduire
| Catégorie | Source | Motif |
|---|---|---|
| Population | vue `v_population_commune` | valeurs officielles, années explicites |
| Économie | vue `v_economie_commune`, `v_economie_sociale_commune` | classes fixes par indicateur |
| Élus | vue `v_elus_actuels`, ADR-0011 | bloc du groupe par législature ; pas de date de naissance (ADR-0013) |
| Communes fusionnées | `.claude/plans/2026-10-07-communes-fusionnees.plan.md`, table `communes_passage` | mention de rattachement |
| Export | `src/ministere_de_l_info/export_web/` (A1) | un fichier par département, `null` ≠ 0 |

## Fichiers à changer
| Fichier | Action | Raison |
|---|---|---|
| `src/ministere_de_l_info/export_web/fiches.py` | créer | fichier par département : identité, population, élections (commune et BV), économie, élus |
| `tests/test_export_web.py` | compléter | sommes BV = commune ; Paris/Lyon/Marseille (arrondissements) ; commune sans économie = `null` |
| `web/src/pages/FicheCommune.tsx` + composants | créer | page, tableau accessible au clavier, graphique d'évolution |

## Tâches
### 1. Export par département
- **Action** : fichiers de ≈ 0,9 Mo médian (communes) et ≈ 2,2 Mo médian (BV), mesurés pour
  l'ADR-0015 ; le BV dans un fichier distinct chargé seulement à l'ouverture du détail.
- **Valider** : `uv run pytest tests/test_export_web.py -q` ; plus gros fichier < 8 Mo.
### 2. Page
- **Action** : en-tête (nom, code INSEE, département) ; tableau des scrutins (tri, n.d.) et
  graphique par bloc ; détail BV repliable ; élus ; économie ; source et licence sous chaque bloc.
- **Valider** : `npx vitest run` ; parité de 3 communes avec Streamlit (Amiens 80021, une commune
  hors HdF, Paris 75056).
### 3. Accessibilité
- **Action** : toutes les valeurs de la carte accessibles par le tableau ; titres hiérarchisés.
- **Valider** : navigation complète au clavier, vérifiée à la main.

## Garde-fous de neutralité
1. Méthode affichée : dénominateur (% des exprimés), classement par scrutin (légende ADR-0013).
2. Ruptures signalées : changement de grille de blocs, de type de scrutin, commune fusionnée ou
   redécoupage de circonscription, sur la ligne concernée.
3. Aucune tendance calculée ni qualificatif (« bastion », « fief », « basculement ») ; pas de
   pronostic. 5. Aucun motif prêté à l'abstention. 6. Libellés de blocs uniquement.

## Contraintes du projet
Communes aux fiches (base copiée sur le disque externe, commits fréquents, pas de push).

## Validation finale
```bash
uv run ruff check . && uv run ruff format --check . && uvx pyright@1.1.408
uv run pytest -m "not slow and not network"
cd web && npx tsc --noEmit && npx vitest run && npm run build
```

## Risques
| Risque | Probabilité | Parade |
|---|---|---|
| Codes communes historiques (fusions) | moyenne | s'appuyer sur `code_commune_origine` et `communes_passage` |
| Économie HdF seulement : confusion | moyenne | mention explicite « disponible pour les Hauts-de-France » |
| Élus : rattachement commune → circonscription | moyenne | `ST_Within` sur `geographies_circonscriptions` (gotcha 10) |

## Acceptation
- [ ] Fiche ouverte depuis la carte et depuis une URL (A2)
- [ ] Parité chiffrée avec Streamlit sur 3 communes
- [ ] Validation visuelle de Mathias
- [ ] Rapport (résumé ≤ 10 lignes), questions fermées listées

## Si l'option B n'est pas retenue
Option C : la fiche interroge les Parquet par code commune (même affichage, tests SQL côté TS).
Option A : page Streamlit supplémentaire, détail BV par requête directe.
