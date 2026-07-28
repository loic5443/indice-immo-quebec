# ImmoRadar — Data, Legal & Operations Handbook
## Sources, gouvernance, conformité et exploitation

**Version :** 1.0  
**Avertissement :** document opérationnel, non avis juridique. Validation par des professionnels québécois requise avant lancement.

## 1. Catalogue de données prioritaire

### 1.1 Évaluation foncière

Le Gouvernement du Québec publie des statistiques et des renseignements sur les rôles d’évaluation. Le rôle est un outil municipal et sa valeur n’est pas automatiquement la valeur marchande actuelle. Les inventaires provinciaux, sommaires et fichiers prescrits peuvent soutenir des agrégats et la compréhension du schéma. Les modalités de réutilisation et la disponibilité au niveau propriété doivent être vérifiées municipalité par municipalité.

### 1.2 Macroéconomie

La Banque du Canada offre l’API Valet pour les séries financières. Statistique Canada fournit des services de données. Chaque série doit conserver code, unité, fréquence, corrections, date d’extraction et conditions.

### 1.3 Habitation et loyers

La SCHL publie des données et recherches sur les marchés de l’habitation. Vérifier les licences, niveaux géographiques et restrictions pour chaque produit.

### 1.4 Données ouvertes

Données Québec et les portails municipaux peuvent fournir zones inondables, transport, permis, équipements et géomatique. Une fiche de licence est obligatoire avant ingestion.

## 2. Registre des sources

Pour chaque source :

| Champ | Description |
|---|---|
| Identifiant | code interne stable |
| Propriétaire | organisme ou fournisseur |
| URL/contrat | référence officielle |
| Licence | droits et restrictions |
| Géographie | couverture |
| Fréquence | publication et ingestion |
| Méthode | API, fichier, import manuel |
| Qualité | complétude, latence, anomalies |
| Données personnelles | oui/non et justification |
| Responsable | personne interne |
| Retrait | procédure de désactivation |

## 3. Classification des données

- **Observée :** publiée ou mesurée par une source.
- **Déclarée :** saisie par l’utilisateur.
- **Dérivée :** calcul déterministe.
- **Modélisée :** estimation statistique.
- **Simulée :** exemple ou scénario.

Le type est stocké avec chaque fait et affiché dans l’interface.

## 4. Qualité

### Contrôles d’entrée

- schéma et types;
- plages;
- unicité;
- géographie;
- dates;
- unités;
- valeurs manquantes;
- variation anormale;
- réconciliation aux totaux.

### Quarantaine

Une ingestion suspecte n’écrase pas la production. Elle est mise en quarantaine, comparée à la version précédente et approuvée.

### Score de qualité

Complétude, fraîcheur, cohérence, provenance et stabilité. Le score de qualité limite la confiance du moteur.

## 5. Rétention

Définir par catégorie :

- comptes;
- sessions;
- analyses;
- instantanés;
- rapports;
- facturation;
- logs;
- demandes de support;
- sauvegardes.

La suppression logique n’est pas suffisante sans calendrier de purge des sauvegardes et sous-traitants.

## 6. Gouvernance du moteur

### Comité de changement

Même avec une petite équipe, chaque changement significatif possède :

- objectif;
- données;
- hypothèse;
- résultats de test;
- biais/segments;
- décision;
- responsable;
- date;
- rollback.

### Model Card

Pour chaque version :

- usage prévu et interdit;
- population et géographie;
- variables;
- métriques;
- limites;
- performance segmentée;
- date;
- approbation.

## 7. Vie privée

### Inventaire

Courriel, nom, adresse analysée, profil d’investisseur, hypothèses financières, historique, paiement et télémétrie peuvent constituer des renseignements personnels selon le contexte.

### Mesures

- finalité et minimisation;
- consentement compréhensible;
- séparation marketing/service;
- accès et correction;
- portabilité lorsque applicable;
- suppression;
- gestion des incidents;
- contrats de sous-traitance;
- personne responsable de la protection.

