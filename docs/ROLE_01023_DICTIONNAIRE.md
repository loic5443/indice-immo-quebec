# Rôle officiel 01023 — dictionnaire retenu

Source : rôle MAMH/Données Québec, XML 2.9, territoire 01023 (Les Îles-de-la-Madeleine). Chaque valeur conservée porte la provenance `MAMH rôle 01023 XML 2.9` et sa balise.

| Chemin XML | Nom officiel | Type / unité | Statut |
|---|---|---|---|
| `/RL/VERSION` | Version du répertoire | texte | ingéré comme métadonnée |
| `/RL/RLM01A` | Code géographique | texte | ingéré comme métadonnée |
| `/RL/RLM02A` | Millésime du rôle | année | ingéré |
| `/RL/RLUEx/RL0101/RL0101x/RL0101Ax` | Numéro inférieur | texte | ingéré si présent |
| `.../RL0101Bx` | Fraction ou suffixe du numéro inférieur | texte | ingéré si présent |
| `.../RL0101Cx`, `.../RL0101Dx` | Numéro supérieur et son suffixe | texte | ingéré si présent |
| `.../RL0101Ex` | Générique de voie | code MEFQ | décodé selon la table officielle |
| `.../RL0101Fx` | Liaison du nom de voie | code MEFQ | décodé selon la table officielle |
| `.../RL0101Hx` | Point cardinal | code MEFQ | décodé selon la table officielle |
| `.../RL0101Jx` | Fraction ou suffixe du local | texte | ingéré si présent |
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

## Décodage des adresses, 18 octobre 2026

La version 2 du parseur décode le générique, la liaison (du, de la, de l’, etc.) et la direction suivant le [MEFQ 2026, partie 2, section 2C, 1.3.3](https://cdn-contenu.quebec.ca/cdn-contenu/adm/min/affaires-municipales/publications/evaluation_fonciere/manuel_evaluation_fonciere/2026/MEFQ_partie_2_2026.pdf). Elle conserve séparément le local et les bornes civiques. Une recherche peut correspondre à une borne explicitement publiée ou à la plage complète; aucun numéro intermédiaire n’est déduit. Les caches importés avec l’ancien parseur doivent être rafraîchis avant d’alimenter les suggestions locales. Migration additive 0028; comptes et dossiers conservés.

Le téléchargement public d’un rôle sélectionné est diffusé vers un fichier temporaire, limité à 50 Mo. L’index conserve son plafond de 20 Mo. Cette limite ne promet pas la couverture de toutes les municipalités.
