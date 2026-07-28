# ImmoRadar — UI/UX Design System
## Expérience, contenu et composants

**Version :** 1.0  
**Direction :** confiance, clarté, sobriété immobilière  
**Promesse UX :** comprendre l’essentiel en un regard; approfondir sans perdre le contexte.

## 1. Principes

1. Une question principale par écran.
2. Le verdict ne précède jamais la confiance et les limites.
3. Le vert signifie favorable, pas « garanti ».
4. Les données manquantes sont visibles et actionnables.
5. Mobile d’abord pour la saisie; bureau optimisé pour la comparaison.
6. Le jargon est expliqué dans le contexte.
7. Une donnée simulée n’utilise jamais le même traitement qu’une donnée observée.

## 2. Identité visuelle

### Palette

| Rôle | Couleur | Usage |
|---|---|---|
| Marine | #0B2545 | navigation, titres, confiance |
| Bleu | #246BCE | actions principales, liens |
| Sarcelle | #12A594 | résultats favorables |
| Or | #C99A2E | accent Premium, parcimonieux |
| Encre | #1E293B | texte |
| Gris | #64748B | métadonnées |
| Fond | #F6F8FB | sections secondaires |
| Risque | #A33A3A | alertes importantes |

Toutes les combinaisons doivent atteindre le contraste WCAG AA. La couleur n’est jamais le seul signal.

### Typographie

- Interface : Inter ou police système moderne.
- Titres : 40/48 bureau, 32/38 mobile.
- H2 : 28/36; H3 : 20/28.
- Corps : 16/24.
- Métadonnées : minimum 14/20.
- Chiffres clés : chiffres tabulaires si disponibles.

## 3. Grille et espacement

Échelle : 4, 8, 12, 16, 24, 32, 48, 64.  
Largeur de contenu : 1200 px maximum.  
Texte narratif : 720 px maximum.  
Rayon cartes : 16 px.  
Ombres légères uniquement; aucune carte dans une carte sans nécessité.

## 4. Navigation

### Bureau

Accueil, Analyser, Marchés, Mes analyses, Premium; compte à droite.

### Mobile

Navigation principale compacte; actions secondaires dans le menu. Le bouton « Analyser » reste prioritaire.

### États

- visiteur;
- connecté gratuit;
- connecté Premium;
- quota utilisé;
- données insuffisantes;
- erreur de fournisseur;
- maintenance.

## 5. Accueil

### Hero

Titre recommandé : **La décision immobilière commence ici.**  
Sous-titre : **Estimez, comparez et comprenez une propriété avec des résultats expliqués et adaptés à votre projet.**  
CTA : **Analyser une propriété**  
Secondaire : **Voir comment ça fonctionne**

L’image immobilière sert de contexte, pas de décoration dominante. Un dégradé garantit le contraste.

### Preuves

Avant données réelles validées, ne pas afficher de fausses statistiques de performance ou de faux témoignages. Préférer :

- « Une estimation gratuite par mois »;
- « Chaque résultat est expliqué »;
- « Les sources et dates sont visibles ».

## 6. Onboarding

### Étape 1 — Objectif

Premier achat, investissement locatif, connaître la valeur, accompagner un client.

### Étape 2 — Préférences

Horizon, tolérance au risque, ville, type de propriété. Les champs optionnels expliquent leur utilité.

### Étape 3 — Première analyse

Une barre de progression affiche les informations minimales, recommandées et facultatives.

## 7. Formulaire d’analyse

Regrouper en sections :

1. propriété;
2. prix et financement;
3. revenus;
4. dépenses;
5. état et travaux;
6. contexte.

Utiliser validation en ligne, unités explicites, exemples et valeurs par défaut marquées « exemple ». Ne pas préremplir des hypothèses comme si elles provenaient de la propriété.

## 8. Écran de résultat

### Niveau 1 — Résumé

- valeur/fourchette ou « estimation indisponible »;
- confiance;
- score adapté au profil;
- verdict nuancé;
- trois facteurs;
- CTA « voir pourquoi ».

### Niveau 2 — ImmoDNA

Six cartes ou radar accessible avec équivalent textuel. Chaque axe indique score, confiance et données manquantes.

### Niveau 3 — Détails

Finances, marché, risques, comparables, sources, scénarios.

### Modèle de contenu

**À approfondir — confiance modérée**  
« Les finances sont favorables dans votre scénario, mais les comparables récents sont peu nombreux. Vérifiez l’état du bâtiment et testez un taux supérieur de 1 %. »

## 9. Composants

### DataBadge

Types : observée, déclarée, dérivée, simulée, indisponible.  
Affiche source/date au clic ou au survol; accessible au clavier.

### ConfidenceMeter

Texte prioritaire : élevée, modérée, faible. Le nombre est secondaire. L’infobulle explique la signification.

### ScoreCard

Contient libellé, score, changement de scénario, confiance, facteur principal. Aucun score sans confiance.

### FactorRow

Icône directionnelle, impact, titre, explication, source. Les impacts en points doivent réconcilier le score.

### RiskAlert

Niveaux : information, à vérifier, important, bloquant. Chaque alerte propose une action.

### EmptyState

Explique pourquoi il n’y a pas de contenu et offre une prochaine action.

## 10. Premium et quota

Le quota est présenté avant l’analyse : **1 estimation gratuite disponible ce mois-ci**.  
Après consommation : date de renouvellement, bénéfices Premium, aucune culpabilisation.  
Une erreur ou analyse incomplète ne consomme pas le quota.

La page Premium compare des résultats concrets, pas une liste vague :

- Gratuit : une estimation/mois, analyse de base, une sauvegarde.
- Premium : analyses supplémentaires, scénarios, rapport, historique, comparaison et alertes.

## 11. Accessibilité

- navigation clavier complète;
- focus visible;
- labels persistants;
- erreurs associées aux champs;
- graphiques avec résumé textuel;
- zoom 200 % sans perte;
- cibles tactiles de 44 px;
- préférence de mouvement réduit;
- langue française correcte et encodage UTF-8.

Le dépôt actuel présente du texte mal encodé dans plusieurs fichiers; la correction est un prérequis de qualité.

## 12. Contenu et ton

### Voix

Calme, précise, directe, sans exagération.

### Dire

- « Selon les données disponibles… »
- « Cette estimation comporte une incertitude… »
- « Voici les facteurs qui influencent le résultat. »

### Éviter

- « Achat garanti »
- « Meilleure occasion »
- « Notre IA sait »
- « Valeur réelle » sans qualification
- « J’achèterais »

## 13. Messages essentiels

### Données insuffisantes

« Nous ne disposons pas d’assez de comparables fiables pour publier une estimation. Vous pouvez tout de même analyser le financement et ajouter des renseignements. »

### Fournisseur indisponible

« Une source est temporairement indisponible. Nous avons conservé les données datées du [date]. »

### Limite

« ImmoRadar est un outil d’aide à la décision. Il ne remplace pas une évaluation, une inspection ni un avis professionnel. »

## 14. Parcours de test

- nouveau visiteur comprend la promesse en 5 secondes;
- il identifie quelle donnée est simulée;
- il complète une analyse sans aide;
- il explique la différence entre score et confiance;
- il retrouve une analyse;
- il comprend pourquoi le quota a été débité;
- il peut supprimer son compte.

## 15. Critères de finition

- aucun texte coupé ou mal encodé;
- aucun bouton sans résultat clair;
- aucun état vide sans prochaine action;
- aucun graphique sans alternative textuelle;
- cohérence mobile/bureau;
- captures de référence pour chaque page et état critique.
