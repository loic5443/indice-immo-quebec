# Rapport de clôture — Sprint 6

## Terminé et accessible

- comptes locaux avec mots de passe hachés, session et suppression;
- onboarding persistant;
- analyses financières, ImmoEngine, scénarios et sauvegardes;
- ImmoValue expérimental, comparables manuels et import CSV local;
- invitations hachées, rôle administrateur et administration locale protégée;
- retours bêta et exports expurgés;
- télémétrie à liste blanche avec consentement et idempotence;
- sources officielles, mode dégradé et diagnostics expurgés.

## Expérimental

ImmoValue et ses comparables sont déclaratifs et non une évaluation officielle. Les métriques administratives sont agrégées et masquent les petits groupes.

## Non disponible / reporté après bêta

Paiements, Stripe, accès public, collecte automatique d'annonces, comparables autorisés externes, IA générative et quotas.

## Validation automatisée

Le test `tests/test_beta_end_to_end.py` exécute 43 vérifications distinctes et tracées dans une base temporaire isolée, sans réseau ni données réelles. L'ancienne mention de 58 étapes était incorrecte : les étapes 25 à 58 répétaient uniquement un contrôle d'existence de la base. Le test actuel vérifie notamment l'inscription transactionnelle, l'épuisement d'une invitation, le brouillon, le CSV, le consentement analytique, l'idempotence, les retours, une source, l'export et la suppression. Il s'agit d'un parcours de fumée au niveau des services, non d'une validation complète de l'interface, du PDF et de tous les 58 gestes historiques.

## Intervention humaine nécessaire

Valider les licences de nouvelles sources, nommer le premier administrateur avec la commande locale, et effectuer la revue de sécurité avant ouverture publique.
