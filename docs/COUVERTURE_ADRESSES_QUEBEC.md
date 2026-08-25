# Couverture des adresses du Québec

ImmoRadar utilise deux sources publiques distinctes après le consentement explicite de la personne :

- le service **MRNF — Adresses Québec** pour les suggestions en ligne lorsque le service répond ;
- le **Référentiel québécois des adresses (RQA)** comme index local de secours provincial. La fiche officielle est <https://www.donneesquebec.ca/recherche/dataset/referentiel-quebecois-des-adresses>; elle annonce une couverture québécoise, une mise à jour mensuelle et une licence CC BY 4.0.

## Synchronisation locale contrôlée

La commande `python scripts/sync_rqa_addresses.py --confirm` télécharge l’archive officielle MRNF dans un fichier temporaire. ImmoRadar exige HTTPS et l’hôte officiel, impose une limite de taille, valide la structure CSV et ne conserve que les champs publics utiles aux suggestions : numéro, unité, voie, municipalité, code postal et coordonnées. L’archive temporaire est supprimée même en cas d’échec. Le nouvel index devient actif seulement après l’import complet; l’index précédent reste utilisable jusqu’à ce moment.

La base locale, les caches et les archives sont exclus de Git. Les recherches restent limitées à huit résultats, sont exécutées par SQLite et ne chargent pas l’ensemble des adresses en mémoire.

## Ce que couvre cette fonction

Le RQA améliore la saisie et la normalisation d’une adresse québécoise. Après une sélection consentie, ImmoRadar valide son code géographique public contre l’index officiel MAMH. Si le territoire est compatible et autorisé, il peut synchroniser **uniquement ce territoire** de façon atomique; sinon, le mode manuel reste disponible. Il ne garantit pas qu’un rôle d’évaluation municipal soit disponible pour chaque municipalité. La valeur au rôle ne peut être montrée que lorsqu’un territoire MAMH compatible est officiellement disponible et synchronisé. Elle reste un repère fiscal, distinct d’une valeur marchande ou d’ImmoValue.

## Vie privée

Aucune recherche ni suggestion n’est déclenchée sans consentement. Les requêtes d’adresse, suggestions, coordonnées et résultats ne vont pas dans la télémétrie, les diagnostics ou les journaux techniques. Ils ne sont pas ajoutés automatiquement aux dossiers sauvegardés.
