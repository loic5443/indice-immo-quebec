# ImmoRadar — hébergement persistant sans domaine personnalisé

## Proposition préparée le 16 octobre 2026

La branche part de `codex/launch-october-2026`, commit `0c16d53`. Aucun compte Render, abonnement payant, paiement Stripe ou envoi réel de courriel n’est créé par les fichiers de configuration.

Streamlit Community Cloud est déjà lié au projet, mais ne garantit pas la conservation des fichiers locaux. La base SQLite des comptes, dossiers et abonnements exige un stockage persistant avant l’ouverture commerciale.

## Déploiement proposé

- Un seul service Docker Render, une seule instance, avec un disque de 1 Go monté sur `/app/var`.
- Plan proposé : `0.5c-512mb`, région `virginia` (États-Unis). La localisation des données devra être retenue explicitement pour l’ouverture du service.
- Tarif affiché le 16 octobre : serveur 7 USD/mois et disque 0,25 USD/Go/mois, soit 7,25 USD/mois de base. Taxes, conversion de devise, dépassements réseau et éventuels autres services sont en supplément. Revoir le montant affiché dans le compte avant toute création payante.
- L’espace de travail Hobby n’a pas de frais fixes; le calcul et le disque restent payants. Aucun espace Pro n’est requis par cette configuration.
- URL `https://…onrender.com` et certificat TLS fournis par Render; aucun domaine personnalisé n’est nécessaire.
- Caddy expose le port public `PORT`; Streamlit et FastAPI restent sur les ports internes de la même instance. Ils utilisent exactement le même fichier SQLite.
- Les migrations sont lancées au démarrage, après montage du disque, jamais à la construction de l’image ou dans un job séparé.
- Le lanceur prépare les permissions du répertoire puis abandonne les privilèges root avant les migrations et les serveurs.
- Une panne d’un processus essentiel arrête tous les autres et fait échouer l’instance. L’endpoint `/_deployment/ready` vérifie la base et la disponibilité de Streamlit.
- Le proxy ne consigne pas les URI ni les en-têtes dans ses erreurs, pour éviter de copier des liens de récupération ou des cookies dans les journaux.

## Procédure quand les accès et le coût seront approuvés

1. Lier le dépôt et la branche validée au compte Render, puis importer `render.yaml` comme Blueprint. Ne pas cliquer sur la création des ressources payantes avant revue du récapitulatif.
2. Vérifier le plan, la région, le disque et le Dockerfile `deployment/render.Dockerfile`. Le plan Free ne permet pas ce disque persistant.
3. Vérifier la réussite du workflow GitHub « Hébergement persistant ». Il construit l’image, valide Caddy, ouvre une vraie session Streamlit, crée un compte fictif puis recrée le conteneur sur le même volume pour vérifier la conservation du compte.
4. Créer le service après accord sur les frais. Les paiements, courriels et opérations périodiques restent désactivés.
5. Vérifier la santé, les journaux et la page d’accueil, puis lancer `python -m scripts.check_hosted_runtime --url https://<url-du-service>` depuis le conteneur ou un poste possédant les dépendances du projet.
6. Créer un compte de recette et un dossier fictif, redémarrer le service depuis Render et confirmer qu’ils sont encore disponibles. Contrôler les ressources mémoire et les temps de réponse avant d’ouvrir les inscriptions.
7. Préparer une sauvegarde SQLite cohérente et sa copie hors du serveur; tester une restauration avant d’accueillir des données réelles. Les sauvegardes sur le même disque ne remplacent pas cette copie externe.

Le lanceur reprend `RENDER_EXTERNAL_URL` pour `IMMORADAR_PUBLIC_URL` si aucune URL explicite n’a été configurée. Une URL fournie manuellement doit être une origine HTTPS sans identifiants, chemin ou paramètres.

## Limites de validation

- 404 tests Python réussis; configuration Caddy 2.10.2 validée avec son binaire réel.
- Trois services exécutés ensemble dans l’environnement de préparation : vérification HTTP, session Streamlit via WebSocket, sauvegarde d’un compte et d’un dossier fictifs, arrêt puis redémarrage avec données conservées.
- Docker n’est pas disponible dans cet environnement. La construction de l’image, les permissions réelles du volume Docker et le fonctionnement dans la limite de 512 Mo doivent passer dans le workflow GitHub et sur Render. Les tests de processus ne remplacent pas cette validation.
- Ce plan mémoire est une proposition de lancement limité, pas une capacité de trafic garantie. Aucune charge simultanée ni montée en charge n’a été validée.
- Une seule instance est compatible avec ce stockage. Les déploiements avec disque impliquent une interruption brève; plusieurs répliques nécessiteraient une base partagée adaptée.
- Le site Streamlit existant n’est ni supprimé ni modifié par cette configuration. Aucune base existante n’est importée automatiquement.
- La facturation réelle, les courriels, la politique de confidentialité et les conditions commerciales restent à valider avant l’ouverture payante.

## Sources officielles

- https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
- https://render.com/docs/disks
- https://render.com/docs/blueprint-spec
- https://render.com/docs/environment-variables
- https://render.com/docs/web-services
- https://render.com/pricing
