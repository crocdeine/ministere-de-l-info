# Exploration — Alternatives à Docker Compose pour le déploiement

**Date** : 2026-08-19
**Type** : Rapport d'aide à la décision (pas de migration technique effectuée)
**Question posée par Mathias** : Docker Compose est-il le bon choix long terme pour déployer ministere-de-l-info, ou existe-t-il un procédé plus simple ou plus optimisé ? Kubernetes a été mentionné sans certitude que ce soit pertinent.

---

## 1. Rappel du contexte technique réel

Avant de comparer des solutions, il faut peser ce qui caractérise concrètement ce déploiement :

- **Un seul hôte** : Mac mini M4 sous OrbStack. Pas de cluster, pas de deuxième nœud prévu.
- **Un seul utilisateur / trafic quasi nul** : usage perso, pas de pic de charge, pas de besoin de scaling horizontal.
- **Un seul service applicatif** : un container Streamlit (`ministere-info`), pas de micro-services à orchestrer entre eux.
- **DuckDB en fichier local, mono-writer** : c'est le point technique le plus structurant. DuckDB (ADR-0001) est une base analytique *in-process*, pas un serveur réseau. Un seul processus peut l'ouvrir en écriture à la fois. Cela signifie qu'on ne peut **pas** faire tourner plusieurs réplicas du container en parallèle pour de la haute disponibilité (HA) — ils se disputeraient le même fichier `.duckdb`. Toute solution qui vend du "multi-réplicas / auto-scaling / rolling update sans downtime" apporte donc un bénéfice nul ici tant que la base reste DuckDB fichier : l'appli est structurellement mono-instance.
- **Pas de besoin de haute disponibilité** : un redémarrage de 30 secondes lors d'une mise à jour n'a aucun impact réel (usage perso, pas de SLA).
- **Deux comportements de déploiement déjà distincts et documentés** : dev (bind mount) vs prod (named volume) — cf. `docs/deployment.md` et gotchas #12-13 du CLAUDE.md.

Ce point (DuckDB mono-writer) est central pour juger Kubernetes et Swarm : leur valeur ajoutée principale (orchestration multi-nœuds, HA par réplication, service discovery) ne s'applique pas à une architecture mono-instance/mono-fichier. Ce n'est pas un obstacle bloquant technique (K8s peut très bien faire tourner un seul pod), mais cela élimine l'essentiel de la justification de complexité.

---

## 2. Comparatif des options

