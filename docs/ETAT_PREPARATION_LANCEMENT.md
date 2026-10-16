# ImmoRadar — lot autonome de préparation au lancement

État mis à jour le 16 octobre 2026. Aucun nouvel hébergement payant ni paiement réel n’est activé. Le propriétaire souhaite différer toute dépense jusqu’à la fin des préparatifs gratuits.

## Résultat concret

La branche de travail repose sur `audit-sync-origin-main-2026-09-22`, commit `fe261232f29d26bed8a2e6abc67a0e169328d6e7`, qui contient la version locale attestée du 22 septembre et les 27 commits suivants.

Le premier lot a ajouté la facturation Premium. Le second rend l’offre tangible : démonstration calculée sans compte, critères personnels sur les dossiers, simulation de prix selon ces critères, rapports exportables et parcours de récupération de compte. Le troisième corrige les parcours commerciaux et la conservation des scénarios.

## Fonctionnalités du second lot

| Parcours | Fonctionnement |
| --- | --- |
| Découverte | L’accueil met en avant le coût, le flux et les scénarios; la démonstration présente un exemple complet avant inscription. |
| Démonstration | Prix, loyers et taux modifiables; trois scénarios, PDF fictif et liens vers Analyse/Premium. Aucun fournisseur ni compte réel n’est consulté. |
| Critères Premium | Prix maximal, flux minimal, rendement sur capital, DSCR et flux prudent; sauvegarde par compte, données absentes signalées. |
| Tri des dossiers | Comparaison des critères sur le dernier instantané de chaque dossier, sans double comptage de ses versions. |
| Plafond de simulation | Prix calculé pour satisfaire les seuils sous hypothèses fixes; ce n’est pas une valeur marchande ni un montant de financement approuvé. |
| Rapport | Section des critères actuels et du plafond. Polices intégrées et vérification visuelle sur un exemple de cinq pages. |
| Compte | Récupération par lien de 30 minutes à usage unique; ancienne session invalidée après changement de mot de passe. |
| Connexion | Limitation des tentatives par identité hachée; données financières non finies refusées par le moteur. |
| Stockage | Migrations atomiques, sauvegarde SQLite cohérente, contrôle d’intégrité et diagnostic sans requête externe. |
| Exploitation | Worker optionnel de sauvegarde et de notifications aux seuls comptes ayant consenti. Rien n’est activé par défaut. |

## Vérifications réalisées

