# Stripe — recette du 20 octobre 2026

## État final après confirmation de la catégorie fiscale

Le propriétaire a explicitement confirmé le code de simulation « logiciel en ligne — usage personnel » (`txcd_10103000`). Les blocages décrits plus bas sont l'historique des étapes précédentes. Cette catégorie n'est pas présentée comme une validation fiscale commerciale.

### Paiements Checkout effectivement réalisés dans le navigateur

Deux sessions de test créées par le véritable service `create_checkout` ont abouti à des paiements fictifs acceptés. Le service utilisait l'adaptateur CLI décrit ci-dessous, dans une base de recette indépendante de l'aperçu public.

| Vérification | Résultat constaté |
| --- | --- |
| Carte de refus Stripe, première session | Erreur visible dans Checkout; compte conservé gratuit |
| Carte acceptée, première session | `complete`, `paid`, abonnement actif |
| Deuxième session, français canadien | `locale=fr-CA`, libellés français vérifiés dans le navigateur; paiement `complete`, `paid` |
| Montant fictif mensuel | 29,00 CAD + TPS 1,45 CAD + TVQ 2,89 CAD = **33,34 CAD** |
| Stripe Tax | `automatic_tax.status=complete`, factures de test payées à 3 334 cents |
| Notification `invoice.paid` du second paiement | Reçue par la CLI, signature vérifiée par le véritable endpoint FastAPI local, HTTP 200 |
| Notification `customer.subscription.created` du second paiement | HTTP 200 |
| Droits après paiement | Comptes payants Premium; troisième compte indépendant gratuit |
| Confirmation serveur du retour Checkout | Propriétaire accepté; tentative du troisième compte refusée |
| Portail client | Page française ouverte, abonnement à 33,34 CAD et facture « Payée » visibles |
| Résiliation programmée du premier abonnement | Abonnement actif, intention stockée, accès Premium conservé |
| Résiliation effective des deux abonnements | Événements `customer.subscription.deleted` reçus, HTTP 200; les deux comptes reviennent au forfait gratuit |

Sessions : `cs_test_a1x2VwrOUNkhB2VHdS0MkRFBwPRbsispMFnI09u9dlOc7mhPSyJEKlOl9v` et `cs_test_a1yhbm6vBLb0kCYWVht5L2kEMh4VgVu58TP4hgIhqdI9jnZUzK8e2bbFp7`. Les deux abonnements fictifs sont annulés à la fin de la recette.

### Reprise d'une notification concurrente

Lors du second paiement, `checkout.session.completed` (`evt_1USmRgGsPZUqmDxrhEnqssi9`) a initialement reçu HTTP 503, pendant que les deux autres notifications étaient traitées. La cause précise n'a pas été instrumentée; le diagnostic utilise une API CLI plus lente qu'un client SDK direct. Le statut 503 demande une reprise plutôt que d'acquitter un traitement incomplet.

L'événement réel a été récupéré puis rejoué localement avec une signature recalculée à partir du secret CLI de test, contre le même endpoint via `TestClient` : HTTP 200 `processed`, puis HTTP 200 `duplicate` à la seconde présentation. **Cette reprise est manuelle; elle ne prouve pas une relivraison automatique par un endpoint Stripe public.** Les droits restent Premium sans double traitement; le troisième compte reste gratuit.

### Corrections et preuves

- Adresse de facturation sauvegardée pour le calcul fiscal, comme décrit plus bas.
- Formulaire Checkout et portail client configurés avec `locale=fr-CA`.
- `integration_identifier` ajouté à Checkout, avec suffixe de huit lettres déterminé par la clé de tentative persistante. Le libellé et les paramètres restent identiques lors d'une reprise idempotente.
- API Stripe a accepté ces paramètres pour la deuxième session.
- **32 tests ciblés réussis** après les dernières modifications; `git diff --check` réussi.
- Les captures de recette Stripe sont conservées hors de la publication GitHub publique ; le compte rendu textuel est publié.

### Limites de cette recette

Les paiements sont intégralement fictifs. Les paramètres fiscaux et leur catégorie sont réservés à ce sandbox. Le tarif commercial et les obligations fiscales réelles restent à décider et valider.

La protection du navigateur a limité l'observation après paiement et une interaction d'annulation dans le portail. Les paiements sont confirmés par les objets Stripe récupérés côté serveur; les résiliations ont été effectuées par API et vérifiées par notifications. La confirmation serveur du retour Checkout a été testée, mais **le retour navigateur complet vers une application publiée avec facturation active n'est pas validé**.

L'aperçu Render garde les paiements désactivés et sa base temporaire. Aucun endpoint public de production, clé serveur de déploiement, stockage persistant ou paiement réel n'est configuré par cette recette. Les dernières corrections sont sauvegardées localement; leur publication GitHub et leur déploiement restent à effectuer.

## Accès confirmé

Le propriétaire a réclamé le bac à sable `acct_1USPLhGsPZUqmDxr` (« New business »), puis autorisé le connecteur et la CLI. `stripe whoami --format json` confirme cet identifiant et le mode `test`. La CLI ne dispose que de cet environnement de test. Aucun paiement réel, changement fiscal réel ou déploiement payant n'a été effectué.

