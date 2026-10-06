# Synthèse — Équipe de réflexion sur les fonctionnalités et les sources

Date : 2026-10-06 — Directeur : Claude Code — Décideur : Mathias

## Résumé exécutif

- Trois rapports croisés : revue de l'existant (`brainstorm-revue-fonctionnalites-2026-10-06.md`),
  analyses politiques (`brainstorm-analyses-politiques-2026-10-06.md`), sources
  (`brainstorm-sources-2026-10-06.md`).
- Constat central : l'outil montre bien une carte à un instant donné, mais **ne permet ni de suivre
  un territoire, ni de comparer, ni de partager** ; et les élections ne couvrent que les
  Hauts-de-France (30 scrutins chargés sur 56 disponibles dans la source déjà utilisée).
- Proposition : quatre vagues, de la structure (fiche territoire, URL, recherche) vers l'élargissement
  (France entière, autres scrutins) puis les analyses avancées, chacune portée dans la future
  interface web.
- 5 bugs avérés déjà corrigés et fusionnés (PR #3) ; le fichier du Sénat servi en HTML est bloqué (PR #5).
- Décisions de Mathias : 9 questions fermées regroupées au § 4.

## 1. Ce qui a été corrigé tout de suite

« Circos gagnées » → « Circos en tête » ; Conseil d'État : seuil suspendu (et non annulé) ; commune
conservée entre scrutins ; attribution des contours de circonscriptions ; tableau fictif retiré
(PR #3). Téléchargement du Sénat protégé contre une page HTML (PR #5).

## 2. Feuille de route proposée

| Vague | Contenu | Sources | Effort |
|---|---|---|---|
| **A — Socle de navigation** | État de la vue dans l'URL (partage) ; **fiche territoire** (commune puis circonscription : population, historique électoral tous scrutins, économie, élus) ; recherche globale ; page Méthodologie et glossaire (remplace les renvois vers des fichiers `docs/adr/` illisibles pour l'utilisateur) ; export CSV partout avec source, licence et date | Déjà en base | M-L |
| **B — Élargissement des données** | Élections **France entière** (niveau commune) ; européennes, régionales, départementales ; candidatures officielles (parité, sortants, sans date de naissance) ; Filosofi par la source officielle INSEE Mélodi au lieu du fichier republié | data.gouv (lov2), INSEE (LO) | M |
| **C — Analyses indispensables** | Géographie de l'abstention et des votes blancs/nuls ; cartes d'évolution entre deux scrutins ; comparaison commune / département / région / France ; qualifications et triangulaires ; fiche « élu et son élection » ; parité | Base + vague B | S-M chacune |
| **D — Parlement et argent public** | Votes nominatifs des députés (puis sénateurs) ; historique complet des mandats AN (AMO) ; comptes de campagne (CNCCFP) ; finances communales (OFGL) | AN, Sénat, CNCCFP, OFGL | M-L |
| Plus tard | Reports de voix (descriptif d'abord), volatilité, profils de bureaux de vote, croisements socio-électoraux étendus, délinquance (SSMSI), IRCOM | divers | L |

Ordre de construction : chaque vague est réalisée **directement dans la nouvelle interface web**
(la fiche territoire est le premier écran à construire après la page Élections déjà maquettée), pour
ne pas développer deux fois.

## 3. Garde-fous communs (proposés par le politiste)

1. Méthode affichée sous chaque analyse dérivée (calcul, dénominateur, période).
2. Toute comparaison entre scrutins signale les ruptures (périmètre, seuil de nuançage, grille de blocs).
3. Incertitude affichée pour toute estimation ; jamais d'estimation présentée comme une mesure.
4. Corrélation ≠ causalité, rappelé à chaque croisement, avec le nombre de communes.
5. Aucun motif attribué à un comportement (désistement, abstention).
6. Vocabulaire neutre : pas de « bastion », « protestataire », « populiste » ; pas de pronostic ni de
   ciblage.

Écartés : projections, circonscriptions « gagnables », ciblage, sondages, score idéologique calculé,
explications causales, publication de bureaux de vote « suspects ».

## 4. Décisions pour Mathias

| # | Question | Recommandation |
|---|---|---|
| 1 | Adopter la feuille de route en 4 vagues (A → D) | Oui |
| 2 | Adopter les 6 garde-fous communs | Oui |
| 3 | Charger les élections France entière (commune) | Oui |
| 4 | Charger européennes, régionales, départementales, classées selon l'ADR-0010 (reconstruction documentée, aucune grille officielle) | Oui |
| 5 | Remplacer le fichier Filosofi republié par un particulier par la source officielle INSEE | Oui |
| 6 | Reports de voix : rester descriptif (nuage de points), sans estimation statistique pour l'instant | Oui |
| 7 | Écarter la simulation d'un autre mode de scrutin | Oui |
| 8 | Remplacer le « Top 20 » nominatif des députés (scores Datan) par une distribution sans noms + recherche individuelle | Oui (un classement nominatif d'élus par un indicateur tiers est contestable) |
| 9 | Comptes de campagne CNCCFP : 23 jeux sur 26 sans licence déclarée. Les réutiliser au titre du droit de réutilisation des informations publiques (code des relations entre le public et l'administration), avec mention de la source | Oui, après ajout d'une note juridique dans `docs/sources.md` |

Points techniques tranchés par le directeur : votes nominatifs de l'AN d'abord (le Sénat ensuite,
format plus lourd) ; HATVP limité à un lien vers la déclaration publiée ; circonscriptions : statu
quo documenté (le « jeu Etalab » prévu au lot F est en fait celui déjà utilisé) ; partielles :
aucune donnée ouverte depuis 2016, limite affichée.
