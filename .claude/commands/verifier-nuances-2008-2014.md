---
description: Vérifie sur les archives officielles du ministère de l'Intérieur le sens des codes de nuances municipales 2008 et 2014, mesure leur poids dans la base locale, puis pousse le résultat sur GitHub pour le directeur de projet.
---

# Vérification des nuances municipales 2008 et 2014 (à exécuter sur le Mac)

Tu es Claude Code sur le Mac de Mathias. Tu exécutes cette mission **de bout en bout, en autonomie**, sans demander de confirmation à Mathias sauf blocage réel. Réponds en français. Mathias est novice en code : à la fin, donne-lui un résumé de 5 lignes, sans jargon.

Le directeur de projet (une session Claude Code dans le cloud) ne peut pas accéder au site du ministère (proxy) ni à la base locale. Ton rôle : produire la preuve, la mettre en forme, et la lui transmettre par GitHub. **Tu ne modifies ni le code, ni la base, ni les classements** : c'est le directeur qui appliquera les corrections après lecture de ton résultat.

## Contexte à lire d'abord

- `CLAUDE.md`
- `reports/verification-nuances-2026-09-24.md`, §2 (codes 2008 et 2014, sources secondaires, hypothèses à confirmer)
- `docs/adr/0005-nuances-et-blocs-officiels.md` et, s'il existe, `docs/adr/0010-revision-nuances-et-blocs.md` (doctrine de classement)
- Les mappings actuels : `_NUANCES_MUNI` dans `src/ministere_de_l_info/etl/schema_elections.py`

## Étape 1 — Préparer une branche dédiée

```bash
git fetch origin
git switch -c mac/verification-nuances-2008-2014 origin/claude/exciting-dirac-8mogwe
```

Si la branche existe déjà (relance), fais `git switch mac/verification-nuances-2008-2014 && git pull --ff-only`.

## Étape 2 — Récupérer les définitions officielles

Sources primaires, dans cet ordre :

1. https://www.archives-resultats-elections.interieur.gouv.fr/resultats/municipales_2008/index.php (chercher la page ou le document des nuances 2008)
2. https://www.archives-resultats-elections.interieur.gouv.fr/resultats/MN2014/nuances.php
3. À défaut, tout document officiel du ministère (circulaire, grille de nuances, notice) trouvé depuis ces pages ou via une recherche web ciblée.

Utilise WebFetch ; si la page est mal rendue, `curl -sL` puis extraction du texte. Pour **chaque code 2008 et 2014** présent dans `_NUANCES_MUNI` ou dans les données (voir étape 3), relève le **libellé officiel exact** et la **définition** telle qu'écrite par le ministère.

Priorité absolue : **LCMD, LMAJ, LGC, LMC (2008)**, puis **LCOM, LUD, LUDI (2014)**.

Archive les preuves : enregistre le texte utile de chaque page officielle consultée (pas le HTML complet) dans `docs/sources-officielles/nuances/2008-municipales_nuances_archives-interieur.md` et `docs/sources-officielles/nuances/2014-municipales_nuances_archives-interieur.md`, avec l'URL et la date de consultation en tête.

## Étape 3 — Mesurer le poids de chaque code dans la base locale (lecture seule)

```bash
uv run python - <<'EOF'
import duckdb
from pathlib import Path
import os
db = os.environ.get("MINISTERE_DB_PATH", str(Path("data/ministere.duckdb")))
con = duckdb.connect(db, read_only=True)
print(con.execute("""
    SELECT e.annee, e.tour, rc.nuance,
           COUNT(DISTINCT rc.code_commune) AS nb_communes,
           SUM(rc.voix) AS voix
    FROM resultats_candidats rc
    JOIN elections e USING (id_election)
    WHERE e.type_scrutin = 'muni' AND e.annee IN (2008, 2014) AND rc.nuance IS NOT NULL
    GROUP BY ALL ORDER BY e.annee, e.tour, voix DESC
""").pl())
EOF
```

Relève aussi, pour LCMD, LMAJ, LGC, LMC (2008), les 10 communes où le code pèse le plus (nom de commune via `geographies_communes`) : cela permet un contrôle de vraisemblance (ex. une liste « majorité » UMP dans une ville connue pour être à droite en 2008).

## Étape 4 — Écrire le résultat dans deux fichiers

1. `reports/verification-nuances-mac-2008-2014.json` — format strict, lisible par machine :

```json
{
  "date_verification": "AAAA-MM-JJ",
  "execute_par": "Claude Code (Mac de Mathias)",
  "codes": [
    {
      "code": "LCMD",
      "annee": 2008,
      "libelle_officiel": "…",
      "definition_officielle": "…",
      "source_url": "…",
      "source_type": "officielle | secondaire | introuvable",
      "hypothese_dossier": "…(ce que disait reports/verification-nuances-2026-09-24.md)…",
      "confirme": true,
      "bloc_actuel_projet": "GAU",
      "bloc_propose_selon_doctrine": "CENT",
      "nb_communes_t1": 0,
      "voix_t1": 0,
      "commentaire": "…"
    }
  ],
  "limites": ["…"]
}
```

2. `reports/verification-nuances-mac-2008-2014.md` — la même chose lisible par un humain : tableau récapitulatif, puis détail des 7 codes prioritaires, puis la liste des autres codes vérifiés, puis les limites.

`bloc_propose_selon_doctrine` : applique la doctrine de l'ADR-0010 (ou, à défaut, de l'ADR-0005) — tu **proposes**, tu n'appliques pas.

## Étape 5 — Transmettre au directeur

```bash
uv run pre-commit run --files reports/verification-nuances-mac-2008-2014.* docs/sources-officielles/nuances/*archives-interieur.md || true
git add reports/verification-nuances-mac-2008-2014.json reports/verification-nuances-mac-2008-2014.md docs/sources-officielles/nuances/*archives-interieur.md
git commit -m "docs(nuances): vérification officielle des codes municipaux 2008/2014 (Mac)"
git push -u origin mac/verification-nuances-2008-2014
```

(Si le pre-commit reformate des fichiers, refais `git add` puis un nouveau commit — gotcha 14 de CLAUDE.md.)

Si le push échoue, ne force rien : affiche à Mathias le contenu du fichier JSON dans un bloc de code pour qu'il le colle dans la conversation avec le directeur.

## Étape 6 — Message final à Mathias

Termine par exactement ce format :

```
✅ Vérification terminée — branche mac/verification-nuances-2008-2014 poussée.
Message à transmettre au directeur :
« Vérification Mac des nuances 2008/2014 poussée sur mac/verification-nuances-2008-2014 (commit <hash>). »
Résumé : <3 lignes max : codes confirmés / infirmés / introuvables>
```

Puis reviens sur la branche de départ : `git switch -`.
