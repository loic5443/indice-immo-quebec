# Model Card — ImmoValue expérimental

Entrées : propriété et ventes comparables saisis par l'utilisateur avec droit d'utilisation confirmé. Sortie : médiane pondérée des prix par superficie, arrondie au millier, avec fourchette prudente. L'outil n'effectue aucune collecte, estimation officielle, recommandation d'offre ni prédiction d'acceptation.

La similarité utilise : type/unités 30 %, superficie 25 %, distance déclarée 15 %, année/état 10 %, terrain 10 %, configuration 5 %, qualité/provenance déclarée 5 %. Les dimensions absentes sont retirées du dénominateur; elles diminuent la confiance au lieu d'être supposées moyennes.

La confiance est plafonnée à 65/100 car les comparables restent déclarés et aucun backtesting réel n'est disponible. Elle baisse avec la dispersion et les ajustements manuels. Trois comparables admissibles sont le minimum absolu.
