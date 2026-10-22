# Cenlio — lot autonome de préparation au lancement

État mis à jour le 20 octobre 2026. Aucun nouvel hébergement payant ni paiement réel n’est activé. Le propriétaire souhaite différer toute dépense jusqu’à la fin des préparatifs gratuits.

## Stripe — recette du 20 octobre 2026

Paiements Checkout fictifs acceptés et refusés, calcul TPS/TVQ de simulation, activation Premium, isolation des comptes, confirmation serveur, lecture du portail client français et résiliations vérifiés. Deux abonnements fictifs annulés en fin de recette. Formulaire et portail passent au français canadien; correction de l'adresse utilisée pour les taxes. 32 tests ciblés réussis. Voir [la recette et ses limites](STRIPE_RECETTE_2026-10-20.md).

Les changements récents ne sont pas encore publiés sur GitHub ou déployés. Le retour navigateur vers une application publiée avec facturation active, le webhook public, la configuration réelle et le stockage persistant restent à valider; l'aperçu public n'encaisse rien.

## Dernière recette — 18 et 19 octobre 2026

- 427 tests locaux réussis après les correctifs d’adresses et de reprise des appartements. La suite distante est également exécutée à chaque sauvegarde de la branche.
- Aperçu HTTPS gratuit : https://immoradar-apercu.onrender.com/ — paiements, courriels et opérations périodiques désactivés; base éphémère et données fictives uniquement.
- 28 requêtes d’adresses réelles et entrées limites vérifiées auprès du MRNF; deux rôles municipaux importés et leurs valeurs affichées dans le navigateur public. Les résultats absents restent explicitement absents.
- Mise en page Chromium vérifiée à 360 et 390 px; formulaire, suggestions, navigation Premium et démonstration contrôlés. Aucun vrai iPhone/Safari ni clavier tactile utilisé.
- Comptes, dossiers, brouillons, isolation entre utilisateurs, réouverture dans un autre processus et restauration d’une sauvegarde contrôlés. La conservation après redémarrage du véritable hébergement persistant reste à valider.
- L’espace Render My Workspace a été confirmé et contient le seul service gratuit d’aperçu. Le plan de production avec disque /app/var est préparé mais non créé, conformément au refus de frais avant la fin des préparatifs gratuits.

Voir [la recette détaillée](VERIFICATION_ADRESSES_MOBILE_COMPTES_2026-10-18.md). Les sections datées du 16 octobre ci-dessous décrivent les contrôles antérieurs; leurs blocages visuels locaux ont été dépassés par les essais HTTPS, sans valider pour autant tous les appareils ou une exploitation payante.

État mis à jour le 19 octobre 2026. Aucun nouvel hébergement payant ni paiement réel n’est activé. Le propriétaire souhaite différer toute dépense jusqu’à la fin des préparatifs gratuits.

## Dernière recette — 18 et 19 octobre 2026

- 427 tests locaux réussis après les correctifs d’adresses et de reprise des appartements. La suite distante est également exécutée à chaque sauvegarde de la branche.
- Aperçu HTTPS gratuit : https://immoradar-apercu.onrender.com/ — paiements, courriels et opérations périodiques désactivés; base éphémère et données fictives uniquement.
- 28 requêtes d’adresses réelles et entrées limites vérifiées auprès du MRNF; deux rôles municipaux importés et leurs valeurs affichées dans le navigateur public. Les résultats absents restent explicitement absents.
- Mise en page Chromium vérifiée à 360 et 390 px; formulaire, suggestions, navigation Premium et démonstration contrôlés. Aucun vrai iPhone/Safari ni clavier tactile utilisé.
- Comptes, dossiers, brouillons, isolation entre utilisateurs, réouverture dans un autre processus et restauration d’une sauvegarde contrôlés. La conservation après redémarrage du véritable hébergement persistant reste à valider.
- L’espace Render My Workspace a été confirmé et contient le seul service gratuit d’aperçu. Le plan de production avec disque /app/var est préparé mais non créé, conformément au refus de frais avant la fin des préparatifs gratuits.

