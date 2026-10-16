# ImmoRadar

Pour préparer l’hébergement avec disque persistant et une adresse HTTPS fournie par Render, consulter [le guide de déploiement](docs/HEBERGEMENT_RENDER.md). La création de ressources payantes reste soumise à l’accord du propriétaire.

ImmoRadar aide à comprendre un dossier immobilier : renseignements publics autorisés, valeur municipale, calculs financiers, ImmoScore et suivi des changements vérifiables.

## Ce que l’application fait

- Recherche d’adresse québécoise après consentement explicite.
- Valeur au rôle municipal lorsqu’un territoire MAMH compatible est disponible. C’est un repère fiscal, pas une valeur marchande.
- ImmoValue seulement lorsque l’utilisateur fournit au moins trois ventes comparables admissibles et autorisées.
- Analyse financière, scénarios, ImmoScore, sauvegarde de dossiers et alertes factuelles selon les droits du compte.

## Données et limites

ImmoRadar ne fabrique pas de prix de vente, de rendement locatif ou de niveau de risque municipal. Les comparaisons de municipalités n’apparaissent que lorsque des indicateurs officiels comparables ont été chargés. Le Référentiel québécois des adresses (RQA) sert à améliorer la recherche d’adresse; le rôle municipal reste disponible territoire par territoire. Les chiffres financiers sont les hypothèses saisies par l’utilisateur.

## Lancer l’application

```powershell
.\.venv\Scripts\python.exe -m streamlit run indice_immo.py --server.port 8501
```

## Repères du projet

- `components/` : interface et parcours utilisateur.
- `calculations/` et `domain/` : formules financières et moteurs déterministes testables.
- `services/`, `repositories/` et `providers/` : règles applicatives, stockage local et sources officielles.
- `migrations/` : évolution rétrocompatible de SQLite.
- `docs/` : documentation produit, sources, méthodes et limites.
- `tests/` : contrôles automatisés du produit et de la confidentialité.

## Préparer le lancement Premium

Le parcours de facturation Stripe et le déploiement avec stockage persistant sont décrits dans [le guide de lancement](docs/LANCEMENT_PREMIUM.md). Les paiements sont désactivés par défaut. La configuration Stripe et la recette sur HTTPS doivent être terminées avant une offre payante.

Tests : `python -m pip install -r requirements-dev.txt`, puis `python -m unittest discover -s tests -q`.
