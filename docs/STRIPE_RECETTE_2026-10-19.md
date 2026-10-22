# Stripe — recette indépendante du 19 octobre 2026

## Environnements

Le connecteur donne accès au compte commercial `acct_1USOYF29Iy10Zomf` en mode réel uniquement. Aucun objet commercial ni paiement réel n’a été créé ou modifié.

Un bac à sable indépendant, non encore réclamé par le propriétaire, a été provisionné avec Stripe CLI 1.54.1 : `acct_1USPLhGsPZUqmDxr`. La CLI annonce une expiration le **26 octobre 2026**. Il ne remplace pas la configuration du compte commercial. Ses clés et son lien privé de récupération ne sont pas enregistrés dans le dépôt.

## Configuration effectivement créée dans ce bac à sable

- Produit « Cenlio Premium — TEST uniquement ».
- Prix récurrent mensuel de **29 CAD fictifs**, hors taxes. Ce montant ne constitue pas une décision de tarif commercial.
- Configuration du portail : historique de factures, modification du moyen de paiement, annulation en fin de période; changement d’offre désactivé.
- Client et abonnement fictifs avec le moyen de paiement de test Stripe `pm_card_visa`. L’abonnement a été annulé au terme de la recette.

## Résultats avec les vrais objets API Stripe

La recette utilise une base SQLite locale isolée et le service de facturation du projet, avec un `StripeClient` réellement connecté au bac à sable. Les certificats TLS sont vérifiés avec le magasin système de cet environnement de travail.

| Vérification | Résultat |
| --- | --- |
| Offre chargée à partir du prix Stripe | 29,00 $ CA / mois, mode test |
| Abonnement Stripe de test | `active` |
| Actualisation serveur de l’abonnement | Premium activé pour le propriétaire |
| Autre compte Cenlio | Reste gratuit |
| Création d’une session du portail client | Réussie |
| Annulation en fin de période | Accès conservé et intention d’annulation stockée |
| Annulation effective dans Stripe | Accès Premium retiré |

## Correction

La validation de configuration n’acceptait que les clés `sk_`. Elle accepte désormais les clés restreintes `rk_test_` et `rk_live_`, ainsi que `rkcs_test_` pour les bacs à sable temporaires. Les clés publiques, les clés du mauvais mode et `rkcs_live_` restent refusées. Une régression automatisée couvre ces cas.

## Limites et reste à faire

- La clé du bac à sable non réclamé reçoit un refus de permission sur la configuration Stripe Tax. Les taxes n’ont pas été configurées ni déclarées validées.
- La recette crée un abonnement directement par API avec un moyen de paiement fictif; elle **ne valide pas le formulaire de paiement Checkout**, son retour navigateur ou la livraison des webhooks Stripe.
- Aucun webhook public n’a été enregistré pour ce bac à sable. Le secret utilisé par le diagnostic local n’est pas un secret de webhook déployé.
- Le portail a été créé par API, mais son interaction complète dans un navigateur reste à vérifier.
- Le bac à sable doit être réclamé et un accès adéquat doit être autorisé avant de poursuivre les essais de taxes et Checkout. Ne jamais désactiver les contrôles de taxes pour faire passer la recette.
- Les clés de ce bac à sable n’ont pas été ajoutées à l’aperçu Render. Son point d’entrée conserve la facturation désactivée et son stockage reste temporaire.
- Le tarif commercial, les inscriptions fiscales applicables, les informations légales, l’accès de production et l’hébergement persistant restent à valider avant toute ouverture payante.

## Références officielles consultées

- https://docs.stripe.com/sandboxes
- https://docs.stripe.com/sandboxes/claimable-sandboxes
- https://docs.stripe.com/keys
- https://docs.stripe.com/tax/set-up
- https://docs.stripe.com/api/billing_portal/configurations/create
- https://docs.stripe.com/api/subscriptions/create
