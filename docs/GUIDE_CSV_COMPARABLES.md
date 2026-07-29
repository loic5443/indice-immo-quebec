# Guide CSV des comparables

Le fichier reste local et n'est jamais téléversé vers un service externe. L'utilisateur doit confirmer qu'il est autorisé à utiliser chaque donnée. Colonnes obligatoires : `address, property_type, sale_date, sale_price, living_area, land_area, year_built, units, bedrooms, bathrooms, distance_km, condition, source_declared, reference, notes, declared_closed_sale, usage_right_confirmed`.

`declared_closed_sale` doit confirmer une vente conclue. Une annonce active est exclue. Le modèle CSV est généré par `services.comparable_csv.csv_template()`.
