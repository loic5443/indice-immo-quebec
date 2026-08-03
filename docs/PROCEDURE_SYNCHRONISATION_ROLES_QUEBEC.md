# Synchronisation administrative des rôles du Québec

Dans **Administration > Données foncières du Québec**, l’administrateur confirme d’abord l’actualisation de l’index MAMH. Il recherche ensuite une municipalité ou son code, confirme le téléchargement, puis lance l’import d’un seul territoire.

L’index est remplacé dans une transaction; en cas d’échec, le dernier index valide reste disponible. Chaque XML est téléchargé dans un fichier temporaire, limité à 20 Mo et 45 secondes, validé (territoire, XML, version 2.9 et empreinte SHA-256), importé en flux et supprimé après l’opération. L’ancienne version locale reste active si l’import échoue.

Les territoires peuvent être désactivés sans suppression. Le retrait du cache exige une seconde confirmation et ne touche jamais aux analyses des utilisateurs. Aucune synchronisation massive ni automatique n’est effectuée. Les XML, caches et bases locales sont exclus de Git.

Seuls les champs de la liste blanche documentée sont conservés. L’adresse utilisateur n’est jamais envoyée par télémétrie.
