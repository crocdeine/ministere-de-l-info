# Brainstorming : déléguer à Google Antigravity (`agy`) pour économiser les jetons Claude

Date : 2026-10-07 · Instruction en lecture seule (rien installé, aucune config modifiée). Seule action : 2 appels `agy -p` triviaux (`/usage` et « OK », Flash low, mode plan) pour valider le mode headless.

## Résumé

1. `agy` 1.3.1 fonctionne en headless, y compris en pipe (le bug « sortie vide hors TTY », issue GitHub #76 de mai, ne se reproduit pas ici). Sortie JSON : `status`, `response`, `duration_seconds`, `usage.{input,output,thinking,total}_tokens`.
2. Le settings.json est `~/.gemini/antigravity-cli/settings.json` ; syntaxe `permissions.{allow,ask,deny}` avec `command(préfixe)`, `command(regex:...)`, `read_file()`, `write_file()`, `read_url()`, `mcp(serveur/outil)`. Précédence deny > ask > allow. En `-p`, tout ce qui n'est pas autorisé est refusé.
3. Le settings actuel est trop permissif et pollué (82 règles dont `command(uv)`, `curl`, `pip install`, `allowNonWorkspaceAccess: true`) : à assainir avant tout usage automatisé.
4. Modèles : Gemini 3.8/3.7/3.6 Flash, 3.1 Pro, Claude Sonnet 4.6 / Opus 4.6, GPT-OSS 120B. Quotas hebdomadaires séparés (constat du jour : Gemini 61 % restant, Claude+GPT 100 %).
5. Plugins tiers : rien d'indispensable. Recommandation : zéro plugin au départ ; un `.agents/` maison minimal.
6. Garde-fou : toute sortie Antigravity est une hypothèse (leçon du relais Gemini « validé » sans test).

## 1. Capacités constatées du CLI

- Modes : `--mode plan|accept-edits` ; `--sandbox` (restrictions du terminal, propagé en `-p` depuis 1.0.6) ; `--effort low|medium|high|xhigh|max` ; `--model <id>` ; `--add-dir` ; `--agent` ; `--project`.
- Print : `-p`, `--output-format text|json|stream-json`, `--json-schema <chaîne|fichier>`, `--print-timeout <durée>` (0 = illimité), `--continue`, `--conversation <id>`, `--input-format stream-json`.
- `--dangerously-skip-permissions` : à ne jamais utiliser ici.
- Sous-commandes : `models`, `agents`, `mcp add|remove|list|enable|disable`, `plugin list|import [gemini|claude]|install <plugin@marketplace|dossier>|uninstall|enable|disable|validate`, `update`, `remote-control`. `-p "/usage"` donne les quotas restants.
- Personnalisation : `.agents/` du projet (`rules/`, `workflows/`, `skills/<n>/SKILL.md`, `agents/*.md`, `plugins/`) et manifests `skills.json`, `rules.json`, `plugins.json`, `agents.json` ; `agy plugin import claude` peut reprendre des plugins Claude. Plugins installés dans `~/.gemini/antigravity-cli/plugins/`.
- Surcoût fixe mesuré : ≈ 12,5 k jetons d'entrée pour un « OK » (prompt système). Négligeable pour une mission, à ne pas multiplier en petites requêtes.
- Fermé (non open source), plus d'ACP.

Sources : [permissions](https://antigravity.google/docs/permissions?tab=cli), [headless](https://antigravity.google/docs/cli/headless), [marketplace](https://antigravity.google/docs/marketplace/), [using](https://www.antigravity.google/docs/cli/using), [guide ECC local](~/.claude/plugins/cache/ecc/ecc/2.2.3/docs/ANTIGRAVITY-GUIDE.md).

## 2. Matrice de délégation

Légende vérification : V0 = lecture seule, le directeur contrôle les affirmations clés ; V1 = le directeur relance lui-même tests/lint ; V2 = relecture complète du diff.

| Tâche | Déléguer ? | Modèle conseillé | Mode / permissions | Vérification par le directeur |
|---|---|---|---|---|
| Relecture de diff / branche (lecture seule) | Oui, en 2e avis | Gemini 3.1 Pro (High) | `--mode plan`, allow git diff/log/show | V0 : chaque constat est vérifié au `file:line` cité avant d'être retenu ; l'absence de constat ne vaut pas validation |
| Recherche de code (« où est X ») | Oui | 3.8 Flash low | `plan`, allow grep/find/cat | V0 : lecture ciblée du `source_location`. Alternative gratuite : graphify, cavecrew-investigator |
| Analyse de sources de données (data.gouv, INSEE, Eurostat : schéma, licences, formats) | Oui, sous conditions | 3.1 Pro ou 3.8 Flash high | `plan`, `read_url` limité aux domaines de CLAUDE.md | V1 : URL, licence et colonnes cités rouverts par le directeur ; aucune conclusion de licence reprise sans lecture de la page |
| Rédaction de documentation (docs/, guide utilisateur, brouillons de rapports) | Oui, sous conditions | 3.8 Flash high | `accept-edits` en worktree, `write_file(docs/)` | V2 : chiffres, noms de tables et chemins recoupés avec le code ; relecture ADR/CLAUDE.md par le directeur |
| Génération de tests pytest | Oui, sous conditions | 3.1 Pro | `accept-edits` en worktree, `write_file(tests/)`, allow `uv run pytest`, `uv run ruff` | V1 obligatoire : le directeur exécute `uv run pytest` et `ruff` lui-même ; tests relus (assertions non triviales, pas de mock qui masque) |
| Maquette web TypeScript (hors Streamlit, hors stack) | Oui, en prototype jetable | 3.1 Pro | worktree dans un dossier dédié (`web/` non suivi), pas d'accès à `data/` | V2 ; reste hors périmètre produit tant que Mathias n'a pas tranché (stack non négociable) |
| Traductions / reformulations (UI, docs) | Oui | 3.8 Flash medium | `accept-edits` en worktree | V2 sur diff ; vocabulaire éditorial et espaces insécables (leçon U+202F) vérifiés |
| Correctifs de code (Python, SQL, ETL) | Non par défaut ; sous conditions pour correctif borné | 3.1 Pro | worktree, fiche de mission obligatoire | V2 + tests exécutés par le directeur ; jamais de merge sans relecture |
| Classements politiques (nuance → bloc, blocs de législature, `leg_blocs_override`) | **Non** | — | — | Décision de Mathias (CLAUDE.md) ; au plus une instruction documentaire de sources par `chercheur-donnees` |
| Écriture dans la base DuckDB, chargement ETL réel, `data/` | **Non** | — | `deny write_file(data/)`, `deny command(duckdb)` | — |
| Git : commit, push, release, tags, CI | **Non** | — | `deny command(git push)`, `command(git commit)`, `command(gh)` | Le directeur seul (règle CI post-push) |
| Décisions d'architecture, ADR, CLAUDE.md | **Non** (brouillon seulement) | — | — | Mathias tranche |
| Secrets, `.env`, accès hors dépôt | **Non** | — | `deny read_file(.env)`, `allowNonWorkspaceAccess: false` | — |

Règle générale : Antigravity produit des brouillons et des constats, jamais un verdict. Une « validation » n'est recevable qu'avec les commandes exécutées et leur résultat (lessons-learned, relais 2026-10-04).

## 3. Configuration recommandée

### Constats sur l'existant (non modifié)
`~/.gemini/antigravity-cli/settings.json` contient : modèle `Gemini 3.1 Pro (High)`, `allowNonWorkspaceAccess: true`, deux `trustedWorkspaces` (dont l'ancien chemin `/Users/crocdeine/Documents/Docker/...`), et 82 règles `allow` héritées de sessions passées : `command(uv)` (équivaut à exécuter n'importe quel code Python), `command(find)`, `command(cat)`, `command(python3 ...)`, `command(pip install ...)`, nombreux `curl`. Contradiction avec la règle « pas de pip » et trop large pour un usage automatisé.

### Règles minimales proposées (à appliquer par Mathias ou le directeur après validation)
Remplacer `permissions` par :

```json
{
  "allowNonWorkspaceAccess": false,
  "model": "Gemini 3.8 Flash (High)",
  "permissions": {
    "allow": [
      "command(git status)", "command(git diff)", "command(git log)", "command(git show)",
      "command(git branch --show-current)", "command(git rev-parse)",
      "command(grep)", "command(rg)", "command(ls)", "command(head)", "command(tail)",
      "command(wc)", "command(sed -n)",
      "command(uv run ruff check)", "command(uv run ruff format --check)",
      "command(uv run pytest)",
      "read_file(/Volumes/le gros stockage/ministere-de-l-info)",
      "read_url(data.gouv.fr)", "read_url(tabular-api.data.gouv.fr)",
      "read_url(insee.fr)", "read_url(ec.europa.eu)", "read_url(data.senat.fr)",
      "read_url(data.assemblee-nationale.fr)"
    ],
    "ask": [
      "command(*)"
    ],
    "deny": [
      "command(git push)", "command(git commit)", "command(git reset)", "command(git checkout)",
      "command(git clean)", "command(rm)", "command(gh)", "command(sudo)",
      "command(pip)", "command(uv add)", "command(uv sync)", "command(uv pip)",
      "command(curl)", "command(wget)", "command(duckdb)",
      "write_file(.git/)", "write_file(data/)", "write_file(.env)", "read_file(.env)",
      "write_file(CLAUDE.md)", "write_file(docs/adr/)"
    ]
  }
}
```

Réserves :
- `uv run pytest` exécute le code du dépôt (conftest, imports) : acceptable en worktree isolé, pas sur le dépôt principal pour un prompt non fiable. Pas de `cat` ni de `find` (le premier lit tout, le second a `-exec`) : utiliser `head`, `sed -n`, `rg`.
- Les redirections, substitutions (`$(...)`) et pipes déclenchent une correspondance exacte, donc un refus en `-p` : voulu.
- Pour les missions en écriture, ajouter `write_file(<dossier cible>)` uniquement dans un settings de mission, pas globalement. Je n'ai pas trouvé de settings par projet documenté : à vérifier (`/permissions` en session) ; à défaut, deux fichiers swappés par un script du directeur (non testé).
- Syntaxe `command()` : préfixe mot par mot (`command(git diff)` couvre `git diff --stat`) ; `regex:` disponible. Vérifier par un test en `-p` après modification.
- Ne pas passer `--dangerously-skip-permissions`.

### Autres réglages
- Modèle par défaut : Flash (High) pour recherche/doc/traduction ; Pro (High) pour relecture et tests. Claude Sonnet/Opus via `agy` : quota « Claude and GPT » distinct du quota Claude Code (100 % restant) ; utilisable en appoint quand le quota Gemini est bas, à tester.
- Sandbox : `--sandbox` systématique en `-p` ; worktree git dédié pour toute mission qui écrit.
- Télémétrie : vérifier dans `/config` que « Enable telemetry » est désactivé (réglage non visible dans les fichiers lus ; des fils de discussion Google signalent des doutes sur l'opt-out réel).
- `trustedWorkspaces` : retirer l'ancien chemin Docker.

## 4. Plugins, MCP, agents tiers

Aucun plugin n'est nécessaire : le catalogue officiel (Firebase, Android, Flutter, Chrome DevTools, BigQuery) ne couvre pas Python/DuckDB/Streamlit. Les commandes ci-dessous n'ont pas été exécutées.

| Élément | Classement | Source / maintenance / licence | Apport | Risque | Commande |
|---|---|---|---|---|---|
| `.agents/` maison (AGENTS.md pointant vers CLAUDE.md, skills `projet-conventions`, `economie-tokens`, `data-viz-politique` réutilisés) | **Recommandé** | Interne | Mêmes conventions que Claude sans les recopier dans chaque prompt | Dérive entre les deux copies : préférer des liens symboliques vers `.claude/skills/` (à tester) | `mkdir .agents` puis liens ; ou `agy plugin import claude` (à essayer d'abord, lecture des plugins Claude, vérifier ce qui est importé) |
| ECC cible antigravity (`ecc-universal`) | Optionnel | npm `ecc-universal`, guide ECC 2.2.x (déjà installé côté Claude, version cache 2.2.3) ; licence à vérifier dans le paquet | Règles, workflows, agents reviewers adaptés Flash/Pro | Copie des dizaines de fichiers dans le dépôt, bruit de contexte (surcoût jetons, l'inverse du but) ; réviseurs génériques non adaptés à Python/DuckDB | `npx ecc-universal@2.2.0 install --profile minimal --target antigravity` (depuis le dépôt, en branche dédiée ; revoir le diff) |
| MCP Context7 (docs de bibliothèques à jour) | Optionnel | `@upstash/context7-mcp`, Upstash, MIT (de mémoire, non revérifié) | Docs Streamlit/DuckDB/Polars à jour sans WebFetch | Requêtes de libellés de bibliothèques envoyées à un tiers (pas de données du projet) ; paquet npx exécuté à chaque lancement | `agy mcp add context7 -- npx -y @upstash/context7-mcp` |
| MCP DuckDB lecture seule | À éviter pour l'instant | (non vérifié) | Requêter la base sans écrire | Risque d'accès à la base ; la base est publique mais `deny duckdb` est plus simple | — |
| Plugin Chrome DevTools officiel | Optionnel (plus tard) | Google | Tests visuels d'une maquette web | Pilote un navigateur ; inutile tant qu'il n'y a pas de maquette | `agy plugin install chrome-devtools@<marketplace>` (nom exact de la marketplace à lire via `/plugin`, onglet Discover) |
| Plugins Firebase/Android/Flutter/BigQuery | Hors sujet | Google | — | — | — |
| `agentic-awesome-skills` (sickn33, 47 k étoiles, MIT, 2 658 skills) | À éviter | GitHub | Catalogue immense | Surcharge de contexte, chaîne d'approvisionnement non auditée, l'auteur lui-même demande d'examiner chaque skill | — (si un jour : `npx agentic-awesome-skills --antigravity --skills <ids> --dry-run`, une skill à la fois) |
| Registres tiers (hol.org, etc.) | À éviter | Agrégateurs sans audit | — | Scores de confiance non vérifiables | — |

Règle d'installation : un plugin = revue de son manifeste (`agy plugin validate <dossier>`), hooks et MCP inclus, avant `install`, car un plugin peut embarquer des hooks et des serveurs MCP exécutables.

## 5. Intégration au pipeline

### Gabarit de lancement (lecture seule)
```bash
cd "<worktree ou dépôt>"
agy -p "$(cat .claude/plans/AAAA-MM-JJ-nom.plan.md)

Consignes : lecture seule. Cite file:line pour chaque constat. Liste les commandes
exécutées et leur résultat ; n'écris jamais « validé » sans exécution." \
  --model gemini-3.1-pro-high --mode plan --sandbox \
  --output-format json --print-timeout 600s \
  > /tmp/agy-<mission>.json 2> /tmp/agy-<mission>.err
```
- Mission avec écriture : même gabarit avec `--mode accept-edits`, lancé depuis un worktree isolé (`git worktree add`), settings avec `write_file(<dossier>)` ciblé.
- Sortie structurée : `--json-schema` avec `{statut, constats:[{fichier, ligne, gravité, texte}], commandes:[{cmd, résultat}], questions_fermées:[]}` pour parser sans relire.
- Durée max : `--print-timeout 600s` (la valeur 0 attend indéfiniment) plus `timeout 900` côté shell. Un timeout rend un code non nul.
- Reprise après coupure : `--conversation <id>` (le `conversation_id` est dans le JSON) ; la fiche de mission reste la référence.
- Lancement en arrière-plan par le directeur ; il lit seulement `.response`, `.status` et `.usage` : `jq '{status, response, usage}'`.

### Vérification par le directeur
1. `status == SUCCESS` et code retour 0 ; sinon, relancer ou abandonner.
2. Chaque constat est recoupé à la source (`git show`, lecture ciblée) ; tous les constats bloquants sont recoupés, un échantillon pour les autres.
3. Pour tout code : `uv run ruff check` + `uv run pytest -q` exécutés par le directeur, résultats cités dans le rapport.
4. Aucune affirmation de test passé n'est reprise sans la sortie de la commande dans le JSON.
5. Aucun agent Antigravity ne commit ni ne pousse ; le directeur commit depuis le worktree après relecture.
6. Décisions structurantes et classements : remontés à Mathias, pas tranchés.

### Mesure de l'économie de jetons
- Côté Antigravity : `usage.total_tokens` de chaque JSON ; journaliser (une ligne CSV `date;mission;modèle;tokens;durée`) dans `reports/` ou `docs/journal.md`. Quotas : `agy -p "/usage"` avant/après une vague (champs « Weekly Limit Remaining »).
- Côté Claude : `/ecc:cost-report`, `/context`, ou `rtk gain` ; comparer le coût du directeur (prompt de mission + lecture du résumé + vérification) à celui d'un sous-agent Claude équivalent sur 3 à 5 missions témoins.
- Seuil de rentabilité : la vérification coûte des jetons Claude ; si elle dépasse ≈ 50 % du coût d'une exécution directe, ne pas déléguer ce type de tâche. Mesurer avant de généraliser.

## 6. Risques

- **Confidentialité** : tout le code lu et les extraits de données partent chez Google ; le dépôt est MIT et la base ODbL (publique), donc l'exposition est faible, mais rien de privé : pas de `.env`, pas de `~/`, pas de sauvegardes (`../ministere-de-l-info-backups/`). Télémétrie à vérifier/désactiver dans `/config` ; le fil Google sur l'opt-out ignoré incite à la prudence.
- **Fiabilité** : relais déjà pris en défaut (« validé » sans exécution) ; modèles Flash enclins aux affirmations non vérifiées ; cela justifie les contrôles V0 à V2 et l'interdiction des classements.
- **Quotas** : Gemini 61 % du plafond hebdomadaire restant au 2026-10-07 (reset 2026-10-11) ; le prompt système coûte ≈ 12,5 k jetons par appel ; les sous-agents parallèles (3 à 5) épuisent vite le quota. Une erreur de quota apparaît comme un échec, pas comme un blocage silencieux (changelog 1.3.1) : surveiller `status`.
- **Sécurité des permissions** : l'allow-list héritée (`uv`, `python3`, `curl`, `pip`) permet l'exécution arbitraire ; à nettoyer avant toute mission automatisée. `allowNonWorkspaceAccess: true` autorise des lectures hors dépôt.
- **Plugins/MCP tiers** : exécution de code arbitraire sous le compte de Mathias ; zéro plugin par défaut.
- **Outil jeune et fermé** : 1.3.x, changelog dense, bugs récents en headless (#76 non résolu en amont mais non reproduit ici) ; épingler la version, relire `agy changelog` avant mise à jour.

## Décisions à soumettre à Mathias (questions fermées)
1. Autorise-t-on le remplacement de la section `permissions` de `~/.gemini/antigravity-cli/settings.json` par la liste du §3 ? (oui/non)
2. Périmètre initial de délégation : relectures et recherches en lecture seule uniquement, puis tests/doc en worktree après trois missions témoins concluantes ? (oui/non)
3. Télémétrie Antigravity : désactivée avant toute mission ? (oui/non)
4. Installer ECC cible antigravity (optionnel) ou rester sur un `.agents/` maison ? (maison recommandé)
