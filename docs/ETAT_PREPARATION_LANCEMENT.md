# ImmoRadar — lot autonome de préparation au lancement

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

- 392 tests automatisés réussis, dont tests de paiement simulé, isolement des comptes, reconnexion, critères, plafond, démonstration, PDF, récupération, migrations concurrentes, rollback et sauvegardes.
- Compilation Python et cohérence des dépendances vérifiées. Les versions principales installées et testées sont fixées dans `requirements.txt`.
- Cinq pages du PDF d’exemple rendues et contrôlées visuellement; la police intégrée corrige la substitution observée avec la police standard.
- Le fichier Compose est analysable et garde les opérations périodiques dans un profil optionnel.
- Ces vérifications ne constituent pas un test de charge, un test d’intrusion ou une validation sur un vrai compte Stripe/Brevo.
- Docker n’est pas disponible dans l’environnement de travail : la construction et le démarrage des conteneurs restent à vérifier sur l’hébergement.

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

L’écriture GitHub a retourné une erreur 403 et l’envoi Git n’avait pas d’authentification utilisable. Aucun changement n’a donc été poussé, fusionné sur `main` ou publié sur un site. Les commits et le fichier de modifications constituent le point de reprise.

Pour la phase d’intégration réelle, il reste les accès GitHub, hébergement/domaine, Stripe et Brevo. Les procédures, configurations et scénarios de recette sont dans `LANCEMENT_PREMIUM.md`.

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
