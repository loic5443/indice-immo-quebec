# Méthodologie ImmoValue expérimentale

Seuls les comparables déclarés comme ventes conclues, avec droit confirmé et données minimales, peuvent être retenus. La valeur centrale est une médiane pondérée des valeurs `prix de vente / superficie × superficie du sujet`, plus tout ajustement manuel déclaré. Les ajustements monétaires automatiques pour rénovations, garages ou chambres sont volontairement absents.

La fourchette est au minimum ±10 %, puis s'élargit selon la dispersion, le nombre de comparables et les ajustements manuels. Les résultats sont arrondis au millier. Sans trois comparables admissibles, aucune estimation n'est affichée.

## Parcours guidé et provenance

L’interface guidée demande un comparable à la fois : description ou adresse, prix de vente **conclu**, date, type, superficie habitable, ville et provenance. La confirmation de vente conclue et le droit d’utilisation déclaré sont obligatoires. Les éléments facultatifs (terrain, année, pièces, distance et ajustement manuel) restent visibles et ne sont jamais devinés. Un doublon exact (description, date et prix) est refusé avant calcul.

ImmoRadar ne dispose pas d’une source ouverte nationale de ventes comparables détaillées par adresse. Les [statistiques du Registre foncier du Québec sur le marché immobilier](https://www.donneesquebec.ca/recherche/dataset/statistiques-du-registre-foncier-du-quebec-sur-le-marche-immobilier), publiées par le MRNF sous CC BY 4.0, sont agrégées par région et plage de prix : elles constituent un contexte potentiel, mais ne sont pas utilisées par ImmoValue comme comparables individuels. Les transactions détaillées demeurent consultables au Registre foncier selon ses modalités, avec compte et frais possibles.

La provenance et le droit d’utilisation restent sous la responsabilité de l’utilisateur. ImmoRadar ne collecte ni n’enrichit automatiquement les ventes, et ne traite pas les transactions de la Ville de Montréal comme un flux de comparables résidentiels généraux.
