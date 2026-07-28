# Runbook — source indisponible

La page doit conserver la dernière observation `valid` avec son statut de fraîcheur. Sans cache valide, elle affiche « donnée indisponible »; elle n'invente jamais de repli. Toute erreur réseau, réponse non conforme, unité imprévue, valeur hors plage ou date invalide est enregistrée dans `source_runs`; les observations invalides sont mises en quarantaine et exclues de l'interface, des analyses et des rapports.
