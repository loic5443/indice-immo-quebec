# Ajouter une source

1. Valider le propriétaire, l'URL officielle, la licence, le territoire, la fréquence et les limites d'usage.
2. Ajouter la fiche complète au registre versionné `source_registry.json` avec le statut `deferred`.
3. Écrire un fournisseur typé, ses tests de schéma et ses règles de qualité; aucun secret ne doit être requis ou inscrit dans le dépôt.
4. Ajouter une migration seulement si la structure de stockage évolue; conserver les observations historiques.
5. Tester succès, panne, changement de schéma, données invalides, cache et quarantaine localement.
6. Passer au statut `integrated` seulement après revue et exposer source, date, qualité et lien dans l'interface.