Voir [la recette détaillée](VERIFICATION_ADRESSES_MOBILE_COMPTES_2026-10-18.md). Les sections datées du 16 octobre ci-dessous décrivent les contrôles antérieurs; leurs blocages visuels locaux ont été dépassés par les essais HTTPS, sans valider pour autant tous les appareils ou une exploitation payante.

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

### Recette client complémentaire du 16 octobre

- 47 essais ciblés réussis : inscription et invitation, démarrage interrompu puis repris, connexion, analyse explicite, sauvegarde et retour au dossier, comparaison gratuite/Premium, PDF, filtres et navigation publique. Commande : `python -m unittest -v tests.test_beta_ui_journey tests.test_account_analysis_return tests.test_launch_demo tests.test_launch_ui_journeys tests.test_billing_ui tests.test_property_comparator_ui tests.test_comparison_report tests.test_saved_analyses_filters tests.test_public_ui_regressions`.
- Sur un vrai serveur Streamlit temporaire, une session WebSocket a ouvert l’accueil, activé la démonstration et récupéré le PDF par HTTP. Réponse 200, type `application/pdf`, contenu PDF de quatre pages et mention de démonstration vérifiés. Base et données fictives isolées, paiements et courriels désactivés, serveur arrêté après le contrôle.
- Les quatre pages de ce PDF ont été rendues et inspectées : tableaux lisibles, accents présents, aucune superposition observée dans cet exemple. Ce contrôle ne garantit pas la mise en page de toutes les saisies possibles.
- La suite complète de 406 tests a également réussi sur la version sauvegardée : [GitHub Actions 38966144157](https://github.com/loic5443/indice-immo-quebec/actions/runs/38966144157), commit `9bbdc3f`.
- **Contrôle visuel du site non terminé** : le navigateur distant ne peut pas joindre le serveur local (`ERR_CONNECTION_REFUSED`). Les essais Streamlit ne prouvent pas le rendu mobile ou ordinateur. Aucun contrôle Safari/iPhone ni essai visuel complet du site n’est déclaré réussi.

Les deux étapes suivantes restent :

1. **Prépublication** : rendre cette version accessible pour la recette visuelle sur téléphone et ordinateur, corriger les défauts observés, puis valider le fonctionnement HTTPS et le stockage sur l’hébergement choisi. Toute création d’hébergement payant exige d’abord l’accord du propriétaire; rien n’a été créé pour contourner cette limite.
2. **Activation commerciale** : configurer et tester Stripe en mode test et les courriels transactionnels, finaliser l’offre et le support, puis valider les paiements réels et ouvrir les abonnements après accord. La configuration actuelle n’encaisse rien.

La version de lancement est sauvegardée sur GitHub dans `codex/launch-october-2026`, commit `0c16d53`. Les préparatifs d’hébergement persistant sont dans `codex/hosting-persistent-2026-10-16`, commit `d6612f1`. Les corrections de parcours du 16 octobre sont préparées à partir de ce dernier état, dans `codex/premium-journey-2026-10-16`. Aucune fusion dans `main` ni publication de cette version commerciale n’a été faite. Un ancien déploiement Streamlit a existé; sa présence ne valide pas cette version.

GitHub est accessible et le connecteur Render est connecté. L’espace My Workspace a été confirmé et un aperçu gratuit existe depuis le 18 octobre; aucune ressource payante n’a été créée. Pour la phase d’intégration réelle, il reste le choix et l’accord sur l’hébergement, puis la configuration Stripe et Brevo. Un domaine personnel n’est pas nécessaire aux premiers contrôles HTTPS si l’hébergeur fournit une adresse. Les procédures et scénarios de recette sont dans `LANCEMENT_PREMIUM.md` et `HEBERGEMENT_RENDER.md`.

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
