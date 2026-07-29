# ImmoRadar — Product Bible
## Vision produit, exigences et feuille de route

**Version :** 1.0  
**Statut :** Référence de travail approuvable  
**Portée :** Québec d’abord; expansion seulement après validation  
**Promesse centrale :** Aider une personne à comprendre une propriété et à prendre une meilleure décision immobilière en moins de 60 secondes.

> ImmoRadar ne vend pas une certitude. Il transforme des données, des hypothèses et des limites connues en une décision plus claire, expliquée et personnalisée.

## 1. Résumé exécutif

ImmoRadar est un copilote immobilier québécois. Le produit cible le moment qui suit la découverte d’une propriété et précède une offre, une décision de financement ou une analyse approfondie. Il rassemble les renseignements disponibles, calcule la viabilité financière, estime une valeur lorsque les données le permettent, mesure l’incertitude et explique les facteurs favorables ou défavorables.

Le produit actuel est un MVP Streamlit. Il comprend un accueil, une analyse locative, des marchés d’exemple, une présentation Premium, des comptes locaux SQLite, la sauvegarde des analyses, les favoris et des tests unitaires. À ce jour, seul le taux directeur est récupéré d’une source externe; les indicateurs de ville sont simulés. ImmoRadar ne doit donc pas être commercialisé comme estimateur automatisé fiable avant l’intégration et la validation de données réelles.

La stratégie produit est progressive :

- rendre la boucle « compte → analyse → sauvegarde → consultation » solide;
- ajouter un moteur décisionnel explicable fonctionnant d’abord avec les données saisies;
- connecter des sources réelles avec provenance, date et droits d’utilisation;
- lancer une bêta contrôlée;
- activer le paiement seulement après validation de la valeur, de la sécurité et des obligations juridiques.

## 2. Mission, vision et positionnement

### 2.1 Mission

Aider chaque Québécois à prendre une meilleure décision immobilière grâce à une analyse rapide, transparente, contextualisée et compréhensible.

### 2.2 Vision

Devenir le réflexe québécois avant une décision immobilière importante : « Avant d’acheter, je passe la propriété dans ImmoRadar. »

### 2.3 Positionnement

ImmoRadar se situe entre les plateformes d’annonces, les fournisseurs de données, les calculatrices financières et les professionnels. Il ne remplace ni un évaluateur agréé, ni un inspecteur, ni un courtier, ni un prêteur. Il aide l’utilisateur à préparer de meilleures questions et à prioriser les vérifications.

### 2.4 Proposition de valeur

- Une seule expérience pour comprendre valeur, rendement, risques et scénario de financement.
- Une conclusion adaptée au profil de l’utilisateur.
- Une explication de chaque score et de chaque limite.
- Une distinction visible entre donnée observée, donnée déclarée, donnée dérivée et simulation.
- Un indice de confiance séparé du score d’opportunité.

## 3. Principes non négociables

1. **Explicabilité.** Aucun score global sans décomposition.
2. **Provenance.** Toute donnée externe affiche source, date et portée géographique.
3. **Incertitude.** Une fourchette remplace une précision artificielle.
4. **Séparation.** Les données réelles, déclarées, dérivées et simulées ne sont jamais mélangées sans étiquette.
5. **Sécurité.** Le minimum de renseignements personnels est recueilli; les accès sont isolés par utilisateur.
6. **Utilité.** Chaque écran répond à une question de décision.
7. **Validation.** Les résultats du moteur sont évalués sur des ventes réelles avant toute promesse de précision.
8. **Réversibilité.** Une nouvelle source ou version du moteur peut être retirée sans casser les analyses historiques.

## 4. Utilisateurs prioritaires

### 4.1 Premier acheteur

**Question principale :** Puis-je acheter cette propriété sans surpayer ni fragiliser mon budget?  
**Critères dominants :** mensualité, marge de sécurité, liquidité, état, proximité, stabilité.  
**Risque UX :** interpréter un score élevé comme une recommandation financière.

### 4.2 Investisseur locatif

**Question principale :** Le rendement compense-t-il les risques et le capital immobilisé?  
**Critères dominants :** RNE, capitalisation, DSCR, cash-flow, vacance, entretien, scénario de taux.

### 4.3 Propriétaire

