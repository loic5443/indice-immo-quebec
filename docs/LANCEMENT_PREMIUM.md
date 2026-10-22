# Lancement Cenlio Premium — cible 22 octobre 2026

## Livré dans cette branche

- Offre mensuelle CAD affichée à partir du prix Stripe réel, sans montant inventé dans le produit.
- Checkout hébergé Stripe, compte client lié au compte Cenlio, clés d’idempotence et protection contre un deuxième abonnement.
- Taxes automatiques dans Checkout : Stripe Tax doit être configuré avant un achat réel. Aucun taux fiscal n’est codé en dur.
- Activation après vérification serveur du client, du propriétaire, du mode, du prix et de l’état de l’abonnement.
- Webhooks signés avec refus des modes incompatibles, traitement idempotent et récupération de l’état courant pour les événements en retard.
- Retour au compte après paiement, récupération après reconnexion et actualisation manuelle si le retour est perdu.
- Portail client : factures, carte et annulation du renouvellement (fonctionnalités à activer dans Stripe).
- Droits actualisés à chaque lecture de compte; retrait après impayé, annulation effective ou expiration de la période vérifiée.
- Activation commerciale du quota gratuit. Consommation transactionnelle pour éviter les doubles estimations concurrentes.
- SQLite configurable sur un volume persistant et architecture de déploiement Docker + HTTPS.

## Configuration requise

L’application et le serveur webhook doivent partager **le même fichier SQLite**. Ne pas les déployer sur deux disques distincts. Cette première architecture utilise une seule machine et une seule instance de chaque service; un changement de stockage sera nécessaire pour plusieurs répliques.