| Solution | Complexité (mise en place + maintenance continue) | Effort de migration depuis l'existant | Bénéfice réel pour CE cas d'usage |
|---|---|---|---|
| **Docker Compose (statu quo)** | Faible — déjà en place, déjà documenté, déjà testé | Nul | Déjà adapté : mono-hôte, mono-service, fichier DB local. Reste la référence pour ce contexte. |
| **k3s / k0s (Kubernetes single-node)** | Élevée — nouveau vocabulaire (pods, deployments, PVC, services, ingress), nouveaux outils (kubectl, manifests YAML), overhead RAM permanent | Fort — réécriture complète du déploiement en manifests K8s, migration du volume, apprentissage | Quasi nul. RAM idle ~400-500 Mo (jusqu'à 1 Go) rien que pour le control plane, sur une machine où le compose actuel ajoute ~50 Mo. Aucun bénéfice HA exploitable (mono-writer DuckDB). Complexité disproportionnée par rapport au problème. |
| **Docker Swarm mode** | Moyenne — plus léger que K8s, intégré nativement à Docker Engine, mais mode "cluster" reste pensé pour plusieurs nœuds | Modéré — réécriture en stack file (proche du compose actuel), mais overlay networks/secrets à apprendre | Faible. Le mode Swarm en cluster à un seul nœud n'apporte quasiment rien par rapport à Compose (pas de facilité de rolling update utile ici puisque mono-instance obligatoire). Écosystème stagnant (SwarmKit maintenu mais n'évolue plus significativement depuis des années) — pari d'avenir incertain. |
| **PaaS auto-hébergé (Coolify / Dokploy / CapRover) par-dessus Docker** | Faible à moyenne — s'installe sur la machine existante, ajoute une UI web par-dessus le moteur Docker déjà en place | Faible-modéré — le compose actuel est réutilisable presque tel quel (Coolify et Dokploy supportent nativement Docker Compose) | Réel mais limité : apporte une UI de gestion (logs, redéploiement en un clic, gestion de `.env` via interface web, webhooks Git pour déploiement auto au push). Utile si Mathias veut piloter le déploiement sans repasser par le terminal SSH à chaque fois. N'apporte rien pour la HA ou la scalabilité (non pertinentes ici). |
| **Sans conteneur — venv + launchd** | Faible techniquement, mais perte d'un isolement déjà acquis | Modéré — il faut réinstaller GDAL, Tectonic, l'extension spatial DuckDB nativement sur macOS (actuellement gérés par le Dockerfile), et écrire un plist launchd pour le service Streamlit | Négatif net. Le Dockerfile encapsule déjà des dépendances système non triviales (GDAL, Tectonic, extension spatial) et l'image est distribuée sur ghcr.io pour une réinstallation reproductible. Revenir à un venv nu casse la reproductibilité et le côté "portable" (install.sh) déjà validé. launchd est déjà utilisé pour les backups (tâche cron simple) — ce n'est pas la même chose que faire tourner un service web complexe en continu. |
| **Hébergement managé externe (Fly.io / Railway / Render / Hetzner+Coolify)** | Faible (managé) à moyenne (Hetzner+Coolify, auto-géré) | Fort — sort du Mac mini, nécessite d'exposer/héberger ailleurs la DB (~900 Mo), change le modèle de coûts et de contrôle | Change la nature du projet : ce n'est plus de l'auto-hébergement perso, ça devient un service payant récurrent (~5-30 $/mois selon l'option, cf. section 4) pour un gain qui n'a de sens que si Mathias veut rendre l'outil accessible publiquement en permanence (disponibilité indépendante du Mac mini, accès distant). Sans ce besoin, c'est une dépense sans contrepartie. |

---

## 3. Statu quo — améliorations mineures identifiées

Le setup actuel (`docker-compose.prod.yml`, `Dockerfile`) est déjà plus soigné que la moyenne d'un projet solo :

**Déjà en place** (vérifié dans le repo) :
- Healthcheck applicatif (`curl /_stcore/health`, `start_period: 30s`) ✅
- Limites de ressources (`deploy.resources.limits.memory: 2G`, `reservations: 512M`) ✅
- `restart: unless-stopped` ✅
- Séparation dev (bind mount) / prod (named volume) documentée et testée ✅
- Utilisateur non-root dans le container ✅
- Image publiée sur ghcr.io, DB distribuée via GitHub Release, `install.sh` validé ✅

**Manquant ou améliorable, à effort très faible** :
1. **Rotation des logs Docker** : aucune configuration `logging.driver`/`logging.options` dans `docker-compose.prod.yml`. Le driver par défaut `json-file` n'a pas de limite de taille par défaut — sur un service qui tourne en continu pendant des mois, les logs peuvent grossir indéfiniment sur le disque du Mac mini. Ajout recommandé : `max-size: "10m"`, `max-file: "3"`.
2. **Watchtower pour les mises à jour auto d'image** : à évaluer avec prudence. Watchtower est explicitement décrit par ses mainteneurs comme destiné aux *homelabs*, pas à un usage "production" — et le projet publie ses images manuellement après tests (CI, validation). Un auto-update non supervisé casserait le principe du CLAUDE.md ("Claude Code propose, attend, exécute" / pas de déploiement sans validation). Watchtower n'est donc **pas recommandé** ici tel quel ; à la rigueur en mode "notification seulement" (`WATCHTOWER_NO_RESTART` + notif), mais l'intérêt reste marginal pour un déploiement mono-utilisateur où Mathias contrôle déjà le rythme des mises à jour.
3. **CPU limits** : seules les limites mémoire sont définies (`deploy.resources.limits.memory`). Ajouter une limite CPU (`cpus: "2"`) éviterait qu'un bug (boucle infinie, requête DuckDB pathologique) ne sature le Mac mini au détriment d'autres usages de la machine.
4. **`docker system prune` périodique** : pas de mention d'un nettoyage régulier des images/couches obsolètes après rebuilds répétés. À ajouter en tâche launchd similaire au backup, ou en rappel manuel.

