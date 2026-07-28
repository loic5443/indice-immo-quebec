# ADR-007 - Instantanés financiers enrichis et scénarios

Date : 2026-07-28

ImmoRadar conserve désormais, avec chaque analyse sauvegardée, les hypothèses financières enrichies, les scénarios déterministes et les tests de résistance au format JSON versionné dans SQLite. Cette décision préserve la lecture des analyses historiques tout en permettant au rapport PDF de reproduire fidèlement l’instantané sauvegardé.

Les scénarios et le rapport ne consultent aucune donnée de marché simulée ou de propriété. Le module n’est pas ImmoValue : il ne produit aucune estimation de valeur ni comparable. Les scénarios favorables sont explicitement des sensibilités et non des prévisions.
