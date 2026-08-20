# Model Card — ImmoValue expérimental

Entrées : propriété et ventes comparables saisis par l'utilisateur avec droit d'utilisation confirmé. Sortie : médiane pondérée des prix par superficie, arrondie au millier, avec fourchette prudente. L'outil n'effectue aucune collecte, estimation officielle, recommandation d'offre ni prédiction d'acceptation.

La similarité utilise : type/unités 30 %, superficie 25 %, distance déclarée 15 %, année/état 10 %, terrain 10 %, configuration 5 %, qualité/provenance déclarée 5 %. Les dimensions absentes sont retirées du dénominateur; elles diminuent la confiance au lieu d'être supposées moyennes.

La confiance est plafonnée à 65/100 car les comparables restent déclarés et aucun backtesting réel n'est disponible. Elle baisse avec la dispersion et les ajustements manuels. Trois comparables admissibles sont le minimum absolu.

## Interprétation et comparaison

La carte de résultat présente séparément la valeur du rôle municipal, l’estimation ImmoValue et le prix demandé déclaré. La valeur du rôle est une référence fiscale officielle; elle peut être plus élevée ou plus basse que le prix du marché actuel, notamment selon l’année du rôle, le secteur et l’évolution récente du marché. Elle n’est jamais renommée valeur marchande, ni injectée dans le modèle. Lorsqu’un prix demandé existe, la conclusion déterministe indique seulement s’il est dans, au-dessus ou sous la fourchette, avec l’écart calculé. Elle ne recommande jamais d’acheter, de vendre ou de négocier.

Les statistiques agrégées ouvertes du Registre foncier servent uniquement de contexte documenté potentiel. Elles ne constituent ni une vente comparable ni une entrée du modèle.
