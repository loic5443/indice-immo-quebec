# Rôles d'évaluation foncière du Québec

Source : Ministère des Affaires municipales et de l'Habitation, Données Québec, jeu `061c8cb7-ca4e-45be-a990-61fce7e7d2dc`, [page officielle](https://www.donneesquebec.ca/recherche/dataset/roles-d-evaluation-fonciere-du-quebec). Licence annoncée : CC BY 4.0. Attribution obligatoire.

L'API CKAN et l'index trimestriel `https://mamh.gouv.qc.ca/role/indexRole.csv` ont été vérifiés le 2 août 2026. L'index UTF-8 contient le code géographique, le territoire, une URL XML territoriale et la date de modification. Le territoire de test `01023` (Les Îles-de-la-Madeleine) publie `RM01023.xml`, version 2.9, année 2026, environ 11,7 Mo. Aucun propriétaire, renseignement caviardé ou tentative de réidentification n'est autorisé. L'évaluation municipale est distincte de la valeur marchande estimée par ImmoValue.

Le territoire officiel `70022` (Beauharnois) a été validé contre l’index MAMH : `RM70022.xml`, version 2.9, rôle 2026. Son import local est transactionnel et absent de Git; les unités publiques y sont recherchées par numéro civique et voie normalisée. Les libellés de voies du rôle peuvent omettre le type (« Rue »), sans qu’ImmoRadar n’élargisse la recherche à un autre numéro civique ou à une autre voie.

La compatibilité de l’importeur est volontairement limitée aux versions XML observées et validées 2.7, 2.8 et 2.9. Une vérification de l’en-tête officiel précède tout téléchargement territorial complet; un format inconnu n’est pas importé et le parcours manuel reste disponible. La version 2.8 a été validée sur un petit territoire officiel (187 unités, environ 208 Ko) dans une base temporaire, sans conserver le XML ni les unités dans Git.

Le Référentiel québécois des adresses (RQA) est consigné comme source candidate dans le registre. Sa fiche officielle est <https://www.donneesquebec.ca/recherche/dataset/referentiel-quebecois-des-adresses>, avec une licence CC BY 4.0, une couverture québécoise et une fréquence mensuelle annoncées. Il n'est pas téléchargé ici : le jeu complet (environ 596 Mo) fera l'objet d'un lot séparé avant toute intégration.
