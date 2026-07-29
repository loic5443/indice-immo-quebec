# ADR-009 — ImmoValue expérimental

ImmoValue opère uniquement sur des comparables manuels ou CSV autorisés par l'utilisateur. Les instantanés sont stockés dans `analyses.immovalue_json`; les anciennes analyses restent lisibles grâce à une valeur par défaut vide. L'estimation est une médiane pondérée par similarité des prix par superficie, avec une fourchette prudente et une confiance plafonnée à 65/100 avant validation historique. Aucune collecte externe, évaluation officielle ou intégration à ImmoScore n'est autorisée dans ce sprint.
