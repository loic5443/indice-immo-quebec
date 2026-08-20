# Documentation officielle ImmoRadar v1.0

Ce dossier conserve les six volumes Markdown de la documentation ImmoRadar v1.0. Ils constituent les références officielles du projet pour les décisions produit, moteur, architecture, interface, croissance et gouvernance des données.

1. [Product Bible](01_Product_Bible.md) — vision, profils, parcours et garde-fous produit.
2. [ImmoEngine Specification](02_ImmoEngine_Specification.md) — contrats, scores, confiance, explicabilité et validation.
3. [Technical Architecture](03_Technical_Architecture.md) — architecture modulaire, sécurité, migrations et exploitation.
4. [UI/UX Design System](04_UI_UX_Design_System.md) — principes et composants d’interface.
5. [Business and Growth](05_Business_and_Growth.md) — stratégie, offre et progression commerciale.
6. [Data, Legal & Operations](06_Data_Legal_Operations.md) — provenance, qualité, conformité et opérations.

Les documents Word d’origine restent hors du dépôt, à leur emplacement fourni. Toute décision technique durable qui s’écarte de ces volumes doit être documentée dans Git.

## Mise en œuvre Sprint 4

La fondation de données officielles est décrite dans [ADR-008](ADR-008_Sprint4_Official_Data_Foundation.md). Le [registre des sources](source_registry.json), la [matrice de décision](SPRINT4_SOURCE_DECISION_MATRIX.md), le [dictionnaire](DATA_DICTIONARY.md) et les procédures de cycle de vie complètent les volumes officiels sans les remplacer.

Les suggestions consenties du géocodeur officiel sont décrites dans [SOURCE_ADRESSES_QUEBEC_GEOCODEUR.md](SOURCE_ADRESSES_QUEBEC_GEOCODEUR.md). Elles n’enregistrent pas une adresse automatiquement et restent indépendantes d’ImmoValue et d’ImmoScore.

## Sprint 6

- [Rapport de clôture](SPRINT6_COMPLETION_REPORT.md)
- [Guide du parcours d'analyse](GUIDE_PARCOURS_ANALYSE.md)
- [Checklist bêta privée](CHECKLIST_LANCEMENT_BETA.md)

## Clôture de la refonte bêta

Le statut fonctionnel, les sources intégrées, les limites et les contrôles de confidentialité de la version 0.7.0 sont consignés dans le [rapport de clôture](REFONTE_BETA_CLOSURE.md).

## ImmoValue guidé

La [méthodologie ImmoValue](IMMOVALUE_METHODOLOGY.md), la [model card](MODEL_CARD_IMMOVALUE.md) et le [guide CSV](GUIDE_CSV_COMPARABLES.md) décrivent le parcours de comparables déclarés. Les statistiques agrégées ouvertes du Registre foncier sont documentées comme contexte seulement : elles ne remplacent pas des ventes comparables individuelles et ne participent pas au calcul.

## Alertes factuelles

Le centre d’alertes Premium lit uniquement les instantanés déjà sauvegardés : variation d’ImmoValue avec confiance suffisante, variation du rôle municipal et perte de flux dans le test « Taux +1 point ». L’utilisateur active le suivi dossier par dossier dans **Mes propriétés**, ou juste après la première sauvegarde; le choix est local, isolé par compte et ne stocke qu’une empreinte du nom normalisé du dossier. Il ne déclenche aucun appel externe ni courriel pendant la bêta.

## Structure produit actuelle

Le [comparateur de deux propriétés](COMPARATEUR_PROPRIETES.md) est intégré à **Mes propriétés**. Il compare deux instantanés appartenant au même compte, explique ses limites et ne constitue pas une recommandation d’achat.

La navigation principale regroupe **Accueil**, **Analyser**, **Mes propriétés**, **Marché** et **Premium**. Les éléments secondaires (compte, confidentialité, à propos et retours) restent accessibles hors de ce parcours principal. Le Dossier immobilier 360 rassemble les renseignements publics consentis, la valeur municipale distincte d’une valeur marchande, ImmoValue lorsqu’il est calculable, l’analyse financière, ImmoScore et le suivi. Les alertes n’apparaissent comme actives que lorsqu’un changement vérifiable peut réellement être calculé; les autres sont des aperçus Premium verrouillés.