**Question principale :** Comment la valeur probable de mon bien évolue-t-elle et quels facteurs l’influencent?  
**Critères dominants :** comparables, fourchette, confiance, historique, changements du secteur.

### 4.4 Courtier ou analyste

**Question principale :** Comment préparer rapidement une discussion structurée avec un client?  
**Critères dominants :** provenance, comparables, rapport exportable, traçabilité, notes.

### 4.5 Non-cibles du lancement

Les banques, assureurs, grands portefeuilles et API B2B ne sont pas des cibles du MVP. Ils exigent disponibilité, auditabilité, contrats, sécurité et qualité de données supérieures.

## 5. Parcours de référence

### 5.1 Première estimation

1. L’utilisateur crée un compte ou se connecte.
2. Il choisit son profil et son objectif.
3. Il saisit une adresse ou décrit la propriété.
4. ImmoRadar indique immédiatement quelles données sont disponibles.
5. L’utilisateur complète les champs manquants.
6. Le moteur produit valeur/fourchette, confiance, score, facteurs, risques et scénarios.
7. L’utilisateur sauvegarde l’analyse ou télécharge un rapport s’il y a droit.
8. Le quota mensuel est mis à jour.

### 5.2 Critères d’acceptation

- Une analyse ne peut pas démarrer avec des entrées incohérentes.
- Un score n’est pas affiché si les données minimales du sous-score sont absentes.
- La confiance n’est jamais assimilée à une probabilité que le prix exact soit vrai.
- Une recommandation contient au moins deux raisons, une limite et une prochaine action.
- Une analyse sauvegardée conserve la version du moteur et un instantané des données.

## 6. Architecture fonctionnelle

### 6.1 ImmoValue

Produit une valeur centrale, une fourchette et un niveau de confiance. La V1 ne doit être activée que lorsque des comparables licenciés ou légalement utilisables sont disponibles.

### 6.2 ImmoScore

Mesure l’adéquation entre une propriété et un profil. Il ne mesure pas la valeur marchande et ne constitue pas une cote de crédit.

### 6.3 ImmoDNA

Présente six dimensions : valeur, finances, marché, bâtiment, risques et liquidité. Chaque dimension est accompagnée de facteurs, de données manquantes et d’une confiance locale.

### 6.4 ImmoCopilot

Transforme les résultats déterministes en résumé lisible. L’IA générative peut reformuler, mais elle ne calcule pas les valeurs et ne crée pas de faits.

### 6.5 « Et si? »

Permet de modifier taux, mise de fonds, loyer, vacance, entretien et horizon. Chaque scénario doit être conservé séparément de l’analyse de base.

## 7. Offre et droits

### 7.1 Gratuit

- Une estimation complète par mois civil.
- Calculateur financier de base.
- Une analyse sauvegardée active.
- Score et explications de base.
- Données de marché publiques avec portée limitée.

### 7.2 Premium

- Estimations supplémentaires selon une politique d’usage équitable.
- Historique illimité.
- Comparaison de propriétés.
- Simulations avancées.
- Rapport PDF professionnel.
- Alertes et suivi.
- Explications détaillées et données enrichies.

### 7.3 Pro — après validation

- Espaces d’équipe.
- Portefeuilles multiples.
- Exports de données.
- Rapports personnalisés.
- API contractuelle.

### 7.4 Règle du quota

Une estimation est débitée seulement lorsqu’un résultat complet est produit. Une relance identique dans une fenêtre courte, une erreur technique ou une analyse insuffisante ne doit pas consommer le quota. L’administrateur doit pouvoir corriger un quota.

## 8. Exigences par fonctionnalité

### 8.1 Compte

- Courriel vérifié avant fonctions sensibles.
- Réinitialisation du mot de passe.
- Politique de session, déconnexion globale et journal d’événements.
- Suppression et export des données du compte.

### 8.2 Analyse financière

- Inclure vacance, entretien, gestion, services, CAPEX, frais d’acquisition et fiscalité comme hypothèses explicites.
- Conserver la convention hypothécaire canadienne.
- Afficher les formules simplifiées et les exclusions.
- Autoriser les scénarios sans exiger de valeur marchande.

### 8.3 Marchés

