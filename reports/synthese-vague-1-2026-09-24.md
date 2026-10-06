# Synthèse — Vague 1 d'agents (2026-09-24)

**Directeur** : Claude Code (session cloud) — **Décideur** : Mathias
**Branche** : `claude/exciting-dirac-8mogwe` (non fusionnée dans `main`)
**Gouvernance** : actée dans CLAUDE.md (commit `dca1ced`)

---

## 1. Agents lancés et livrables

| # | Agent | Livrable | Statut |
|---|---|---|---|
| 1 | Vérification du code | `reports/audit-code-2026-09-24.md` — 3 critiques, 10 importants, 18 mineurs | ✅ |
| 2 | Recherche de données (nuances) | `reports/verification-nuances-2026-09-24.md` — 25 questions | ✅ |
| 3 | Outillage Claude Code | 8 agents `.claude/agents/`, 3 skills recalés, hook SessionStart cloud, `reports/outillage-claude-2026-09-24.md` | ✅ fusionné |
| 4 | Documentation | README, `docs/*` à jour, ADR 0007-0009 rétroactifs, CLAUDE.md (faits) | ✅ fusionné |
| 5 | Infra | Checksum DB corrigé (51 tests shell), uv figé dans l'image GHCR, `reports/infra-2026-09-24.md` | ✅ fusionné |
| 6 | R&D exécution Mac | `reports/rd-execution-mac-2026-09-24.md` — recommande le natif uv | ✅ |
| 7 | R&D feuille de route | `reports/rd-feuille-de-route-2026-09-24.md` — 42 pistes, 3 scénarios, 14 questions | ✅ |
| 8 | Expérience utilisateur | `reports/ux-2026-09-24.md` — 14 quick wins, 13 fonctionnalités, 12 questions | ✅ |
| 9 | Correctifs ETL critiques | C1, C2, C3 corrigés + 20 tests en mémoire | ✅ fusionné |

## 2. Ce qui a été corrigé sans attendre (bugs avérés, sans choix de fond)

| Correctif | Effet | Fichiers |
|---|---|---|
| C2 — relance des référentiels | Ne détruit plus les 67 nuances municipales | `etl/schema_elections.py` (source unique des 3 jeux de nuances) |
| C3 — `INSERT OR IGNORE` | Une correction de classement est désormais réellement appliquée | `scripts/load_elections_municipales.py` |
| C1 — `v_listes_commune_muni` | Une ligne par liste (plus de fusion de listes de même nuance), sauf limite 2008 | `scripts/migrations/0007_add_municipales_views.py`, `viz/elections_muni_queries.py` |
| Checksum DB | Fin du retéléchargement systématique ; vérification avant remplacement | `deploy/install.sh`, `deploy/update.sh`, `scripts/publish_db.sh`, `scripts/download_db.sh` |
| Image GHCR | `uv` figé en 0.11.16 | `deploy/Dockerfile` |

**À relancer sur le Mac après fusion dans `main`** (ordre impératif) :
1. `uv run python scripts/init_elections_schema.py`
2. `uv run python scripts/load_elections_municipales.py`
3. `uv run python scripts/migrations/0007_add_municipales_views.py`
4. Contrôles SQL fournis dans le rapport de l'agent ETL (reproduits en annexe A).
5. Test réel de `deploy/update.sh` : un retéléchargement unique attendu, puis « déjà à jour ».

## 3. Décisions pour Mathias — regroupées en 8 lots

Chaque lot a une recommandation du directeur. Répondre « lot N : OK » suffit ; le détail ligne par ligne reste disponible dans le rapport source.

