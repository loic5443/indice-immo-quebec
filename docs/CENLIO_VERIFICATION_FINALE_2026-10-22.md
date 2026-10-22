# Cenlio — compte rendu de vérification du 22 octobre 2026

## Résultat

Renommage terminé dans la version locale : pages, navigation, titre navigateur, messages, expéditeur des courriels, rapports PDF et leurs polices, téléchargements, documentation et nom de l’image d’accueil. Signature d’accueil : « Cenlio — L’immobilier, plus clair. »

## Vérifications réussies

- Suite complète : **429 tests réussis en 58,701 s** après les dernières modifications.
- Chargement supplémentaire des 11 destinations de l’application via Streamlit AppTest : Accueil, Analyser, Mes propriétés, Marché, Premium, Mon compte, Démonstration, À propos, Confidentialité, Donner mon avis et Administration. Aucune exception ; aucune ancienne marque identifiée dans les textes contrôlés. Administration vérifiée ici comme visiteur non autorisé, sans contournement des droits.
- Tests existants de recherche et suggestions d’adresse, formulaire, consentement, données officielles et isolation des sessions réussis. Il ne s’agit pas d’un nouveau relevé en direct de toutes les adresses québécoises.
- Tests de comptes, connexion, récupération de mot de passe, persistance entre processus, restauration de sauvegarde et séparation des propriétaires réussis.
- Nouvelle migration 0029 : remplacement du seul ancien libellé de provenance généré. Le test confirme que les comptes, identifiants, mots de passe, chiffres et instantanés restent identiques, et que la migration peut être relancée sans effet supplémentaire.
- Tests Premium, quotas et intégration de paiement simulée réussis ; aucun paiement réel ni nouvel envoi de courriel effectué.
- Rapport d’analyse : 4 pages générées ; rapport comparatif : 3 pages. Texte extrait et données PDF contrôlés : marque Cenlio présente, ancienne marque absente dans ces exemples.
- Compilation Python réussie ; pip check sans dépendance cassée ; git diff --check propre.

Les premières vérifications après ajout de la migration ont signalé cinq attentes de tests restées à la version de schéma précédente. Elles ont été mises à jour, puis les 19 tests ciblés et la suite complète ont réussi.

## Limites et étapes de lancement

- Contrôles exécutés sur le code local, pas sur une version déployée contenant ces modifications.
- Tentative de navigateur vers la version locale : connexion refusée par le navigateur distant. Aucune validation visuelle réelle sur téléphone ou navigateur n’est revendiquée pour cette version. Les parcours ont été vérifiés avec AppTest ; les styles mobiles existants restent en place.
- L’aperçu hébergé reste sur sa version précédente. La branche locale diverge de sa branche distante : synchronisation à résoudre sans écraser l’historique, puis déploiement et recette du navigateur.
- Le stockage permanent sur l’hébergement reste à mettre en place et à vérifier. Les tests de persistance locale ne rendent pas durable le disque de l’aperçu gratuit.
- Courriels de l’application et paiements réels restent à valider en production. Le domaine n’a pas été acheté ; le contrôle officiel au registre québécois et des marques proches reste ouvert.
- Les variables de configuration et identifiants techniques de compatibilité restent inchangés. Certains anciens noms restent donc dans le code technique, les URL externes et l’historique Git ; les supprimer aveuglément pourrait rompre les intégrations.
- Les outils disponibles ne permettent pas de modifier les titres, messages ou épingles des conversations ChatGPT. Aucun historique de conversation n’a été modifié.

Aucun changement effectué aux comptes ou noms chez les prestataires externes, aucune dépense engagée et aucune activation de paiement réel.
