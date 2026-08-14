# Comparateur de deux propriétés

Le comparateur de **Mes propriétés** met en regard exactement deux dossiers sauvegardés par le même compte. Il lit leurs instantanés tels qu’ils ont été enregistrés : il ne recalcule pas ImmoScore, ImmoValue, les scénarios ou les hypothèses financières d’une analyse historique.

## Données comparées

Selon leur disponibilité dans chaque instantané, le comparateur présente le prix analysé, les revenus et dépenses, le paiement hypothécaire, le flux de trésorerie, le rendement sur mise, le taux de capitalisation, la capacité à couvrir la dette (DSCR), ImmoScore, la confiance, la version du moteur et les scénarios sauvegardés. La valeur municipale, lorsqu’elle sera présente dans un instantané, est toujours un **repère fiscal** et jamais une valeur marchande.

Une valeur absente demeure « Non disponible » : elle n’est pas remplacée par zéro et elle ne reçoit aucune interprétation défavorable.

## Lecture déterministe

Pour les indicateurs comparables, le service indique seulement un avantage A, un avantage B, une égalité ou une absence de comparaison. Il fournit au plus trois éléments favorables et trois éléments à vérifier par propriété, puis une conclusion adaptée au profil sauvegardé : « mieux alignée avec vos hypothèses ». Cette lecture n’est ni une recommandation d’achat ni une promesse de rendement. Des versions ImmoEngine différentes sont signalées sans modification des données historiques.

## Accès et limites

Un compte Gratuit conserve un aperçu utile : prix/propriété déclaré, flux mensuel, ImmoScore et confiance lorsqu’ils existent. Le détail financier, les scénarios et la conclusion comparative sont réservés aux comptes Premium techniques et aux administrateurs, au moyen du service central de droits.

Les requêtes SQLite incluent toujours l’identifiant du compte connecté et les deux identifiants demandés. Un administrateur ne reçoit pas automatiquement les analyses d’un autre compte. Aucun nom, adresse, montant ou résultat comparé n’est transmis à la télémétrie.

## Rapport

Le PDF individuel existant reste disponible pour chaque dossier. Un PDF comparatif est volontairement différé : le générateur actuel produit un seul instantané propriétaire à la fois. Une version comparative sera ajoutée seulement lorsqu’elle pourra porter les deux contrôles d’accès et les deux versions sans risque de mélange de données.
