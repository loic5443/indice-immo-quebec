# ImmoRadar

Application Streamlit d'aide à l'analyse d'un projet immobilier locatif au Québec et au Canada.

## Architecture

- `data/real_data.py` : données externes récupérées sans secret (taux directeur de la Banque du Canada).
- `data/simulated_data.py` : indicateurs et tendances d'exemple, explicitement identifiés comme simulés.
- `calculations/real_estate.py` : validations et formules financières testables.
- `components/` : interface Streamlit, formulaires et présentation des résultats.
- `tests/` : tests unitaires des calculs importants.

## Lancer l'application

```powershell
.\.venv\Scripts\streamlit.exe run indice_immo.py
```

## Notes sur les données

Le taux directeur canadien est récupéré en direct lorsque la source est disponible. L'inflation, le chômage et les statistiques de villes sont simulés. Les chiffres saisis dans la fiche d'analyse sont vos propres hypothèses.
