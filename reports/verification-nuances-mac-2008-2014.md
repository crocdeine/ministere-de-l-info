# Vérification Mac des nuances municipales 2008 et 2014

- Date : 2026-09-25
- Exécuté par : Claude Code (Mac de Mathias)
- Sources primaires : archives du ministère de l'Intérieur, pages « nuances » de
  [municipales 2008](https://www.archives-resultats-elections.interieur.gouv.fr/resultats/municipales_2008/nuances.php)
  et [municipales 2014](https://www.archives-resultats-elections.interieur.gouv.fr/resultats/MN2014/nuances.php).
  Texte archivé dans `docs/sources-officielles/nuances/2008-municipales_nuances_archives-interieur.md`
  et `docs/sources-officielles/nuances/2014-municipales_nuances_archives-interieur.md`.
- Version machine : `reports/verification-nuances-mac-2008-2014.json`.
- Rien n'a été modifié dans le code, la base ou les classements.

## Récapitulatif (7 codes prioritaires)

| Code | Année | Libellé officiel | Hypothèse du dossier | Confirmée | Bloc actuel | Bloc proposé | Communes T1 | Voix T1 |
|---|---|---|---|---|---|---|---|---|
| LCMD | 2008 | Liste centre-MoDem | centre-MoDem, pas « Communiste et Divers » | oui | GAU | **CENT** | 6 | 13 610 |
| LMAJ | 2008 | Liste de la majorité | majorité UMP, pas « sortante » | oui | exclu (NULL) | **DTE** | 43 | 114 281 |
| LGC | 2008 | Liste gauche-centristes | entente gauche + centristes | oui | DIV | CENT (faible) ou DIV | 1 | 660 |
| LMC | 2008 | Liste majorité-centristes | entente majorité + centristes | oui | CENT | CENT (maintien) ou DTE | 1 | 2 737 |
| LCOM | 2014 | Liste du Parti communiste français | PCF → GAU | oui | GAU | GAU | 63 | 73 978 |
| LUD | 2014 | Liste Union de la Droite | Union de la droite → DTE | oui | DTE | DTE | 42 | 159 734 |
| LUDI | 2014 | Liste Union Démocrates et Indépendants | UDI → CENT | oui | CENT | CENT | 48 | 31 963 |

Les « blocs actuels » sont ceux du code de la branche `claude/exciting-dirac-8mogwe`
(`_NUANCES_MUNI`) ; les poids viennent de la base locale (Hauts-de-France).

## Détail

### LCMD 2008 — « Liste centre-MoDem » → CENT

Le libellé officiel tranche : il s'agit du centre MoDem, pas d'une liste « Communiste et
Divers ». Règle 2 de l'ADR-0010 : la grille INTA1931378J (2020) range LMDM en CENT, même
formation. Contrôle de vraisemblance : la commune où le code pèse le plus est **Arras
(51,2 %)**, ville du maire UDF-MoDem sortant ; viennent ensuite Amiens (5,8 %),
Boulogne-sur-Mer (7,5 %), Villers-Cotterêts (21,7 %), Creil (10,8 %) et Cucq (10,5 %).
Le test qui fige `LCMD = GAU` dans `tests/test_elections_municipales.py` est à corriger.

### LMAJ 2008 — « Liste de la majorité » → DTE

Le libellé désigne la majorité présidentielle (UMP, Nouveau Centre, divers droite
soutenus). La lecture « majorité municipale sortante » est contredite par les données :
à **Calais (36,4 %)**, la mairie sortante était communiste, et la liste LMAJ est celle de la
droite. Les autres communes les plus fortes sont des listes UMP ou Nouveau Centre :
Saint-Quentin (60,8 %), Compiègne (65,7 %), Beauvais (47,3 %), Chantilly (65,4 %),
Amiens (38,9 %), Laon (54,2 %), Albert (66,2 %), Berck (42,4 %), Soissons (32,9 %).
Règle 2 : la grille 2020 classe LLR et LUD en DTE, même famille ; c'est aussi la logique
déjà appliquée à `MAJ 2007 → DTE` en législatives. C'est le code qui pèse le plus :
3e code de 2008 en voix au 1er tour (114 281 voix), et 21 communes (85 435 voix) au
2nd tour. Tant qu'il reste exclu, la droite parlementaire de 2008 est absente des
agrégats DTE.

### LGC 2008 — « Liste gauche-centristes »

Libellé confirmé. Aucune grille officielle ne prévoit d'union gauche-centre. Deux options :
CENT, par symétrie avec LMC (le code se définit par son élément centriste ; certitude
faible), ou maintien de DIV (règle 3). Le poids est négligeable : une seule commune,
Fouquières-lès-Lens (22,2 %, 660 voix au 1er tour et 2 614 au 2nd).

### LMC 2008 — « Liste majorité-centristes »

Libellé confirmé. Proposition : maintien de CENT (règle 3). Alternative : DTE si l'on
retient le poids dominant de l'UMP (grille 2020 : LUD → DTE). Le poids est négligeable :
une seule commune, Béthune (23,7 %, 2 737 voix).

### LCOM, LUD, LUDI 2014

Les trois libellés officiels confirment mot pour mot les reclassements déjà appliqués
par l'ADR-0010 (lot 1) : LCOM → GAU, LUD (« Union de la Droite », et non UDI) → DTE,
LUDI (UDI) → CENT.

## Autres codes vérifiés

Tous cohérents avec le classement actuel :

- **2008** : LEXG (EXG), LCOM « Liste du Parti Communiste » (GAU), LUG (GAU), LSOC (GAU),
  LVEC « Liste des Verts » (GAU), LDVG (GAU), LAUT « Liste inclassable » (DIV),
  LDVD (DTE), LFN (EXD). LREG et LEXD sont des codes officiels, mais absents des
  données HdF et non mappés : sans effet.
- **2014** : LEXG, LFG, LPG, LSOC, LUG, LDVG, LVEC « Liste Europe-Ecologie-Les Verts »,
  LDIV, LMDM, LUC, LUMP, LDVD, LFN, LEXD.

`NC` (2014) ne figure pas dans la liste officielle : il couvre les communes de moins de
1 000 habitants. Son exclusion est conforme.

## Limites

- Les archives ne publient que des libellés courts. Les définitions longues (« conduite
  par un candidat UMP », « … UDFD ») restent de source secondaire (penombre.org,
  france-politique.fr).
- Aucune circulaire de nuances 2008 ou 2014 n'est liée depuis les pages des deux scrutins.
- Les mesures ont été faites sur `data/ministere.duckdb` du 21/06/2026, restaurée d'une
  archive zip, avant l'étape 2 : les poids par code sont valables, les blocs stockés
  dans la base ne sont pas à jour.
- Le périmètre est les Hauts-de-France, avec la lacune connue du Nord en 2008.
- `curl` est bloqué par Cloudflare (403) : les pages ont été lues avec un navigateur.
