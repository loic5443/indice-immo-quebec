# Revue technique des sources et de la confidentialité — 23 septembre 2026

Cette revue vérifie la cohérence du produit avec les fiches officielles et le code. Elle ne remplace pas un avis juridique, une vérification contractuelle des licences ou un audit de sécurité de production.

## Sources

| Source | Usage actuel | Attribution et limite à respecter |
| --- | --- | --- |
| [Rôles d’évaluation foncière du Québec](https://www.donneesquebec.ca/recherche/dataset/roles-d-evaluation-fonciere-du-quebec) | Valeurs publiques du rôle municipal, lorsqu’un territoire est synchronisé | Licence CC BY 4.0 selon la fiche officielle; afficher MAMH / Données Québec, année et date de référence. Ne pas révéler de propriétaire ni réidentifier une personne. Le rôle est un repère fiscal, pas une valeur marchande. |
| [Référentiel québécois des adresses](https://www.donneesquebec.ca/recherche/dataset/referentiel-quebecois-des-adresses) | Suggestions locales seulement si le répertoire a été chargé | Licence CC BY 4.0 selon la fiche officielle; attribution MRNF / Données Québec. La couverture du répertoire ne garantit ni la présence d’un rôle synchronisé ni une correspondance exacte. |
| [Adresses Québec — géocodeur REST](https://www.donneesquebec.ca/recherche/dataset/adresses-quebec/resource/64cbcdfc-4dd6-42e7-9a5d-489e775da83b) | Suggestions officielles à la demande | La fiche de cette ressource précise CC BY 4.0; attribution MRNF / Données Québec. Requête seulement après consentement. La licence n'est pas une garantie de disponibilité, de capacité de service ou de couverture exhaustive. |
| [Imagerie orthorectifiée du Québec — service WMS utilisé](https://donneesquebec.ca/recherche/dataset/imagerie-orthorectifiee-du-quebec/resource/c55df227-c002-40c2-ad6b-499ab2323626) | Contexte aérien facultatif, si couvert | La fiche de cette ressource WMS précise CC BY 4.0; attribution MRNF / Données Québec. Couverture et année d'acquisition variables; ce n’est pas une photo de façade ni une preuve de l’état du bâtiment. Ne pas extrapoler la licence aux autres couches ou services non vérifiés. |
| [Banque du Canada — Valet](https://www.bankofcanada.ca/valet/docs/) | Taux directeur observé et contexte daté | Les [conditions de la Banque](https://www.bankofcanada.ca/terms/) imposent attribution, exactitude et respect des limites de requêtes. L’article 1.3 impose, avant une distribution payante de contenu de la Banque, un avis indiquant sa provenance et sa disponibilité gratuite sur le site de la Banque. Ne pas utiliser son logo sans autorisation. |

Les indicateurs de prix moyen, variation et rendement par ville restent différés : aucune source et méthode autorisées ne sont intégrées. Le registre ne doit donc pas les marquer comme intégrés. Les ventes comparables détaillées sont fournies par l’utilisateur avec confirmation de provenance et de droits; les statistiques agrégées du Registre foncier ne deviennent pas des ventes comparables individuelles.

## Vérifications de sécurité réalisées

- Le parcours navigateur s’exécute sur une base et des comptes fictifs isolés; aucune base réelle n’a été modifiée.
- Le diff destiné à la demande de fusion est contrôlé pour les noms de fichiers sensibles, les marqueurs de clé privée et les formats de clés connus, sans afficher de valeur détectée.
- `.gitignore` exclut les bases SQLite, secrets locaux, certificats, fichiers Python compilés et PDF générés.
- Les tests couvrent les autorisations de compte, le consentement préalable aux recherches publiques, l’isolation des analyses, la télémétrie en liste blanche et l’expurgation des diagnostics. Ce n’est pas un test d’intrusion.

## Décision avant diffusion

La validation technique autorise la poursuite de la revue de la demande de fusion. Elle n’autorise pas à promettre la couverture de toutes les adresses, une photo de chaque propriété ou une valeur marchande sans comparables. Les fiches officielles du géocodeur et du WMS utilisés annoncent toutes deux CC BY 4.0, mais une personne responsable doit encore valider la conformité des attributions dans le produit, le traitement des données personnelles, la sécurité de déploiement et le texte d’avis Banque du Canada avant toute offre payante ou publication générale. La fusion sur `main` reste une décision distincte.