1. Créer/valider le compte Stripe de l’entreprise. Créer un produit Premium et un prix récurrent mensuel en CAD. Le montant relève du propriétaire; 29 $ dans les tests est une donnée fictive, pas un tarif décidé.
2. Activer le portail client avec factures, modification de carte et annulation en fin de période. Ne pas autoriser le changement de prix vers un prix que cette version ne reconnaît pas.
3. Configurer Stripe Tax, les informations commerciales, les reçus et les conditions applicables avant le passage en production.
4. Choisir le serveur et le domaine. Pointer le DNS vers le serveur. Installer Docker Compose et ouvrir les ports 80/443.
5. Copier `.env.example` vers `.env` sur le serveur. Saisir les secrets dans la configuration privée, jamais dans le dépôt ou une conversation.
6. Démarrer avec `docker compose up --build -d`. Les migrations initiales sont exécutées avant les deux services. Caddy assure HTTPS et le transfert WebSocket à Streamlit.
7. Dans Stripe, enregistrer `https://<domaine>/stripe/webhook` et recopier son secret de signature privé dans `STRIPE_WEBHOOK_SECRET`.
8. Abonner le webhook à `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `customer.subscription.paused`, `customer.subscription.resumed`, `invoice.paid`, `invoice.payment_failed`, `invoice.payment_action_required`.
9. Activer `IMMORADAR_BILLING_ENABLED=1` en mode test avec une clé et un prix de test. Redémarrer les services après un changement de configuration. Réaliser la recette ci-dessous.
10. Créer une base de production séparée de la base de test. Configurer clé, prix et webhook de production puis `IMMORADAR_BILLING_MODE=live`. Ne jamais réutiliser les comptes clients Stripe de test pour de vrais paiements.

## Recette avant ouverture payante

Les tests automatisés utilisent un fournisseur simulé et des signatures locales. Ils ne remplacent pas cette recette dans un vrai environnement Stripe de test.

- Visiteur → création de compte → analyse gratuite → Premium → prix et taxes visibles → Checkout.
- Carte de test réussie → Premium actif → sauvegarde de deux dossiers → comparaison → rapport PDF → suivi.
- Retour fermé après paiement → activation par webhook → reconnexion → mêmes droits et dossiers.
- Reconnexion après retour Stripe : le bon compte récupère son paiement; un autre compte ne reçoit jamais ses droits.
- Double clic → un seul checkout/abonnement. Annulation du checkout → compte gratuit.
- Carte refusée/notification impayée → droits gratuits; régularisation → droits Premium.
- Annulation en fin de période → accès jusqu’à échéance; annulation effective → gratuit, dossiers conservés.
- Test et production isolés. Clés privées absentes des pages, diagnostics, commits et logs.
- Sauvegarde/restauration SQLite vérifiée, y compris les dossiers et la correspondance des abonnements.
- Import d’adresses/rôles et couverture vérifiés sur les territoires annoncés. Attribution et avis de sources contrôlés suivant l’audit du 23 septembre.

## Éléments encore requis pour un service commercial

Le code de facturation ne suffit pas à déclarer le produit prêt à vendre. Il reste à valider les parcours ci-dessus sur le site HTTPS, la qualité de l’analyse et les limites de couverture, puis l’offre auprès de premiers clients.

- Adresse de support et procédure pour remboursements, litiges et suppression de compte. La suppression d’un compte lié à Stripe est bloquée tant qu’un opérateur n’a pas résolu son dossier, pour éviter une facturation sans propriétaire.
- Surveillance des erreurs de webhook, sauvegardes hors du serveur et restauration réelle.
- La récupération de mot de passe et les limites de connexion sont implémentées. Configurer Brevo pour les courriels transactionnels et tester la délivrabilité réelle; vérifier aussi les protections et limites du serveur exposé à Internet.
- Conditions d’abonnement, confidentialité, politique de remboursement, coordonnées commerciales et attributions des données publiques.
- Alertes par courriel : consentement distinct et configuration Brevo. Le worker optionnel peut être lancé avec le profil Compose `operations`; le suivi compare les instantanés sauvegardés et ne surveille pas toutes les annonces du marché.
- La capacité d’inscription reste régie par `beta_settings` (100 comptes initialement). Ajuster explicitement dans l’administration avant le lancement, sans supprimer le contrôle de capacité.

## Séquence proposée sur dix jours

| Période | Résultat à vérifier |
| --- | --- |
| J1–J2 | Facturation, droits, tests et version de revue sauvegardée |
| J3–J4 | Domaine, serveur persistant, Stripe test et recette complète |
| J5–J6 | Récupération de compte, limites de connexion, support et qualité mobile |
| J7–J8 | Parcours avec premiers testeurs et corrections liées à leur usage |
| J9–J10 | Restauration, supervision, configuration commerciale et ouverture contrôlée |

La date du 22 octobre est une cible, pas une publication planifiée automatiquement.

## Références d’intégration

- https://docs.stripe.com/checkout/fulfillment
- https://docs.stripe.com/billing/subscriptions/webhooks
- https://docs.stripe.com/api/checkout/sessions/create
- https://docs.stripe.com/api/customer_portal/sessions/create


## Compléments du lot autonome du 12-13 octobre

- Démonstration sans compte avec loyers, prix et taux modifiables, calculs de production et exemple PDF clairement fictif.
- Critères Premium persistants par compte : prix, flux mensuel, rendement sur capital, DSCR et scénario prudent. Le tableau agrège le dernier instantané de chaque dossier; les données absentes ne passent jamais un critère.
- Plafond de prix mathématique selon les seuils et hypothèses fixes; aucune estimation marchande ou qualification du prêteur n’est annoncée. Les taxes, loyers, mise de fonds et coûts restent fixes, sans assurance hypothécaire ajoutée automatiquement.
- Critères courants et simulation du plafond exportés dans le rapport PDF. Polices françaises intégrées pour éviter une substitution différente selon l’ordinateur du lecteur.
- Lien de récupération valide 30 minutes, à usage unique, stocké sous forme de hash. Le changement de mot de passe invalide les anciennes sessions.
- Limites par identité hachée : 10 tentatives de connexion et 3 demandes de récupération par fenêtre de 15 minutes. Réponse publique identique pour un courriel de récupération connu ou inconnu.
- Migrations transactionnelles et sérialisées, avec rollback de la structure et de sa version en cas d’échec.
- Sauvegarde cohérente via l’API SQLite, intégrité et références vérifiées, fichiers privés, sans écrasement des sauvegardes existantes.
- Worker optionnel de sauvegarde et de notifications consenties. Il est désactivé par défaut, ne journalise que des agrégats et ne supprime aucune sauvegarde.

### Courriels de récupération

Configurer `IMMORADAR_AUTH_EMAIL_ENABLED=1`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL` et une URL publique HTTPS. La récupération est transactionnelle et séparée du consentement marketing ou des alertes. Sans cette configuration, l’interface annonce l’indisponibilité de l’envoi au lieu de prétendre envoyer un lien.

### Sauvegardes et worker

- Commande ponctuelle : `python -m scripts.backup_database --destination /chemin/prive/nouvelle-sauvegarde.sqlite`.
- Vérification : `python -m scripts.backup_database --source /chemin/prive/sauvegarde.sqlite --verify-only`.
- Cycle périodique : configurer `IMMORADAR_OPERATIONS_ENABLED=1` et, si souhaité, `IMMORADAR_BACKUPS_ENABLED=1`, puis `docker compose --profile operations up --build -d`.
- Les sauvegardes du volume applicatif doivent être copiées hors de la machine. La rotation et la supervision du stockage restent à configurer sur l’hébergement; ce code ne détruit pas les anciennes copies.
- Avant restauration, arrêter les services applicatifs, vérifier la sauvegarde, conserver une copie de la base actuelle puis restaurer le fichier vérifié sur le volume avec les bons droits. Tester d’abord sur une instance isolée.
- Diagnostic sans appel réseau : `python -m scripts.launch_readiness`. Il ne prouve ni le bon fonctionnement HTTPS, ni la délivrabilité, ni le paiement en production.
