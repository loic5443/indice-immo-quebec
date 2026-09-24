# Vue aérienne officielle

Après le consentement à la recherche publique et la sélection d’une adresse, ImmoRadar peut afficher une vue aérienne officielle fournie par le ministère des Ressources naturelles et des Forêts du Québec (MRNF), à partir du jeu [Imagerie orthorectifiée du Québec](https://www.donneesquebec.ca/recherche/dataset/3eec3d05-61c1-4bcb-bf22-2d4bd71e2c0d).

Cette vue est un contexte visuel seulement. Elle n’est jamais utilisée pour calculer ImmoValue, ImmoScore, le flux de trésorerie ou toute autre conclusion. La valeur au rôle municipal demeure un repère fiscal distinct; elle n’est pas une valeur marchande.

L’image est demandée uniquement au service WMS officiel du MRNF, par HTTPS, après le consentement. Elle reste en mémoire pour la session courante et n’est pas ajoutée aux brouillons, analyses sauvegardées, rapports PDF, journaux, diagnostics ou événements de télémétrie. Les coordonnées nécessaires au rendu ne sont jamais conservées après la requête.

La couverture et l’année de prise de vue varient. ImmoRadar essaie d’abord les couches officielles récentes de l’inventaire écoforestier, puis des couches récentes de planification et suivi; il n’effectue qu’un nombre limité de requêtes après consentement. Si aucun rendu officiel exploitable n’est disponible, ImmoRadar indique simplement que la vue aérienne est indisponible et l’analyse peut se poursuivre en mode manuel.

Attribution : MRNF — Imagerie orthorectifiée du Québec. Licence : CC BY 4.0, selon la fiche officielle Données Québec.
