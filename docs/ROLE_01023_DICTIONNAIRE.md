# Rôle officiel 01023 — dictionnaire retenu

Source : rôle MAMH/Données Québec, XML 2.9, territoire 01023 (Les Îles-de-la-Madeleine). Chaque valeur conservée porte la provenance `MAMH rôle 01023 XML 2.9` et sa balise.

| Chemin XML | Nom officiel | Type / unité | Statut |
|---|---|---|---|
| `/RL/VERSION` | Version du répertoire | texte | ingéré comme métadonnée |
| `/RL/RLM01A` | Code géographique | texte | ingéré comme métadonnée |
| `/RL/RLM02A` | Millésime du rôle | année | ingéré |
| `/RL/RLUEx/RL0101/RL0101x/RL0101Ax` | Numéro inférieur | texte | ingéré si présent |
| `.../RL0101Gx` | Nom de voie | texte | ingéré si présent |
| `.../RL0101Ix` | Appartement ou local | texte | ingéré si présent |
| `.../RL0104A` à `RL0104H` | Numéro matricule | texte | ingéré, identifiant de recherche |
| `.../RL0105A` | Utilisation prédominante | code CUBF | ingéré |
| `.../RL0302A` | Superficie du terrain | m² | ingéré |
| `.../RL0306A` | Nombre d'étages | nombre | ingéré |
| `.../RL0307A` | Année de construction | année | ingéré |
| `.../RL0401A` | Date de référence au marché | date | ingéré |
| `.../RL0402A` | Valeur du terrain | CAD au rôle | ingéré |
| `.../RL0403A` | Valeur du bâtiment | CAD au rôle | ingéré |
| `.../RL0404A` | Valeur de l'immeuble | CAD au rôle | ingéré |

Sont exclus par liste blanche : propriétaire, adresse postale de propriétaire, courriel, téléphone, cadastral/lot, toute donnée caviardée ou balise non documentée. Aucune donnée supprimée n'est reconstruite ou inférée.