Ces quatre points sont des ajustements de configuration, pas des changements d'architecture — effort de quelques minutes chacun.

---

## 4. Coûts approximatifs si sortie du Mac mini (hébergement managé)

Pour référence si Mathias envisage un jour de sortir de l'auto-hébergement :

- **Fly.io** : pas de tier gratuit en 2026 (supprimé). Une petite instance (256 Mo) part à ~2 $/mois, mais un usage réaliste avec egress et volume tourne plutôt à 8-25 $/mois.
- **Railway** : abonnement Hobby à 5 $/mois + usage (vCPU/RAM/egress) ; total réaliste 10-15 $/mois pour une charge solo.
- **Render** : Starter à 7 $/mois ; avec une base de données gérée en plus, 21-28 $/mois (non pertinent ici puisque DuckDB est un fichier, pas un service à part).
- **Hetzner + Coolify auto-géré** : VPS CX22/CX23 à environ 7-10 €/mois, stack complète (avec sauvegardes, monitoring) plutôt 17-35 €/mois. Coolify lui-même est gratuit en self-hosted ; une offre cloud Coolify (gestion uniquement, pas le serveur) existe à partir de 5 $/mois si on veut déléguer l'admin de la plateforme.

Dans tous les cas, ces options impliquent : (a) un coût récurrent inexistant aujourd'hui, (b) le transfert d'une base de données personnelle (données électorales, mais aussi l'app en elle-même) chez un tiers, (c) une perte de contrôle physique total sur la machine. Cela ne correspond plus au modèle "auto-hébergé perso sur le Mac mini" décrit dans le CLAUDE.md — ce serait un changement de nature du projet, pas juste un changement d'infra, et donc une décision structurante à documenter en ADR si jamais envisagée.

---

## 5. VERDICT

**Recommandation : garder Docker Compose tel quel.** Aucune des alternatives évaluées n'apporte un bénéfice justifiant son coût de complexité dans ce contexte précis.

**Argumentation :**

1. **Kubernetes (k3s/k0s) est disproportionné pour ce cas** : sa proposition de valeur — orchestration multi-nœuds, haute disponibilité par réplication, scaling automatique — ne s'applique à aucun des paramètres du projet (un hôte, un service, un utilisateur, une base fichier mono-writer qui interdit de toute façon le multi-réplicas). L'overhead permanent (~500 Mo-1 Go de RAM rien que pour le control plane, sur une machine qui alloue déjà 2 Go au container applicatif) et la charge cognitive (nouveau vocabulaire, nouveaux outils, nouveaux modes de panne à apprendre en solo) ne sont pas compensés par un bénéfice mesurable. Ce serait de la complexité pour la complexité — exactement le type de dérive que le CLAUDE.md cherche à éviter ("proposer, attendre, exécuter", rigueur méthodologique).

2. **Docker Swarm** souffre du même problème à un degré moindre : moins lourd que K8s, mais sa raison d'être (cluster multi-nœuds) ne s'applique pas non plus à un mono-nœud, et son avenir à long terme est incertain (maintenu mais stagnant).

3. **launchd + venv sans conteneur** serait un retour en arrière : le Dockerfile actuel encapsule des dépendances système non triviales (GDAL, Tectonic, extension spatial DuckDB) dont la reproductibilité via image ghcr.io est un acquis récent et validé (v0.4.3, testé sur macOS 26.4.1). Défaire ça pour gagner quoi ? Rien d'identifiable — au contraire, ça réintroduirait le risque "ça marche sur ma machine".

4. **Un PaaS auto-hébergé (Coolify en tête, vu son avance en maturité et communauté face à Dokploy/CapRover)** est la seule option qui a un intérêt réel, mais seulement si le vrai problème de Mathias est **opérationnel** (par ex. : il en a assez de taper des commandes `docker compose` en SSH, veut un déploiement en un clic depuis un `git push`, veut une UI pour consulter logs/santé sans terminal). Ce n'est pas un problème mentionné dans la demande initiale, et le compose actuel reste réutilisable presque tel quel si ce besoin apparaît plus tard — ce n'est donc pas urgent, mais c'est l'option à garder sous le coude si la friction opérationnelle augmente.

5. **Sortir vers un hébergement managé externe** changerait la nature même du projet (perso auto-hébergé → service payant tiers) sans que rien dans le contexte actuel (trafic nul, un seul utilisateur) ne le justifie. À ne considérer que si l'objectif devient explicitement de rendre l'outil accessible publiquement en permanence — ce qui serait une décision structurante à part entière, indépendante de la question infra.

**Actions concrètes proposées (mineures, non structurantes)** : ajouter la rotation de logs (`max-size`/`max-file`) et une limite CPU dans `docker-compose.prod.yml`, et prévoir un nettoyage périodique des images Docker obsolètes. Watchtower n'est pas recommandé compte tenu du principe "pas de déploiement sans validation" du projet.

---

## Sources

- [Why Docker Swarm is still My Go-To in 2026 - Dayio.dev](https://dayio.dev/posts/why-docker-swarm-is-still-my-go-to-in-2026/)
- [Support Swarm mode / clarify its status · Issue #175 · docker/roadmap](https://github.com/docker/roadmap/issues/175)
- [Docker Swarm Still Works. But Does It Still Have a Future? — Portainer](https://www.portainer.io/blog/docker-swarm-still-works-but-does-it-still-have-a-future)
- [Deprecated Docker Engine features — Docker Docs](https://docs.docker.com/engine/deprecated/)
- [Swarm mode — Docker Docs](https://docs.docker.com/engine/swarm/)
- [Kubernetes at Home: k3s on a Single Linux Server (2026) — FOSS Linux](https://www.fosslinux.com/158174/kubernetes-at-home-k3s-on-a-single-linux-server.htm)
- [Docker Compose vs Kubernetes: Which in 2026? — DeployWise](https://deploywise.dev/blog/docker-compose-vs-kubernetes)
- [Container Orchestration Beyond Docker: When to Consider Kubernetes for Self-Hosting — CompactHost](https://compacthost.com/blog/container-orchestration-beyond-docker-when-to-consider-kuber/)
- [Why K3s is the Best Option for Smaller Projects — Work & Life Notes](https://worklifenotes.com/2023/05/23/why-k3s-is-the-best-option-for-smaller-projects/)
- [Dokploy vs Coolify vs CapRover in 2026 — MassiveGRID Blog](https://massivegrid.com/blog/dokploy-vs-coolify-vs-caprover/)
- [Best Self-Hosted PaaS (2026): Coolify, Dokploy, CapRover, ServerCompass — Deploy Handbook](https://deployhandbook.com/best/self-hosted-paas)
- [Self-Hosted PaaS Showdown 2026 — Deploynix Laravel Blog](https://deploynix.io/blog/self-hosted-paas-showdown-2026-coolify-vs-dokploy-vs-caprover-vs-deploynix)
- [GitHub - containrrr/watchtower](https://github.com/containrrr/watchtower)
- [Watchtower - containrrr.dev](https://containrrr.dev/watchtower/)
- [Render vs Railway vs Fly.io: 2026 Pricing Showdown — ExpressTech](https://expresstech.io/render-vs-railway-vs-fly-io-2026-pricing-showdown/)
- [Railway vs Fly.io (2026): Pricing & Platform Comparison — Render](https://render.com/articles/railway-vs-fly-io)
- [7 Fly.io Alternatives in 2026: Real Pricing After the Free Tier Died — ExpressTech](https://expresstech.io/7-fly-io-alternatives-in-2026-real-pricing-after-the-free-tier-died/)
- [Best VPS for Coolify 2026: 5 Tested Providers Ranked — NextGrowth](https://nextgrowth.ai/best-vps-for-coolify/)
- [I Self-Hosted 4 Projects on Hetzner + Coolify — Ceaksan](https://ceaksan.com/en/hetzner-coolify-self-hosting-reality)
- [Pricing — Coolify](https://coolify.io/pricing)
- [Self-hosted n8n with Hetzner and Coolify in 2026 — Gauthier Huguenin](https://hgnn.io/en/blog/self-hosted-stack-hetzner-coolify-n8n)

**Fichiers de référence internes consultés** : `CLAUDE.md`, `docs/deployment.md`, `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `docs/adr/0001-duckdb-vs-postgres.md` (référencé pour la contrainte mono-writer).