| Lot | Sujet | Recommandation du directeur | Détail |
|---|---|---|---|
| **1** | **Classements municipaux confirmés par les grilles officielles 2020/2026** : LCOM → GAU, LUDI → CENT, LUD → DTE (+ LUD 2026), LECO → DIV | **Appliquer** (c'est l'application stricte de la règle ADR-0005 « classement officiel de l'époque ») | nuances Q1-Q4, Q9 |
| **2** | **Codes 2008/2014 reconstruits sur sources secondaires** : LCMD → CENT, LMAJ → DTE, LGC, LMC | **Vérification manuelle d'abord** (10 min sur archives-resultats-elections.interieur.gouv.fr, bloqué depuis le cloud) | nuances Q5-Q8, Q10 |
| **3** | **Écologistes et cas historiques** : ECO 2024 → DIV ; ECO 2002-2012 → DIV ; ECO 2017/2022 GAU ; UDI, Lepage, PRV, CPNT | **Appliquer ECO 2024 → DIV** (grilles concordantes) ; les autres : trancher cas par cas | nuances Q11-Q17 |
| **4** | **Législatif** : FI/LFI-NUPES → GAU ; LFI-NFP (2024) ; RRDP → GAU ; Sénat GEST → GAU, RDPI → CENT ; clé (groupe, législature) + ADR ; refonte du modèle « un député = une ligne » (audit I7) | **Oui à la clé (groupe, législature) et à l'ADR**, avant le rechargement post-sénatoriales du 27/09 | nuances Q18-Q23, audit I7, feuille de route Q5 |
| **5** | **ADR de révision de l'ADR-0005** (blocs officiels dès 2020, règle écologistes, définitions LCMD/LMAJ) + ajout de `type_scrutin` à la clé des nuances (audit M5) | **Oui** — l'ADR-0005 contient aujourd'hui des affirmations factuellement fausses | nuances Q24-Q25, audit M5 |
| **6** | **Exécution sur le Mac** : passer de Docker/OrbStack au natif uv + LaunchAgent (Docker gardé en repli 2 semaines) ; Dockerfile unique ; `.streamlit` dans l'image | **Natif uv** (58/70 contre 49/70) — mais d'abord répondre : l'app installée sert-elle à d'autres que toi ? | rd-mac Q1-Q3, infra D3-D4 |
| **7** | **Qualité / CI** : CI sur les branches `claude/**` ; base échantillon Parquet < 5 Mo committée (Somme) pour tests hermétiques ; montée Streamlit 1.64 / DuckDB 1.5.4 ; typage (pyright ou ty) | **Oui** CI élargie + base échantillon (prérequis de tout le reste) ; pyright | infra D5-D6, feuille de route Q9-Q11 |
| **8** | **Orientation produit** : scénario « Consolider puis Approfondir » ; HdF conservé 6 mois ; UX : URL partageables → page Méthodologie → fiche commune ; quick wins UX ; Filosofi 2023 avec rupture de série | **Oui** au scénario A puis C et aux quick wins UX ; périmètre HdF maintenu | feuille de route Q1-Q4, ux §7 |

## 4. Proposition de vague 2 (après arbitrage)

| Ordre | Tâche | Agent | Dépend de |
|---|---|---|---|
| 1 | Base échantillon + CI élargie + tests hermétiques | ingenieur-infra + verificateur-code | Lot 7 |
| 2 | Application des classements validés + ADR de révision | ingenieur-etl + documentaliste | Lots 1, 3, 5 |
| 3 | Modèle Législatif (groupe, législature) + rechargement Sénat post-27/09 | ingenieur-etl | Lot 4 |
| 4 | Quick wins UX (contraste, erreurs base absente, onglets paresseux, pondération participation, croisement éco T1, RSA en taux) | developpeur-ui | Lot 8 (en partie des bugs : peuvent démarrer) |
| 5 | Bugs importants restants de l'audit (I1-I6, M2) | ingenieur-etl / developpeur-ui | — |
| 6 | Migration native Mac (essai en parallèle sur port 8502) | ingenieur-infra | Lot 6 |

## 5. Constats transverses à retenir

- La CI ne pouvait détecter aucun des bugs critiques : aucune vue SQL n'est testée sans la base réelle. La base échantillon est le chantier qui débloque tout le reste.
- Les sénatoriales du 27/09/2026 rendront la composition du Sénat obsolète dès octobre.
- Filosofi 2022 ne sera jamais produit ; Filosofi 2023 n'est pas comparable (nouvelle méthode).
- Corrections à l'état des lieux : les tags `v0.4.2` et `v0.4.3` existent (sans release GitHub) ; le tag `v0.2` n'existe pas sur le dépôt distant.
- `docs/schema-elections.md` reste en retard (5 vues, 149 nuances) : à traiter en vague 2.

---

## Annexe A — Contrôles SQL après correctifs C1-C3

```sql
-- Nuances par année : 2008=12, 2014=17, 2020=19, 2026=19 (total 216 avec pres + legi)
SELECT annee, COUNT(*) FROM nuances_harmonisees GROUP BY 1 ORDER BY 1;

-- Aucune liste dupliquée (attendu : 0 ligne)
SELECT annee, tour, code_commune, no_panneau, COUNT(*)
FROM v_listes_commune_muni WHERE no_panneau IS NOT NULL
GROUP BY ALL HAVING COUNT(*) > 1;

-- Conservation des voix (les deux sommes doivent être égales)
SELECT (SELECT SUM(voix) FROM v_listes_commune_muni),
       (SELECT SUM(voix) FROM resultats_candidats rc
        JOIN elections e USING (id_election) WHERE e.type_scrutin = 'muni');
```
