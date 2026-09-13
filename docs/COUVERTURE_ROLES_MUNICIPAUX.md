# Couverture des rôles municipaux

ImmoRadar utilise seulement les rôles d’évaluation foncière publiés par le MAMH. La valeur affichée est un repère fiscal officiel; elle n’est jamais une estimation de valeur marchande.

Le Référentiel québécois des adresses aide à trouver une adresse dans l’ensemble du Québec. La disponibilité du rôle municipal est distincte : chaque territoire est importé séparément, avec son année, son empreinte et ses champs publics autorisés.

## Synchronisation contrôlée

`scripts/sync_role_coverage.py` traite les territoires de l’index officiel un à la fois. Par défaut, un lot se limite à 10 territoires et 250 Mo. Les rôles déjà actifs et à jour sont ignorés; une interruption se reprend avec un nouveau lot. Un territoire désactivé par l’administration ne sera jamais téléchargé automatiquement.

Une exécution complète exige du stockage dimensionné et une surveillance des publications du MAMH. Elle doit être lancée en lots mesurés, pas comme un téléchargement massif non contrôlé.
