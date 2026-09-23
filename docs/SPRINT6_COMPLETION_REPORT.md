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

Le test `tests/test_beta_end_to_end.py` exécute 60 vérifications distinctes et tracées dans deux parcours sur des bases temporaires isolées, sans réseau ni données réelles. L'ancienne mention de 58 étapes était incorrecte : les étapes 25 à 58 répétaient uniquement un contrôle d'existence de la base. Les parcours actuels vérifient l'inscription transactionnelle, les invitations, le brouillon, le CSV, le consentement analytique, l'idempotence, les retours, les sources, l'export, la suppression, ainsi qu'un calcul financier sauvegardé, sa relecture isolée, ses scénarios et son PDF. `tests/test_beta_ui_journey.py` vérifie en plus le formulaire d'inscription, le refus d'une invitation invalide, les neuf écrans d'onboarding, l'interruption et la reprise, l'accès à Analyser, le calcul explicite d'un invité et la sauvegarde d'un dossier avec relecture dans Mes propriétés. Ces tests ne remplacent toujours pas une validation complète des 58 gestes dans l'interface.

## Intervention humaine nécessaire

Valider les licences de nouvelles sources, nommer le premier administrateur avec la commande locale, et effectuer la revue de sécurité avant ouverture publique.
