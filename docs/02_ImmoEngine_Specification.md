# ImmoRadar — ImmoEngine Specification
## Règles métier, scores, confiance et validation

**Version :** 1.0  
**Principe :** calcul déterministe d’abord; explication générative ensuite  
**Statut :** Spécification cible — aucun résultat de valeur ne doit être présenté comme opérationnel avant validation.

## 1. Objectif et frontières

ImmoEngine reçoit un instantané de propriété, un contexte de marché, un profil utilisateur et des hypothèses financières. Il produit des résultats structurés, versionnés et explicables. Il ne signe pas une évaluation, ne confirme pas l’état physique d’un bâtiment et ne remplace pas une analyse professionnelle.

## 2. Contrat d’entrée

### 2.1 PropertySnapshot

- identifiant interne;
- adresse normalisée, coordonnées et précision du géocodage;
- type et sous-type;
- superficie habitable, terrain, année, unités, chambres, salles de bain;
- état et rénovations avec provenance;
- prix demandé et date;
- évaluation municipale et année de référence;
- taxes et charges;
- indicateurs de qualité et valeurs manquantes.

### 2.2 MarketSnapshot

- zone géographique et méthode de découpage;
- période de référence;
- ventes comparables admissibles;
- métriques de prix, liquidité, inventaire et loyers;
- variables macroéconomiques;
- version et licences de chaque source.

### 2.3 UserProfile

- profil : premier acheteur, investisseur, propriétaire, courtier;
- horizon;
- tolérance au risque;
- objectif de rendement;
- contraintes de paiement;
- hypothèses modifiables.

## 3. Contrat de sortie

Chaque sortie contient :

- `analysis_id`, `engine_version`, `created_at`;
- `data_as_of` et empreinte des sources;
- résultats;
- facteurs positifs et négatifs;
- valeurs manquantes;
- confiance par module;
- avertissements;
- statut : `complete`, `partial`, `insufficient_data`, `failed`;
- trace de calcul exploitable pour audit.

## 4. ImmoValue v1

### 4.1 Conditions d’activation

Le module est activé seulement si :

- le type de propriété est couvert;
- l’adresse est résolue avec confiance;
- au moins trois comparables admissibles existent, dont idéalement deux récents;
- les caractéristiques essentielles sont connues;
- aucune anomalie bloquante n’est détectée.

Sinon, ImmoRadar affiche une analyse financière et contextuelle sans estimation de valeur.

### 4.2 Sélection des comparables

Les comparables sont filtrés par :

- même catégorie de propriété;
- transaction de gré à gré admissible;
- fenêtre temporelle configurable;
- rayon adapté à la densité;
- superficie et année dans une plage acceptable;
- exclusion des ventes liées, saisies, terrains seuls et cas atypiques lorsque repérables.

### 4.3 Similarité

Score de similarité `S_i` entre 0 et 1 :

`S_i = 0,30 T + 0,20 A + 0,15 Z + 0,10 Y + 0,10 L + 0,10 C + 0,05 Q`

où T = type, A = superficie, Z = zone, Y = année/état, L = lot, C = configuration, Q = qualité des données. Les pondérations sont initiales et doivent être calibrées.

### 4.4 Ajustement temporel

Le prix de vente d’un comparable est ramené à la date d’analyse avec un indice local :

`P_t = P_vente × (Indice_analyse / Indice_vente)`

Si aucun indice local fiable n’existe, l’ajustement temporel est omis et la confiance diminue.

### 4.5 Valeur par comparable

Deux approches sont combinées :

- prix ajusté direct;
- prix unitaire ajusté × superficie du sujet.

La combinaison dépend de la qualité des superficies. Les valeurs extrêmes sont réduites par winsorisation ou exclues avec justification.

### 4.6 Agrégation

`Valeur = médiane pondérée(V_i, poids = S_i × récence_i × qualité_i)`

La médiane pondérée est préférée à une moyenne simple pour réduire l’effet des anomalies. Une régression hédonique pourra devenir un modèle secondaire après disponibilité d’un jeu de validation suffisant.

### 4.7 Fourchette

