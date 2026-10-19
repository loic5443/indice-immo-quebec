# Recette adresses, affichage étroit et stockage — 18 octobre 2026

## Résultat vérifié

427 tests automatisés réussis (Python 3.12), dépendances cohérentes et compilation des fichiers modifiés. La version fonctionnelle de la première série de corrections est publiée sur https://immoradar-apercu.onrender.com/ ; les corrections d’affichage de couverture et de filtrage des appartements sont publiées depuis le 19 octobre. La correction d’abréviation ajoutée le 19 octobre est également incluse dans le lot final. Aucun service payant, paiement réel, domaine ou courriel réel activé.

## Adresses et suggestions

28 requêtes réelles auprès du service public MRNF, dont 25 variantes d’adresses, une saisie vide, deux chiffres seuls et une adresse inexistante. Villes couvertes par les essais : Repentigny, Montréal, Valleyfield, Beauharnois, L’Île-Perrot, Longueuil, Boucherville, Varennes, Québec, Lévis, Sherbrooke, Saguenay, Trois-Rivières, Gatineau et Granby. 19 requêtes ont fourni des suggestions dans cette série; les autres ont renvoyé un résultat vide ou une saisie trop courte. Ce chiffre décrit ces requêtes et ne constitue pas un taux de couverture de la province. Une sélection temporairement indisponible de Place Ville-Marie a réussi lors d’un nouvel essai après ajout du repli exact.

Corrections : direction non répétée, numéro civique exact quand une rue suit le numéro, suggestions de locaux distinctes, ancien appartement/code postal non repris après changement d’adresse, apostrophes typographiques acceptées, réponse vide de typeahead reprise par le résolveur officiel. Une clé de suggestion défaillante peut être reprise une fois par son libellé exact (ville, code postal et local compris); aucune correspondance approximative ne remplace la sélection.

Les adresses sans suggestion, les abréviations non reconnues et les municipalités absentes de l’index restent explicitement en mode manuel. Le défaut observé avec « 350 boul de Maisonneuve O Montreal » a été corrigé le 19 octobre : le résolveur développe les types de rue courants et les points cardinaux isolés après un numéro et un type de voie connus, sans modifier le texte saisi. L’essai réel retrouve alors 350 Boulevard De Maisonneuve Ouest, Montréal, H3A 0B4. Un test protège ce comportement et préserve les noms tels que Saint-Ours. Repentigny n’est pas reliée avec certitude dans cet index MAMH au moment du contrôle; cela ne signifie pas que l’adresse n’existe pas. Le répertoire RQA provincial n’est pas chargé dans l’aperçu.

## Rôles officiels

Imports réels et contrôlés : Beauharnois (70022), 6 124 unités / XML 2.9 / 8 323 334 octets; Salaberry-de-Valleyfield (70052), 19 006 unités / XML 2.9 / 25 544 337 octets. Le second dépassait l’ancien plafond de 20 Mo. Les rôles sélectionnés sont désormais diffusés vers un fichier temporaire, avec plafond de 50 Mo, puis remplacés atomiquement après validation. Le plafond de l’index reste de 20 Mo.

Le parseur reconstruit les génériques, liaisons, directions, suffixes, locaux et bornes civiques selon le manuel officiel MEFQ. Tests réels : 170 chemin du Canal et 170/172 chemin de la Beauce, Beauharnois; 61 rue Sainte-Cécile, Valleyfield. Les bornes correspondent aux valeurs explicitement publiées, aucun numéro intermédiaire n’est inféré. Migration additive 0028 et version du parseur enregistrée pour rafraîchir les anciens caches.

Dans le navigateur public, sélectionner 61 rue Sainte-Cécile puis 170 chemin du Canal a rempli les nouvelles villes et codes postaux et affiché respectivement les valeurs fiscales 2026 de 4 855 600 $ et 463 100 $. Ces exemples sont des renseignements fiscaux publics, pas des prix de vente ni des estimations marchandes. Plusieurs unités exigent un choix explicite; un appartement saisi filtre les correspondances, y compris à la reprise d’un brouillon.

## Affichage aux largeurs de téléphone

Contrôle du vrai site HTTPS dans un cadre de largeur fixe : 390 px (accueil, formulaire, suggestions, sélection, Premium, démonstration) et 360 px (accueil et Premium). Largeur du document égale à celle du cadre, sans débordement horizontal. Ville et code postal correctement remplis après sélection sur le format 390 px. Menu latéral et boutons permettent de naviguer. Dans la démonstration, loyers 4 000 → 4 100 $/mois : flux 670 → 767 $/mois et couverture 1,29 → 1,33x.

Il s’agit d’une validation de mise en page dans Chromium à largeur étroite. Aucun iPhone matériel, Safari iOS, clavier tactile, zoom système ni appareil Android n’a été utilisé. Ces comportements restent à vérifier sur appareil réel avant de revendiquer une compatibilité mobile complète. Les routes ?qa_width=360/390/430/768 n’existent que dans l’entrée d’aperçu, avec origine HTTPS Render fixe; elles n’acceptent pas d’URL arbitraire.

## Comptes et conservation

Deux processus distincts créent puis rouvrent la même base SQLite : authentification, rejet du mauvais mot de passe, profil/onboarding, dossiers et scénarios, brouillon et étape conservés. Le deuxième compte ne voit pas le dossier ni le brouillon du premier. Une sauvegarde SQLite native est vérifiée (intégrité, SHA-256), copiée dans une nouvelle base, puis les mêmes vérifications sont exécutées dans un autre processus. Les données originales ne sont pas modifiées par la restauration.

Ces essais prouvent le fonctionnement du stockage et de la restauration quand le fichier est conservé. Ils ne prouvent pas une conservation définitive sur l’aperçu gratuit. Le service Render gratuit utilise un disque éphémère : ses comptes et dossiers peuvent disparaître au redémarrage ou au déploiement. Le bandeau l’indique et réserve l’aperçu aux données fictives. La configuration de production avec disque persistant /app/var est préparée dans render.yaml, mais sa création payante attend l’accord du propriétaire. La recette de redémarrage sur ce véritable hébergement demeure bloquante avant des comptes réels payants.

## Clôture de la recette gratuite — 19 octobre 2026

Le déploiement Render `dep-dbb8q92fngtc73fofnig`, commit applicatif `28da4db`, est en ligne. La version documentée `fcb4cb3` possède le même code. GitHub Actions [39328845620](https://github.com/loic5443/indice-immo-quebec/actions/runs/39328845620), job `118321680050`, a réussi : 427 tests en 51,838 secondes, dépendances vérifiées.

La sélection en ligne de l’adresse abrégée remplit bien Montréal et H3A 0B4; la valeur municipale n’est pas disponible dans cet aperçu pour cette adresse et reste indiquée comme manquante. Sur la dernière version à 390 px, sélectionner 170 chemin du Canal remplit Beauharnois et J6N 0J1 et révèle 463 100 $ au rôle 2026. La largeur du document reste de 390 px, sans débordement horizontal. Le message périmé de non-couverture n’apparaît plus au-dessus du résultat réussi.

[Capture de la mise en page à 390 px](QA_MOBILE_2026-10-19.jpg). Ceci reste une validation Chromium de largeur étroite, pas un essai matériel iPhone/Safari. Le service est toujours gratuit sans disque persistant; comptes réels et paiements ne doivent pas y être ouverts. La vérification de conservation sur le véritable hébergement reste à exécuter après accord sur les frais.