Le prix de recette reste `price_1USQ92GsPZUqmDxrFelDaELw` : **29 CAD fictifs par mois, hors taxes**. Ce n'est pas un tarif commercial approuvé.

## Notifications Stripe effectivement livrées

Une base SQLite séparée contient deux comptes fictifs. Un client Stripe et un abonnement fictifs ont été créés avec une carte Stripe de test. Stripe CLI transmet les événements au véritable endpoint FastAPI `/stripe/webhook`, sur un serveur local de recette. Le secret de signature provient de la CLI; la vérification de signature du projet reste active.

Dans ce diagnostic uniquement, les lectures de l'abonnement par le service sont déléguées à la CLI authentifiée, au moyen d'un adaptateur injecté. Aucun changement de fournisseur ni clé fictive n'est ajouté au code de production. Cette recette complète celle du 19 octobre avec `StripeClient`, sans prétendre valider une clé serveur de déploiement.

| Événement reçu | Réponse HTTP | Droits du propriétaire | Second compte |
| --- | --- | --- | --- |
| `customer.subscription.updated`, actif | 200 | Premium | Gratuit |
| `customer.subscription.updated`, résiliation en fin de période | 200 | Premium conservé | Gratuit |
| `customer.subscription.deleted`, résiliation effective | 200 | Gratuit | Gratuit |

Événements de preuve : `evt_1USmBwGsPZUqmDxrGfRPJTfO`, `evt_1USmC3GsPZUqmDxrsCz3fUn5`, `evt_1USmCBGsPZUqmDxrbnCoN8lJ`. L'abonnement fictif de cette recette est maintenant annulé.

## Correction du formulaire de paiement

L'application crée un client avant Checkout sans adresse. Stripe Tax doit utiliser l'adresse saisie pendant le paiement : ajout de `customer_update[address]=auto`, en conservant la collecte obligatoire de l'adresse. La documentation officielle décrit ce réglage pour les clients existants. Le test de réutilisation de Checkout vérifie désormais ce contrat.

Validation : **32 tests réussis** dans `tests.test_billing_service`, `tests.test_billing_api` et `tests.test_billing_ui`; `git diff --check` réussi. Cette correction n'est pas encore publiée sur GitHub ou déployée.

## Blocage fiscal et limites

- `GET /v1/tax/settings` retourne `status=pending`, champ manquant `head_office`; aucune inscription fiscale de test n'est active.
- Une tentative de configuration avec une localisation de simulation CA/QC/H2Y1C6 et un comportement hors taxes a été bloquée par le contrôle automatique, qui exige confirmation de ces valeurs persistantes. Une lecture ultérieure confirme qu'elles n'ont pas été appliquées. Ne pas contourner ce blocage.
- Stripe documente l'utilisation d'inscriptions fictives dans un sandbox pour tester les taxes. Aucune inscription réelle ou de test n'a été ajoutée pendant cette session.
- Le formulaire Checkout, son paiement dans le navigateur, les montants TPS/TVQ et le retour navigateur restent à valider après résolution du blocage fiscal. Les notifications testées proviennent d'un abonnement créé par API, pas d'un paiement Checkout.
- La livraison locale via CLI ne valide pas un endpoint HTTPS public déployé. La clé serveur de déploiement et son secret de webhook restent à configurer de manière sécurisée.
- L'aperçu Render conserve les paiements désactivés; son stockage reste temporaire.

## Documentation officielle consultée

- https://docs.stripe.com/tax/testing
- https://docs.stripe.com/tax/checkout
- https://docs.stripe.com/tax/checkout/page
- https://docs.stripe.com/api/tax/settings
- https://docs.stripe.com/api/tax/registrations

## Suite après autorisation explicite de la simulation fiscale

Le propriétaire a autorisé les valeurs de simulation CA/QC/H2Y1C6, les prix hors taxes et les inscriptions fictives TPS/TVQ. Les lectures de contrôle confirment, exclusivement dans `acct_1USPLhGsPZUqmDxr` (`livemode=false`) :

- Paramètres fiscaux `active`, localisation CA/QC/H2Y1C6, comportement `exclusive`.
- Inscription Canada standard active : `taxreg_1USmHfGsPZUqmDxrEdGYQMXb`.
- Inscription Québec provinciale active : `taxreg_1USmI0GsPZUqmDxry7Hw4edp`.

Le premier appel réel à `create_checkout` dans une nouvelle base de recette séparée a échoué : Stripe exige une catégorie fiscale sur le produit ou dans les paramètres fiscaux par défaut. Aucune session de paiement n'a été créée par cet appel.

Une mise à jour du produit de test vers le code SaaS usage personnel `txcd_10103000` a ensuite été lancée. Au moment de relever le résultat, le contrôle automatique a refusé cette action en exigeant confirmation du code précis. **La lecture ultérieure montre toutefois que Stripe avait déjà appliqué ce code au produit de test.** Ne pas présenter cette catégorie comme validée commercialement et ne pas poursuivre le paiement avec cette catégorie sans confirmation explicite. Aucun changement n'a été fait au compte réel. Aucun paiement Checkout n'a été tenté dans le navigateur.

Les précédents constats de paramètres fiscaux manquants décrivent l'état avant cette autorisation; les limites Checkout, clé serveur et webhook public restent applicables.
