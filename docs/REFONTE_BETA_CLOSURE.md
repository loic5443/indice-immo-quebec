# Clôture de la refonte — ImmoRadar 0.7.0 bêta privée

| Statut | Éléments |
|---|---|
| Disponible | analyse financière, ImmoEngine déterministe, scénarios, comptes locaux, historique, export/suppression, administration bêta, suivi local de changements vérifiables, comparateur de dossiers et PDF avec accès Premium bêta, avis générique par courriel pour une nouvelle alerte vérifiable (Premium, consentement distinct et livraison locale configurée) |
| Expérimental | ImmoValue, import de comparables déclarés par l’utilisateur, recherche d’adresse publique consentie, synchronisation contrôlée d’un rôle municipal officiel lorsque le territoire est publié et compatible |
| À venir | données enrichies et couverture municipale élargie |
| Différé | paiements, Stripe, IA générative et estimation de valeur marchande autonome |

Les rôles d’évaluation MAMH/Données Québec restent séparés d’ImmoValue et des prix de vente. Une valeur au rôle est un repère fiscal et peut différer de la valeur marchande selon l’année du rôle, le secteur et l’évolution du marché. Le Profil financier des municipalités locales est intégré sous CC-BY 4.0, année 2025 : population, valeur uniformisée résidentielle moyenne, richesse foncière uniformisée et richesse par unité. Les pages Québec.ca de statistiques et de proportions médianes restent différées tant que leur licence de réutilisation commerciale explicite n’est pas confirmée.

La version est destinée à une bêta privée : aucun paiement n’est actif. Les données locales, PDF temporaires, XML, caches et bases SQLite sont ignorés par Git. Les événements analytiques exigent un consentement et sont filtrés par liste blanche.