- Supprimer les chiffres simulés de la production publique.
- Afficher territoire, période, unité, source, date d’extraction et date de révision.
- Empêcher la comparaison de séries incompatibles.

### 8.4 Rapport

- Page de résumé; hypothèses; résultats; facteurs; risques; sources; limites; version du moteur.
- Aucune formulation laissant croire à une évaluation professionnelle officielle.

## 9. État actuel et écarts

| Domaine | État actuel | Écart avant bêta |
|---|---|---|
| Interface | Streamlit, navigation et CSS | Corriger les textes encodés et tester l’accessibilité |
| Comptes | SQLite local, PBKDF2 | Vérification courriel, récupération, sessions serveur |
| Calculs | Hypothèque, cash-flow, CoC, cap rate, DSCR | Ajouter vacance, CAPEX, frais d’acquisition et scénarios |
| Marchés | Six villes simulées | Remplacer par séries réelles et sourcées |
| Estimation | Non implémentée | Données comparables, modèle, validation et gouvernance |
| Premium | Présentation seulement | Droits, quotas, Stripe, facturation et support |
| Tests | Calculs et base locale | E2E, sécurité, migrations, performance, confidentialité |

## 10. Feuille de route

### Phase 0 — Stabilisation

- Corriger tous les problèmes d’encodage.
- Ajouter migrations de base de données et configuration d’environnement.
- Éliminer les secrets locaux du flux de développement.
- Créer la télémétrie respectueuse de la vie privée.

### Phase 1 — Moteur déterministe

- Profils utilisateurs.
- Score financier explicable.
- ImmoDNA fondé sur entrées et données disponibles.
- Scénarios « Et si? ».
- Rapport v1.

### Phase 2 — Données réelles et estimation expérimentale

- Catalogue de sources et contrats d’usage.
- Résolution d’adresse et géocodage.
- Comparables et modèle de référence.
- Backtesting, intervalles et monitoring.
- Étiquette « bêta » et régions limitées.

### Phase 3 — Bêta privée

- 50 à 100 participants recrutés dans les profils cibles.
- Mesure de compréhension, confiance, erreurs et intention de payer.
- Entrevues et journal de décisions.

### Phase 4 — Premium

- Quotas.
- Stripe Checkout et portail client.
- Webhooks idempotents.
- Conditions, confidentialité, remboursement et taxes.
- Support et procédure d’incident.

## 11. Mesures de succès

### Produit

- Temps médian jusqu’au premier résultat : moins de 5 minutes pour une analyse manuelle; objectif ultérieur de 60 secondes avec données.
- Pourcentage d’utilisateurs pouvant expliquer le score : au moins 80 % en test.
- Taux de sauvegarde après analyse.
- Taux de retour à 30 jours.

### Moteur

- Erreur absolue médiane et MAPE par région/type/prix.
- Couverture réelle des intervalles de confiance.
- Taux d’analyses refusées pour données insuffisantes.
- Dérive des variables et performance par version.

### Business

- Activation : compte + première analyse complète.
- Conversion après consommation de l’estimation gratuite.
- Revenu récurrent mensuel, churn et coût de soutien.

## 12. Décisions et garde-fous

- Ne pas revendiquer « l’estimation la plus précise » sans étude indépendante.
- Ne pas automatiser une recommandation catégorique d’achat.
- Ne pas collecter les actions des utilisateurs pour modifier silencieusement les scores.
- Ne pas lancer un radar d’annonces sans droit d’accès et de réutilisation des données.
- Ne pas activer Stripe avant la gestion complète des droits et webhooks.

## 13. Définition de « prêt pour la bêta »

- Zéro donnée simulée non signalée.
- Tous les résultats ont provenance et date.
- Les comptes sont récupérables et supprimables.
- Les analyses sont isolées, versionnées et exportables.
- Les tests critiques passent dans un environnement propre.
- Une évaluation de sécurité et de confidentialité est réalisée.
- Les limites du produit sont visibles avant et après l’analyse.

## Mise à jour Sprint 5

ImmoValue est une estimation expérimentale distincte d'ImmoScore. Elle requiert au moins trois ventes comparables déclarées par l'utilisateur, affiche une fourchette et ne constitue jamais une évaluation officielle ou une recommandation d'offre.