La fourchette initiale provient de la dispersion pondérée et d’un plancher d’incertitude :

`marge = max(marge_minimale, k × MAD_pondérée, erreur_historique_segment)`

La valeur présentée est arrondie à un niveau cohérent avec la confiance; jamais au dollar près.

## 5. Confidence Engine

### 5.1 Définition

La confiance mesure la qualité de l’information et la performance historique attendue du modèle pour ce segment. Elle n’est pas la probabilité que le prix final tombe exactement sur la valeur centrale.

### 5.2 Sous-scores

| Dimension | Poids initial |
|---|---:|
| Quantité de comparables | 20 % |
| Similarité | 25 % |
| Récence | 15 % |
| Dispersion | 15 % |
| Complétude du sujet | 10 % |
| Qualité/provenance | 10 % |
| Performance historique du segment | 5 % |

Un plafond est appliqué si une dimension critique est faible. Par exemple, moins de trois comparables plafonne la confiance à 49.

### 5.3 Libellés

- 80–100 : élevée;
- 60–79 : modérée;
- 40–59 : faible;
- moins de 40 : estimation non publiée.

Ces seuils doivent être recalibrés pour obtenir une couverture empirique honnête.

## 6. ImmoScore

### 6.1 Règle fondamentale

Le score global mesure l’adéquation au profil et au scénario. Une même propriété peut recevoir un score différent selon l’utilisateur. La valeur marchande reste identique pour un même instantané.

### 6.2 Dimensions

| Dimension | Premier acheteur | Investisseur |
|---|---:|---:|
| Prix vs valeur | 20 | 15 |
| Abordabilité / finances | 25 | 25 |
| Bâtiment | 15 | 10 |
| Quartier | 15 | 10 |
| Liquidité | 10 | 10 |
| Croissance | 5 | 10 |
| Risques | 10 | 10 |
| Rentabilité locative | 0 | 10 |

Les poids sont normalisés sur les dimensions disponibles. Si plus de 25 % du poids est indisponible, le score global devient « incomplet ».

### 6.3 Normalisation

Chaque métrique est transformée sur 0–100 par seuils documentés ou percentiles du segment. Les seuils sont versionnés. Les valeurs extrêmes sont plafonnées. Aucune variable individuelle ne peut ajouter ou retrancher plus de 20 points au score global.

### 6.4 Score financier investisseur

Exemple de sous-score :

- DSCR : 30 %;
- cash-on-cash : 25 %;
- taux de capitalisation relatif : 20 %;
- cash-flow et marge de sécurité : 15 %;
- sensibilité aux taux/vacance : 10 %.

Un DSCR inférieur à 1 n’entraîne pas automatiquement « mauvais achat », mais déclenche un risque majeur et réduit le plafond du score financier.

### 6.5 Explication

Le moteur retourne les cinq facteurs les plus influents avec :

- direction;
- impact en points;
- donnée utilisée;
- référence au sous-score;
- action possible.

La somme des contributions doit réconcilier le score à un écart d’arrondi près.

## 7. ImmoDNA

ImmoDNA est la vue multi-dimensionnelle, pas un nouvel algorithme. Les six axes sont :

1. valeur relative;
2. finances;
3. marché/croissance;
4. liquidité;
5. bâtiment;
6. risques.

Chaque axe affiche score, confiance, facteurs, données manquantes et tendance lorsque disponible.

## 8. Opportunity Engine

### 8.1 Objectif

Classer des propriétés admissibles selon leur écart à la valeur, leur qualité financière, leur liquidité et leurs risques. Le terme « sous-évaluée » n’est utilisé que si la confiance et la qualité de données dépassent un seuil.

### 8.2 Score d’opportunité

`O = 0,35 écart_valeur + 0,25 finances + 0,15 croissance + 0,15 liquidité + 0,10 risque_inversé`

Un ajustement de confiance réduit le score :

`O_final = 50 + (O - 50) × confiance/100`

Ainsi, une donnée incertaine rapproche le résultat du neutre au lieu de créer une fausse conviction.

### 8.3 Percentile

Le percentile compare uniquement des propriétés du même segment, dans une fenêtre temporelle et géographique définie. Il faut afficher la taille de l’échantillon.

