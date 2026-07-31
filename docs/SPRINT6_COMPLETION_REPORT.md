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

Le test `tests/test_beta_end_to_end.py` exécute 58 vérifications tracées dans une base temporaire isolée, sans réseau ni données réelles.

## Intervention humaine nécessaire

Valider les licences de nouvelles sources, nommer le premier administrateur avec la commande locale, et effectuer la revue de sécurité avant ouverture publique.
