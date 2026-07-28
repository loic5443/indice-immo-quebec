# Dictionnaire de données — Sprint 4

- `market_observations.value` : valeur observée publiée par une source intégrée; jamais une estimation ImmoRadar.
- `market_observations.observed_at` : date de l'observation chez la source.
- `market_observations.retrieved_at` : date de récupération locale.
- `market_observations.quality_status` : `valid` ou `quarantined`; une valeur en quarantaine n'est jamais visible publiquement.
- `market_observations.content_hash` : empreinte dédupliquant une observation identique sans écraser l'historique.
- `analyses.market_context_json` : instantané informatif des indicateurs officiels disponibles à la sauvegarde; aucun champ de cet instantané n'alimente le score ou le verdict.

Classification : `observed` (source officielle), `declared` (utilisateur), `derived` (calcul), `modelled` (moteur explicable), `simulated` (développement uniquement, hors parcours public).