Une évaluation des facteurs relatifs à la vie privée est recommandée avant profilage, IA, données sensibles ou transfert hors Québec.

## 8. Conditions d’utilisation — exigences

Les conditions finales doivent traiter :

- admissibilité;
- licence d’utilisation;
- comptes;
- paiement et renouvellement;
- usage acceptable;
- propriété intellectuelle;
- sources tierces;
- absence de garantie;
- limites de responsabilité;
- suspension;
- résiliation;
- droit applicable;
- communications;
- changements.

Ne pas copier des conditions génériques. Faire valider les textes.

## 9. Avis produit

Formulation de base :

> ImmoRadar fournit des estimations et analyses indicatives à partir des données et hypothèses disponibles. Les résultats peuvent être incomplets ou inexacts et ne constituent ni une évaluation officielle, ni un conseil financier, juridique, fiscal ou immobilier. Faites vérifier les renseignements importants par des professionnels qualifiés avant une décision.

L’avis doit être adapté à chaque fonction et ne remplace pas des contrôles de qualité.

## 10. Propriété intellectuelle et marque

- Documenter versions, auteurs et décisions.
- Conserver historique Git.
- Vérifier disponibilité d’ImmoRadar et des sous-marques avant usage commercial.
- Utiliser le symbole ™ seulement avec une stratégie cohérente; ne pas suggérer un enregistrement inexistant.
- Les accords avec employés, pigistes et fournisseurs doivent céder les droits nécessaires.

## 11. Sécurité opérationnelle

### Accès

Moindre privilège, MFA administrateur, revue trimestrielle, départ d’un collaborateur le jour même.

### Vulnérabilités

Mises à jour, analyse de dépendances, divulgation responsable, registre des correctifs.

### Incidents

Détecter, contenir, préserver les preuves, évaluer, notifier si requis, corriger et faire un postmortem.

## 12. Runbooks

### Source indisponible

1. Confirmer l’incident.
2. Geler la dernière version avec date.
3. Désactiver les résultats dépendants si trop anciens.
4. Informer clairement.
5. Ouvrir ticket fournisseur.
6. Réconcilier après retour.

### Estimation aberrante

1. Suspendre le partage.
2. Conserver l’instantané.
3. Vérifier appariement, comparables et unités.
4. Évaluer l’étendue.
5. Corriger ou retirer.
6. Communiquer aux utilisateurs affectés si nécessaire.

### Webhook paiement échoué

1. Vérifier signature et idempotence.
2. Rejouer l’événement.
3. Réconcilier Stripe/droits.
4. Ne pas facturer deux fois.
5. Documenter.

## 13. Support

Catégories : compte, facturation, donnée, estimation, bug, confidentialité.  
Les agents ne modifient jamais un résultat sans trace.  
Une contestation d’estimation devient un signal qualité, pas une promesse de correction individuelle.

## 14. Sources officielles recommandées

- Gouvernement du Québec — évaluation foncière et statistiques.
- Manuel d’évaluation foncière du Québec.
- Institut de la statistique du Québec.
- Banque du Canada — Valet API.
- Statistique Canada — services de données.
- SCHL — données sur les marchés de l’habitation.
- Données Québec et portails municipaux.

Les liens figurent dans la bibliographie du présent volume. L’intégration technique ne doit commencer qu’après lecture des conditions applicables.

## 15. Checklist avant bêta

- registre des sources complet;
- licences validées;
- données simulées retirées ou confinées;
- Model Card;
- politique de confidentialité;
- conditions bêta;
- consentements;
- suppression/export;
- sécurité;
- sauvegarde/restauration;
- incident;
- support;
- mesure de performance.

## 16. Checklist avant paiement

- entité et taxes;
- Stripe et banque;
- prix/renouvellement visibles;
- remboursement;
- factures;
- webhooks;
- annulation;
- service après annulation;
- protection des consommateurs validée;
- tests en production contrôlée.
