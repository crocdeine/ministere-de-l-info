# Recherche : Ruflo, passerelle vers Antigravity, compétences partagées, images, quotas

Date : 2026-10-09 · Lecture seule : rien installé, aucune configuration modifiée. Appels `agy` : `--help`, `plugin --help`, `mcp --help`, `models`, `changelog`, `-p "/usage"` et 2 `-p` triviaux (Flash low, mode plan, sans outil). Sources web citées en fin de document ; les chiffres de tiers sont signalés comme tels.

## Résumé

1. **Ruflo ne route pas vers Antigravity** : sa documentation mentionne « Claude, GPT, Gemini, Cohere, Ollama » (appels API, failover), jamais `agy`. Il ne répond pas à la demande « se brancher à Antigravity ».
2. Ruflo est lourd (README : 98 agents, 60+ commandes, 30 skills, 314 outils MCP, hooks, daemon, écrit `.claude/`, `.claude-flow/`, `CLAUDE.md`) et a un passif sécurité sérieux : CVE-2026-59726 (CVSS 10, RCE sans authentification via le pont MCP, corrigé en 3.16.3), script `preinstall` obfusqué dans les versions 3.1.0-alpha.55 à 3.5.2, audits tiers contestant l'effectivité de nombreuses fonctions. **Déconseillé.**
3. Des ponts MCP maintenus par la communauté existent déjà pour `agy` (agy-bridge, MIT, 6 outils ; claude-to-agy, 1 outil). Mais l'appel direct `agy -p --output-format json` via Bash, déjà possible, coûte moins de contexte et moins de risque. **Recommandation : un skill Claude + un script shell de ~30 lignes, pas de MCP, pas de Ruflo.**
4. « Identique » est atteignable pour les **règles et les skills** (même `SKILL.md`, via liens symboliques), pas pour les sous-agents, hooks ni commandes. Constat important de ce jour : `agy` **ne voit actuellement ni notre règle `.agents/rules/projet.md` ni `~/.agents/skills`** (voir §3).
5. Images : un sous-agent intégré `image-generator` existe (confirmé par `agy -p`) ; **aucun outil vidéo/Veo** visible. Utilité pour ce projet : faible (neutralité, pas d'illustration éditoriale).
6. Gain réaliste en jetons Claude : 15 à 30 % sur les tâches déléguables (recherche, gros fichiers, brouillons), et net négatif si la vérification n'est pas bornée. Quota Gemini restant : **24 %** au 2026-10-09 (reset 2026-10-11 21:17 UTC) ; Claude/GPT via `agy` : 100 %.

---

## 1. Ruflo (ruvnet, ex claude-flow)

| Point | Constat | Fiabilité |
|---|---|---|
| Nom et version | Dépôt `ruvnet/ruflo` (renommé depuis claude-flow, ~février 2026) ; paquet npm et CLI encore nommés `claude-flow`. Une source tierce date la v3.32.22 du 2026-07-27 ; la page GitHub n'affiche pas de release. Version actuelle (octobre) non confirmée : `npm view claude-flow version` à lancer avant toute décision. | Moyenne |
| Licence | MIT (README, jsDelivr) ; Snyk liste aussi ISC (dépendances probables). | Bonne |
| Maintenance | Très active (≈ 9 000 commits, 74 k étoiles selon la page GitHub), mais cadence de publication extrême (plus de 1 500 releases selon un article tiers) : instabilité probable. | Moyenne |
| Ce que `init`/le plugin installe | README : « 98 agents, 60+ commandes, 30 skills, MCP server, hooks, daemon » ; écrit `.claude/`, `.claude-flow/`, `CLAUDE.md`, helpers, settings ; enregistre un serveur MCP (314 outils annoncés). Installation côté Claude Code : `/plugin marketplace add ruvnet/ruflo` puis `/plugin install ruflo-core@ruflo` (Claude Code ≥ 2.1.287). Mémoire (base) : non précisé par le README. | Bonne (README) |
| Télémétrie | Non documentée ; l'issue #1375 n'en fait pas état, mais signale des processus d'arrière-plan persistants et des fichiers résiduels (`.swarm/`, `.hive-mind/`). | Faible |
| Sécurité | CVE-2026-59726 (CVSS 10.0, Noma Labs, avant 3.16.3) : pont MCP non authentifié exposé au réseau par défaut, 233 outils dont exécution de commandes. Issue #1375 (mars 2026) : preinstall obfusqué supprimant des entrées du cache npx (versions 3.1.0-alpha.55 à 3.5.2), injection SQL corrigée en 3.5.40, allégation (contestée par le mainteneur) d'instructions cachées dans les descriptions d'outils ; un audit d'avril affirme que vérification de signature Raft factice et fonctions « stub ». Divulgation tierce de janvier 2026 sur un mécanisme IPFS/IPNS d'injection de comportements : non confirmé comme corrigé. | CVE : forte ; le reste : allégations tierces, à ne pas tenir pour établi |
| Routage vers Antigravity/Gemini | Gemini cité comme fournisseur API parmi 5 ; aucune mention d'Antigravity ni de `agy` dans le README. Aucune documentation officielle trouvée sur un pont `agy`. | Bonne (absence) |

### Coût en contexte et conflits (constat local, mesure directe impossible en lecture seule)
- État actuel de la machine : restes de claude-flow déjà actifs. `~/.claude/commands/` contient **88 fichiers** (analysis, automation, github, hooks, monitoring, optimization, sparc), repris dans la liste des skills de chaque session ; `~/.claude/agents/` en compte 23 ; `~/.claude/settings.json` autorise `mcp__claude-flow__*` et `npx claude-flow*`. Ce coût fixe est donc **déjà payé sans bénéfice** (Ruflo n'est pas installé). Un nettoyage serait la première économie de jetons concrète (décision Mathias, question 2).
- Ruflo complet ajouterait une centaine d'agents, 30 skills et 314 outils MCP (chargés à la demande via ToolSearch, mais noms listés), plus un `CLAUDE.md` réécrit : conflit direct avec le `CLAUDE.md` du projet (« Mathias décide »), avec les agents du projet (`.claude/agents/`), avec les 100+ skills ECC, et chevauchement avec ECC (`ecc:council-multi-model`, `ecc:model-route`, `ecc:multi-*`), ponytail et caveman (hooks de session). Les hooks Ruflo se cumulent avec ceux de ECC/ponytail/caveman à chaque outil.

## 2. Alternatives pour déléguer à `agy`

| Option | Effort | Fiabilité | Contexte Claude | Sécurité |
|---|---|---|---|---|
| **A. Skill Claude + script shell appelant `agy -p --output-format json`** | ~30 lignes de shell + un `SKILL.md` de ~40 lignes | Bonne : enveloppe JSON documentée (`status`, `response`, `usage`, `conversation_id`), `--print-timeout`, code retour non nul si échec | Minimal : le skill n'est chargé qu'à l'appel (la description seule est listée) ; sortie tronquée par le script | Maîtrisée : `--mode plan --sandbox` + settings à liste blanche déjà posés ; jamais `--dangerously-skip-permissions` |
| B. agy-bridge (sshahzaiib, MIT, 57 étoiles, 37 commits, `npx -y agy-bridge`) | Faible (une commande), mais dépendance npx exécutée à chaque lancement | Bonne sur le papier : routage par type de tâche, repli sur quota 429, `follow_up` par session, troncature à 50 000 caractères | 6 outils MCP à décrire (coût non publié) | **Défaut dangereux : `AGY_SKIP_PERMISSIONS=true`** (passe `--dangerously-skip-permissions`) et `AGY_SANDBOX=false`. Projet jeune, 1 mainteneur. À n'utiliser qu'en forçant les deux variables et en épinglant la version |
| C. claude-to-agy (rauls-kjarners) | Faible (script Python + `claude mcp add`) | Un seul outil `delegate_to_agy`, timeout 600 s | 1 outil : léger | Même vigilance sur les permissions ; non audité |
| D. MCP maison de ~100 lignes | 0,5 jour (SDK MCP Python, subprocess `agy -p`, troncature, gestion du process group) | Dépend de nous | 1 outil | Maîtrisée |
| E. `agy --remote-control` / `agy remote-control start` | Hors sujet : daemon qui permet de piloter une session `agy` à distance (depuis un autre appareil), pas une API de délégation | — | — | Surface d'attaque supplémentaire : à éviter |
| F. ACP/A2A | Le brainstorm du 10-07 note « plus d'ACP » ; `agy --help` ne propose ni ACP ni A2A. Seul `--input-format stream-json` permet un processus multi-tours. | — | — | — |

Verdict : **A** (déjà possible, c'est ce que préconisait le brainstorm), éventuellement **D** si on veut un outil natif ; **B/C** seulement si Mathias veut du « prêt à l'emploi » et accepte de relire le code.

Squelette de A (non exécuté) : voir le plan en §7.

## 3. Compétences partagées : ce qui est vraiment possible

Constats d'aujourd'hui (test `agy -p`, Flash low, depuis le dépôt, sans outil) : le contexte d'`agy` ne contient que la règle `user_global` et les skills intégrés `agy-customizations` et `antigravity-guide`. **Il ne voit pas** notre `.agents/rules/projet.md` ni les 36 skills de `~/.agents/skills/` (ceux-ci sont les cibles des liens symboliques de `~/.claude/skills/`).

Causes documentées (docs Antigravity « Rules » et « Skills ») :
- Chaque `.md` de `.agents/rules/` doit avoir un frontmatter avec `trigger` valide (`always_on`, `model_decision`, `glob`, `manual`) ; **sans frontmatter la règle est silencieusement ignorée**. Notre `projet.md` commence par un titre : il est donc ignoré. Correctif de 3 lignes (`trigger: always_on`) ; attention : `always_on` injecte tout le contenu à chaque tour, préférer `model_decision` avec une description.
- `AGENTS.md` et `GEMINI.md` (à la racine ou dans `.agents/`) sont lus sans frontmatter, en `always_on`. Limites : 24 000 octets par fichier, budget commun de 20 000 jetons pour les règles globales et `always_on`. Notre `CLAUDE.md` est trop gros pour être injecté tel quel ; un `AGENTS.md` court qui pointe vers `CLAUDE.md` (lecture à la demande) est le bon format.
- Skills d'espace de travail : `<projet>/.agents/skills/<nom>/SKILL.md` ; globaux CLI : `~/.gemini/antigravity-cli/skills/` ; `description` obligatoire, `name` optionnel. Format compatible avec le nôtre (frontmatter `name`/`description` + corps). Aucune lecture documentée de `.claude/skills/` ni de `~/.agents/skills/`.
- `agy plugin import claude` : **non documenté** dans les pages consultées (Marketplace, Plugins) ; l'aide du CLI ne donne que « Import plugins from gemini or claude ». Son effet (composants convertis) est inconnu : à tester en environnement jetable (§7, étape 4) avant tout usage.

Ce qu'on peut rendre identique, et les limites :

| Élément | Identique ? | Moyen | Limite |
|---|---|---|---|
| Skills du projet (8 : projet-conventions, data-viz-politique, economie-tokens, design-system-mi, insee-duckdb-loader, latex-rapport-fr, streamlit-duckdb-patterns, + skill-creator/etc.) | Oui | Liens symboliques `.agents/skills/<n>` -> `../../.claude/skills/<n>` (à tester : le chargeur d'`agy` suit-il les liens ?) ; sinon copie par script | Les skills qui appellent des outils propres à Claude (Task, ToolSearch, MCP) ne marchent pas ; chaque skill chargé coûte des jetons Gemini aussi |
| Skills globaux (`~/.agents/skills`, 36) | Oui, mais à ne pas tous exposer | Lien `~/.gemini/antigravity-cli/skills/<n>` pour une sélection | Charger 36 skills = bruit ; en choisir 5 à 8 |
| Règles / CLAUDE.md | Partiellement | `AGENTS.md` court pointant vers `CLAUDE.md` ; ou `@[label](path)` (inclusion documentée, soumise aux 24 ko) | Pas de fusion automatique ; dérive possible |
| Sous-agents (`.claude/agents/*.md`, champ `tools:` à la Claude) | Non fiable | `agy` a ses propres `agents/*.md` avec champs `skills:`, `rules:`, `plugins:` ; format voisin mais outils différents | Noms d'outils différents (Read/Grep/Bash vs `read_file`...) ; à réécrire, pas à copier |
| Hooks, commandes slash, plugins ECC | Non | Plugin `agy` avec `hooks.json` possible, sémantique différente | Ne pas viser l'identité |
| Permissions | Non | Settings propres à `agy` (`permissions.allow/ask/deny`, déjà posés) | Syntaxe différente de Claude Code |

Conclusion : viser « mêmes conventions, mêmes sources de vérité » (skills du projet + `AGENTS.md` court), pas « mêmes agents ». Un réflexe : un test de fumée `agy -p "liste tes skills"` après chaque changement.

## 4. Images et vidéos

- **Constaté** (`agy -p`, 2026-10-09) : sous-agent intégré `image-generator` ; pas d'outil `generate_image` direct ni d'outil Veo exposé. Le changelog 1.2.16 confirme : les requêtes d'image passent par ce sous-agent, qui écrit le prompt, vérifie chaque résultat (jusqu'à 3 essais) et enregistre dans les artefacts de la conversation. Modèles : Nano Banana / Nano Banana Pro d'après le blog Antigravity (selon accès du compte). **Vidéo : aucune source officielle trouvée** pour le CLI ; ne pas compter dessus.
- **Appel non interactif** (non exécuté, pour ne rien générer) : `agy -p "Génère une image : <description>. Enregistre-la dans <dossier>" --output-format json --mode accept-edits` en `--dangerously-skip-permissions` n'est pas nécessaire si l'écriture est dans le dossier autorisé (`write_file(<dossier>)` dans les settings de mission). Le chemin exact des artefacts est dans `~/.gemini/antigravity-cli/brain/<conversation_id>/` (à vérifier au premier essai).
- **Conditions d'usage** : pas de page officielle trouvée sur la propriété des images générées par Antigravity. Les Conditions additionnelles de l'API Gemini disent que Google ne revendique pas la propriété du contenu généré, peut produire des sorties similaires pour d'autres, et que l'utilisateur en est responsable (mention d'attribution possible selon la loi). Une source tierce affirme qu'Antigravity n'incorpore pas de filigrane SynthID (observation d'un utilisateur, non officielle). À lire : antigravity.google/terms et ai.google.dev/terms avant toute publication.
- **Utilité pour ce projet** : faible. Outil de data-visualisation politique neutre : les cartes et graphiques sont générés par Plotly/Folium à partir des données. Illustrations d'ambiance, portraits ou « photos » d'élus seraient risqués (image trompeuse, neutralité, droit à l'image). Usages défendables : icônes ou pictogrammes abstraits pour le design system, visuels de la page d'accueil ou du README sans figure humaine, à valider par Mathias, avec mention « généré par IA » et sans prétention documentaire. Pour une vraie vidéo ou des captures animées, mieux vaut les outils existants (captures d'écran, `ecc:manim-video`, `ecc:remotion-video-creation`).
- **Risques** : fausse impression de source (image « type affiche électorale »), reconnaissance de personnalités, dérive éditoriale, licence floue ; règle proposée : aucune image générée dans l'application ni dans les rapports sans décision explicite de Mathias.

## 5. Où Antigravity/Gemini est aussi bon, meilleur ou moins bon

Sources chiffrées = agrégateurs tiers (à recouper avec les fiches de modèles des éditeurs) ; aucun benchmark de Gemini 3.8 Flash comparé à Claude trouvé hors communiqué de Google (« DeepSWE v1.1 », non vérifié).

| Tâche | Verdict | Pourquoi / preuve |
|---|---|---|
| Codage général | À peu près égal (Gemini 3.1 Pro 80,6 % vs Opus 4.6 80,8 % sur SWE-bench Verified, selon un comparatif tiers) | Prix Gemini 3.1 Pro 4 à 7 fois inférieur côté API ; notre cas passe par les quotas de l'abonnement |
| Contexte très long (≥ 500 k jetons) | **Claude meilleur** sur la récupération multi-aiguilles (MRCR v2 à 1 M : Opus 4.6 ≈ 76-78 %, Gemini 3.1 Pro ≈ 18-26 % selon sources) | Contre l'intuition « Gemini = contexte long » ; à 128 k, Gemini est bon (≈ 85 %). Notre dépôt tient largement sous 128 k par mission |
| Multimodal (lecture de PDF, captures, tableaux scannés) | Plausiblement meilleur ou égal, et gratuit côté quota Claude | À tester sur 3 PDF de circulaires (`docs/sources-officielles/nuances/`) avec contrôle humain des extraits ; limite d'image à 2 576 px par côté sur les modèles Claude (changelog 1.3.2) |
| Recherche web ancrée | Probablement bon (outil `read_url` limité à nos domaines) ; vérifier chaque URL/licence citée | Le brainstorm exige de rouvrir les pages avant toute conclusion de licence |
| Traduction/reformulation, gros volumes répétitifs | Flash suffit, économique | Contrôle des espaces insécables (U+202F) et du vocabulaire éditorial |
| Génération de tests | Utile en brouillon ; exécution et lecture par le directeur | |
| Relecture de gros fichiers / de diffs | **Médiocre sans vérification** : première mission = 1 constat juste sur 3 (`docs/lessons-learned.md`) ; commentaire tiers : Gemini propose plus volontiers un correctif plausible pour du code non lu, Claude dit plus souvent « je dois voir ce fichier » (anecdotique) | Utiliser comme second avis, pas comme vérificateur |
| Décisions de fond, classements politiques, ADR | Non, quel que soit le modèle | Règle du projet |

### Économie de jetons Claude : estimation prudente
- Coût fixe par appel `agy` : ≈ 12,5 k jetons Gemini (mesuré aujourd'hui : 12 770 jetons pour une question triviale) ; ne coûte rien à Claude.
- Coût Claude d'une délégation : rédaction de la mission (500 à 2 000 jetons) + lecture du JSON (1 000 à 4 000) + vérification (très variable). Une tâche faite directement par un sous-agent Claude (recherche de code, rédaction de doc) consomme typiquement 20 à 80 k jetons dans le sous-agent, hors de la fenêtre du directeur mais dans le quota hebdomadaire.
- Hypothèse (à mesurer sur 3 à 5 missions) : recherche/lecture lourde 40 à 60 % d'économie ; documentation et traduction 30 à 50 % avant vérification, 15 à 30 % après ; relecture et code : proche de zéro ou négatif. Au total, **15 à 30 % du quota sur les familles éligibles**, soit une fraction modeste du quota global.
- Fort levier concurrent, sans risque : retirer les 88 commandes et agents orphelins de claude-flow (coût fixe par session), `rtk`, ponytail/caveman déjà actifs.

## 6. Quotas et conditions

- **Connaître son offre** : `agy -p "/usage"` (JSON : groupes, `remaining_fraction`, `reset_time`). Constat du jour : Gemini (Flash et Pro partagent une limite) **24 % restant, reset 2026-10-11 21:17 UTC** ; Claude/GPT-OSS : 99,8 % restant, reset 2026-10-11 17:36 UTC. Le palier lui-même (gratuit/Pro/Ultra) n'est pas affiché ; il se lit dans `/config` ou sur la page de compte Google AI de Mathias (question 4).
- Règle officielle visible dans le JSON : limite hebdomadaire par groupe, consommation proportionnelle au coût des jetons, liée au palier individuel. Informations de tiers (non officielles) : Pro ≈ 20 $/mois, Ultra 100 $ ou 200 $/mois selon la source ; plafonds hebdomadaires depuis mars 2026 ; de nombreux utilisateurs rapportent des blocages de plusieurs jours sur Gemini 3.1 Pro. Prudence : planifier les missions lourdes juste après un reset, préférer Flash.
- Puisque Claude/GPT via `agy` est à 100 %, un repli est possible : `--model claude-sonnet-4-6` (quota séparé de celui de Claude Code). Attention : ce serait toujours des sorties d'un modèle non supervisé par le directeur, vérification identique.
- **Conditions d'utilisation** : les « Interactions » (données d'usage, métadonnées, retours) sont enregistrées et servent à améliorer les produits et les modèles de Google ; suppression sur demande à antigravity-support@google.com ; le réglage « Enable telemetry » est le contrôle disponible, mais des utilisateurs doutent de son effet sur l'entraînement (fils Google, non tranché officiellement). Données concernées chez nous : code MIT et base ODbL publique ; ne jamais envoyer `.env`, sauvegardes, `~/`. Sorties : Google ne revendique pas la propriété du contenu généré (Conditions API Gemini) ; responsabilité de l'utilisateur ; autres conditions à lire sur antigravity.google/terms.

## 7. Recommandation et plan d'installation (NON EXÉCUTÉ)

**Recommandation** : ne pas installer Ruflo. Mettre en place la délégation « légère » (option A) + les compétences partagées minimales, mesurer sur 3 missions témoins, puis décider d'un éventuel MCP maison (D). Prérequis de sécurité déjà satisfaits : settings `agy` à liste blanche.

Étapes (chacune en branche dédiée, sauvegarde préalable de `~/.claude/settings.json` ; aucune n'est exécutée) :

1. **Correctif de la règle d'`agy`** (dépôt) : ajouter en tête de `.agents/rules/projet.md` :
   ```
   ---
   trigger: model_decision
   description: Règles du projet ministere-de-l-info (lecture seule, pas de classement politique, conventions)
   ---
   ```
   et créer un `AGENTS.md` de 10 lignes à la racine renvoyant vers `CLAUDE.md` et `.claude/skills/`. Test : `agy -p "Quelles règles vois-tu ?" --model gemini-3.8-flash-low --mode plan`.
2. **Skills partagés** (dépôt) :
   ```bash
   cd "/Volumes/le gros stockage/ministere-de-l-info"
   mkdir -p .agents/skills
   for s in projet-conventions data-viz-politique economie-tokens insee-duckdb-loader streamlit-duckdb-patterns; do
     ln -s "../../.claude/skills/$s" ".agents/skills/$s"; done
   agy -p "Liste tes skills (noms seulement), sans appeler d'outil" --mode plan --model gemini-3.8-flash-low
   ```
   Si les liens ne sont pas suivis, remplacer par `rsync -a --delete` dans un script `scripts/sync-skills-agy.sh` appelé par un hook de pré-commit.
3. **Script de délégation** `~/.claude/bin/agy-delegate` (ou `scripts/agy_delegate.sh`) :
   ```bash
   #!/usr/bin/env bash
   # usage: agy-delegate <modele> <fichier-mission.md>
   set -euo pipefail
   m="${1:?modele}"; f="${2:?mission}"
   out=$(mktemp -t agy-XXXX.json)
   timeout 900 agy -p "$(cat "$f")" --model "$m" --mode plan --sandbox \
     --output-format json --print-timeout 600s > "$out"
   jq -r '"status=\(.status) tokens=\(.usage.total_tokens) conv=\(.conversation_id)\n\(.response)"' "$out" | head -c 20000
   ```
   plus un skill `.claude/skills/deleguer-agy/SKILL.md` (≈ 40 lignes) : quand déléguer (matrice du brainstorm), gabarit de mission, règle « toute affirmation vérifiée au `file:line` par le directeur », journalisation `date;mission;modèle;tokens`. Écriture seulement en worktree avec settings de mission.
4. **Test d'import** (jetable, seulement si Mathias le souhaite) : copie de `~/.gemini/antigravity-cli` dans un dossier temporaire n'est pas supportée proprement ; à la place, lancer `agy plugin import claude` après avoir sauvegardé `~/.gemini/antigravity-cli/` (`cp -R`), puis `agy plugin list` et `agy plugin uninstall` si le résultat est bruyant. Attendu : risque d'importer ECC/claude-flow entiers (coût de contexte côté Gemini).
5. **Nettoyage des restes claude-flow** (décision Mathias) : sauvegarder puis retirer `~/.claude/commands/{analysis,automation,github,hooks,monitoring,optimization,sparc,claude-flow-*}`, les agents orphelins de `~/.claude/agents/`, les variables `CLAUDE_FLOW_*`, les permissions `mcp__claude-flow__*` / `npx claude-flow*` de `~/.claude/settings.json`, et le paragraphe « Ruflo Integration » de `~/.claude/CLAUDE.md`. Mesurer avant/après avec `/context`.
6. **Mesure** : 3 missions témoins (recherche de code, rédaction de doc, lecture d'un PDF) ; comparer jetons Claude (mission + lecture + vérification) à l'exécution directe ; décider.
7. (Facultatif) si Mathias veut un outil MCP : écrire le MCP maison (SDK `mcp` Python, un outil `delegate(model, prompt, mode)` lançant le script de l'étape 3, ≈ 100 lignes) ; ne prendre agy-bridge que paramétré `AGY_SKIP_PERMISSIONS=false`, `AGY_SANDBOX=true`, version épinglée, après lecture du code.

## 8. Risques

- Confidentialité : tout ce que lit `agy` part chez Google et peut servir à entraîner (réglage de télémétrie ambigu). Exposition faible (dépôt MIT, base ODbL) à condition de ne rien envoyer d'autre.
- Fiabilité : sorties de Flash/Pro non vérifiées ; 1 constat sur 3 juste lors de la première mission ; risque de « validé » sans exécution.
- Quotas : 24 % restant sur Gemini ; blocages de plusieurs jours possibles ; le prompt système coûte ≈ 12,5 k jetons par appel.
- Sécurité : `--dangerously-skip-permissions` (défaut d'agy-bridge) ; plugins/MCP tiers = exécution de code sous le compte de Mathias ; Ruflo = CVE 10.0 corrigée mais passif de confiance.
- Dérive des deux jeux de règles/skills (liens symboliques à tester, script de sync sinon).
- Images : propriété et conditions floues, neutralité, risque de trompe-l'œil.
- Outil jeune et fermé (`agy` 1.3.x), changelog dense ; épingler la version.

## 9. Questions fermées pour Mathias

1. Renonce-t-on à Ruflo (recommandé) et retient-on l'option A (skill + script `agy -p`) ? (oui/non)
2. Autorises-tu le nettoyage des restes claude-flow dans `~/.claude/` (88 commandes, agents orphelins, variables, paragraphe de CLAUDE.md), après sauvegarde ? (oui/non)
3. Autorises-tu la correction de `.agents/rules/projet.md` (frontmatter) et l'ajout d'un `AGENTS.md` court ainsi que des liens symboliques de skills vers `.claude/skills` ? (oui/non)
4. Quel est ton palier Google (gratuit, AI Pro, Ultra) et la télémétrie d'Antigravity est-elle désactivée dans `/config` ? (à renseigner)
5. Veux-tu que je teste `agy plugin import claude` (avec sauvegarde de `~/.gemini/antigravity-cli/`) ? (oui/non)
6. Génération d'images : interdite dans l'application et les rapports tant que tu n'as pas validé un cas précis ? (oui/non)
7. Souhaites-tu un MCP maison (~100 lignes) plutôt que le script + skill ? (non recommandé pour l'instant)

## Sources

- Ruflo README : https://github.com/ruvnet/ruflo ; issue d'audit #1375 : https://github.com/ruvnet/ruflo/issues/1375
- CVE-2026-59726 (Ruflo MCP) : https://thehackernews.com/2026/07/ruflo-mcp-flaw-lets-unauthenticated.html ; https://hackread.com/rufroot-vulnerability-attackers-hijack-ruflo-login/
- Aperçu des versions : https://www.augmentcode.com/learn/ruflo-v3-32-22-meta-harness-claude-code ; https://security.snyk.io/package/npm/claude-flow
- agy-bridge : https://github.com/sshahzaiib/agy-bridge ; autres ponts : https://mcpservers.org/servers/sshahzaiib/agy-bridge, https://mcp.directory/servers/claude-to-agy, https://glama.ai/mcp/servers/leologoli/agymcp
- Antigravity : https://antigravity.google/docs/cli/headless ; https://antigravity.google/docs/skills ; https://antigravity.google/docs/rules ; https://antigravity.google/docs/plugins/ ; https://antigravity.google/docs/marketplace/ ; https://antigravity.google/terms ; https://antigravity.google/blog/nano-banana-pro ; `agy changelog` (local, 1.2.15 à 1.3.2)
- Gemini API Additional Terms : https://ai.google.dev/terms
- Quotas/forums (tiers) : https://www.cloudzero.com/blog/google-antigravity-pricing/ ; https://agentpedia.codes/blog/antigravity-weekly-quota-cooldown-explained ; https://discuss.ai.google.dev/t/antigravity-data-training-opt-out/125236
- Comparatifs de modèles (tiers) : https://www.morphllm.com/comparisons/opus-4-6-vs-gemini-3-1-pro ; https://www.vellum.ai/blog/claude-opus-4-6-benchmarks ; https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/
