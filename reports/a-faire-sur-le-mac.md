# À faire sur le Mac — liste tenue à jour par le directeur

Dernière mise à jour : 2026-09-24

Ce fichier regroupe tout ce qui ne peut être fait que sur le Mac mini (la session cloud n'a ni la base de données, ni accès aux sites du ministère). Suivre les étapes **dans l'ordre**. Chaque étape indique son état :

- ✅ **Prête** : peut être faite maintenant.
- ⏳ **En préparation** : les agents y travaillent ; ne pas la faire encore.

Toutes les commandes se tapent dans le **Terminal**, dans le dossier du projet :

```bash
cd ~/Documents/Docker/ministere-de-l-info
```

---

## Étape 0 — Récupérer la branche de travail ✅ Prête

```bash
git fetch origin
git switch claude/exciting-dirac-8mogwe
git pull
```

Vérification : `git log --oneline -1` affiche un commit récent du directeur.

---

## Étape 1 — Vérifier les codes de nuances 2008/2014 ✅ Prête

C'est Claude Code sur le Mac qui fait tout seul.

1. Lancer Claude Code dans le dossier du projet :
   ```bash
   claude
   ```
2. Taper :
   ```
   /verifier-nuances-2008-2014
   ```
3. Laisser travailler jusqu'au message final « ✅ Vérification terminée ».
4. **Copier la phrase « Message à transmettre au directeur »** et la coller dans la conversation avec le directeur.

Ce que fait la commande : lecture des définitions officielles sur le site d'archives du ministère, mesure du poids de chaque code dans la base (sans rien modifier), écriture du résultat, envoi sur la branche `mac/verification-nuances-2008-2014`. Elle ne modifie ni le code, ni la base, ni les classements.

---

## Étape 2 — Appliquer les corrections à la base ⏳ En préparation

Correctifs des bugs critiques (déjà faits) + nouveaux classements de nuances (en cours). Les commandes exactes seront ajoutées ici quand tout sera fusionné, pour ne relancer les scripts qu'une seule fois.

---

## Étape 3 — Créer l'extrait de base pour les tests ⏳ En préparation

Un script exportera un petit échantillon (département de la Somme, < 5 Mo) pour que les tests fonctionnent partout. Commande à venir.

---

## Étape 4 — Passer l'application en direct sur le Mac (sans Docker) ⏳ En préparation

Procédure pas à pas avec point d'arrêt, Docker gardé en secours 2 semaines. À venir.

---

## Étape 5 — Tester la mise à jour de la base ⏳ En préparation

Test réel du script de mise à jour corrigé. À faire après la fusion dans `main`.

---

## Étape 6 — Recharger le Sénat après les sénatoriales du 27/09 ⏳ En préparation

Après la refonte du module Législatif (en cours). Procédure à venir.