## 9. Prix intelligent

Le « prix intelligent » est un intervalle de discussion, pas une prédiction d’acceptation. La V1 peut proposer :

- borne prudente = percentile inférieur de la valeur;
- cible = valeur centrale moins coût des risques quantifiables;
- plafond = limite selon profil/financement.

Toute « probabilité d’acceptation » est interdite avant disponibilité de données d’offres et d’acceptations légalement utilisables.

## 10. ImmoCopilot

### 10.1 Entrée autorisée

Uniquement les objets structurés produits par le moteur et les textes de source approuvés.

### 10.2 Sortie

- verdict nuancé : favorable, à approfondir, prudence, données insuffisantes;
- deux à cinq raisons;
- risques prioritaires;
- questions à poser;
- scénarios suggérés;
- limites et date.

### 10.3 Garde-fous

- pas de conseil juridique, fiscal ou financier personnalisé;
- pas de fait non présent dans le contexte;
- pas de recommandation catégorique « achetez »;
- pas de discrimination fondée sur des caractéristiques protégées;
- journalisation du prompt système et de la version.

## 11. Calculs financiers

### 11.1 Paiement hypothécaire

La convention canadienne convertit le taux nominal composé semestriellement en taux mensuel équivalent :

`r_m = (1 + j/2)^(2/12) - 1`

`M = P × r_m(1+r_m)^n / ((1+r_m)^n - 1)`

### 11.2 Revenu net d’exploitation

`RNE = revenus effectifs - dépenses d’exploitation`

Le service de la dette et l’impôt ne font pas partie du RNE.

### 11.3 Vacance

`revenus_effectifs = loyers_bruts × (1 - taux_vacance) + autres_revenus`

### 11.4 Ratios

- Capitalisation = RNE / prix.
- DSCR = RNE / service annuel de la dette.
- Cash-on-cash = flux annuel avant impôt / capital réellement investi.
- Capital investi inclut mise de fonds, frais d’acquisition et travaux initiaux.

La mise en œuvre actuelle n’inclut pas encore tous ces postes; la spécification cible doit remplacer la formule simplifiée.

## 12. Validation et backtesting

### 12.1 Jeu de référence

Séparer entraînement, calibration et test par temps et géographie. Éviter qu’une transaction ou une propriété apparentée se retrouve dans plusieurs ensembles.

### 12.2 Métriques

- MAE en dollars;
- erreur médiane absolue en pourcentage;
- biais moyen;
- couverture des intervalles;
- performance par type, région, prix et confiance;
- taux de refus.

### 12.3 Critère de déploiement

Une nouvelle version ne remplace l’ancienne que si :

- elle améliore ou maintient les métriques globales;
- elle ne dégrade pas substantiellement un segment important;
- ses intervalles sont calibrés;
- ses changements sont documentés;
- un retour arrière est possible.

## 13. Versionnement et audit

Format recommandé : `major.minor.patch`.

- major : changement de sens ou de modèle;
- minor : nouvelle source ou calibration;
- patch : correction sans changement attendu significatif.

Chaque analyse conserve les paramètres, sources, versions et facteurs calculés. Les données personnelles inutiles ne sont pas incluses dans la trace.

## 14. Cas limites

- condo sans superficie fiable : valeur non publiée ou confiance plafonnée;
- propriété atypique : refus ou estimation avec avertissement majeur;
- multiplex : approche par revenu distincte de l’unifamilial;
- rénovation déclarée non vérifiée : utilisée comme hypothèse, pas comme fait;
- prix demandé absent : score valeur possible, score négociation absent;
- marché peu liquide : fourchette élargie et percentile d’opportunité suspendu.

## 15. Tests d’acceptation du moteur

- déterminisme à données et version identiques;
- invariants financiers;
- contributions réconciliées;
- refus sur données insuffisantes;
- absence de valeurs NaN/infini;
- bornes 0–100;
- source et date pour chaque donnée;
- tests de non-régression;
- tests de sensibilité : hausse du taux ne doit pas améliorer artificiellement l’abordabilité.