- 406 tests automatisés réussis le 16 octobre, dont tests de paiement simulé, isolement des comptes, reconnexion, critères, plafond, démonstration, PDF, récupération, migrations concurrentes, rollback, sauvegardes, hébergement et retour vers Premium après authentification.
- Compilation Python et cohérence des dépendances vérifiées. Les versions principales installées et testées sont fixées dans `requirements.txt`.
- Cinq pages du PDF d’exemple rendues et contrôlées visuellement; la police intégrée corrige la substitution observée avec la police standard.
- Le fichier Compose est analysable et garde les opérations périodiques dans un profil optionnel.
- Ces vérifications ne constituent pas un test de charge, un test d’intrusion ou une validation sur un vrai compte Stripe/Brevo.
- Docker est absent de l’environnement de travail local. La construction et le démarrage ont toutefois réussi dans GitHub Actions : [exécution 38963680907](https://github.com/loic5443/indice-immo-quebec/actions/runs/38963680907), avec vraie session Streamlit via WebSocket et conservation d’un compte fictif après recréation du conteneur sur le même volume. Ce contrôle ne remplace pas la validation sur Render ni un test de charge.

## Parcours Premium corrigé le 16 octobre

Un visiteur qui choisit Premium retrouve maintenant l’offre après connexion ou après le démarrage obligatoire de son nouveau compte. Une connexion refusée ou un démarrage incomplet conserve cette intention. Ce retour n’ouvre pas de paiement et n’accorde aucun droit Premium. Le dernier choix explicite entre conserver une analyse et choisir Premium détermine la destination.

Deux nouveaux essais d’interface couvrent une vraie connexion avec mot de passe incorrect puis correct, et la fin du démarrage avec reconnaissance des limites d’abord absente puis acceptée. Le parcours de création de compte depuis Premium et le retour vers une analyse sont également contrôlés. Le workflow `launch-journeys.yml` permet de répéter la suite sur GitHub avec les paiements réels et les courriels désactivés.

## Corrections du troisième lot

- Les alertes utilisent les droits commerciaux actuels : un abonnement actif ouvre l’accès même si le compte était gratuit; une résiliation ou une expiration le ferme.
- Le quota ImmoValue commercial ne peut plus être contourné par une session sans compte. Les comparables restent disponibles pour l’inscription.
- La déconnexion et l’invalidation d’une session effacent les données privées conservées dans cette session.
- Les scénarios et tests de résistance sont effectivement enregistrés avec le dossier. Modifier un scénario personnalisé crée un nouvel instantané; rouvrir le dossier restitue ses paramètres.
- « Nouveau dossier » abandonne le brouillon précédent du même compte, conserve les dossiers sauvegardés et laisse les autres comptes intacts.
- Les simulations dépassant les bornes du moteur affichent une indisponibilité explicite et conservent les résultats de base.
- Pour un logement sans revenu locatif, les tableaux et PDF présentent le coût mensuel et des ratios locatifs non applicables. Une valeur nulle reste nulle dans la comparaison.
- Deux rapports fictifs de quatre pages, avec et sans revenus locatifs, ont été rendus pour contrôle visuel.

## État des accès et de la publication

La version de lancement est sauvegardée sur GitHub dans `codex/launch-october-2026`, commit `0c16d53`. Les préparatifs d’hébergement persistant sont dans `codex/hosting-persistent-2026-10-16`, commit `d6612f1`. Les corrections de parcours du 16 octobre sont préparées à partir de ce dernier état, dans `codex/premium-journey-2026-10-16`. Aucune fusion dans `main` ni publication de cette version commerciale n’a été faite. Un ancien déploiement Streamlit a existé; sa présence ne valide pas cette version.

GitHub est accessible et le connecteur Render est connecté. Aucun espace de travail Render n’est sélectionné et aucune ressource payante n’a été créée. Pour la phase d’intégration réelle, il reste le choix et l’accord sur l’hébergement, puis la configuration Stripe et Brevo. Un domaine personnel n’est pas nécessaire aux premiers contrôles HTTPS si l’hébergeur fournit une adresse. Les procédures et scénarios de recette sont dans `LANCEMENT_PREMIUM.md` et `HEBERGEMENT_RENDER.md`.

La récupération est implémentée mais ne peut envoyer de lien tant que la configuration de courriel et l’URL HTTPS ne sont pas prêtes. Le suivi ne surveille pas automatiquement toutes les annonces; il compare les instantanés sauvegardés. Les sauvegardes périodiques du même volume doivent être copiées hors du serveur et surveillées.

Les attributions de données, coordonnées commerciales, conditions d’abonnement et procédure de support doivent être finalisées avant une ouverture payante. La cible du 22 octobre reste un objectif; aucune publication future n’est planifiée automatiquement.

## Principes d’inspiration

L’approche reprend des méthodes produit observables, pas du code, du texte publicitaire, des marques ou des bases de données tierces :

- Un exemple permet de comprendre les calculs avant de s’abonner.
- Les outils Premium aident à sélectionner, comparer et présenter un achat à partir de critères personnels.
- Les limites de disponibilité des données restent visibles; l’absence de comparables ne devient pas une fausse valeur marchande.

Références publiques consultées :

- https://help.dealcheck.io/en/articles/2259844-screening-properties-with-custom-investment-criteria
- https://help.dealcheck.io/en/articles/2490178-comparing-properties-side-by-side
- https://help.dealcheck.io/en/articles/5017895-how-can-i-print-property-information-analysis-and-reports
- https://www.biggerpockets.com/investment-calculators
- https://www.zillow.com/zestimate/
