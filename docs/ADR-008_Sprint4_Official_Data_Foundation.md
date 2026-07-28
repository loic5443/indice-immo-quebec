# ADR-008 — fondation des données officielles

Date : 2026-07-28 · Statut : accepté.

Le produit conserve un registre versionné des sources et sépare les fournisseurs, la validation, les services et les dépôts SQLite. Une observation est persistée de manière immuable avec sa source, ses dates, son unité, son territoire, son statut de qualité et l'exécution qui l'a obtenue. Les échecs et valeurs invalides sont mis en quarantaine; le service peut exposer la dernière valeur valide avec un indicateur de fraîcheur. L'absence de donnée est un état normal de l'interface.

À ce sprint, seule la série V39079 de la Banque du Canada est intégrée. Aucun prix, rendement, risque, tendance ou comparatif de villes du Québec n'est publié tant que la source et la méthode ne sont pas validées. Les indicateurs externes sauvegardés sont un contexte informatif, sans influence sur ImmoEngine, son score ou son verdict.
