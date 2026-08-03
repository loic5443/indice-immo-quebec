# Suggestions d’adresses Québec — géocodeur MRNF

## Finalité et source

ImmoRadar propose une autocomplétion facultative au moyen du service officiel [Adresses Québec — REST (géocodeur)](https://servicescarto.mrnf.gouv.qc.ca/pes/rest/services/Territoire/Adresse_Geocodage/GeocodeServer), référencé par sa [fiche Données Québec](https://www.donneesquebec.ca/recherche/dataset/adresses-quebec/resource/64cbcdfc-4dd6-42e7-9a5d-489e775da83b).

L’appel est possible seulement après le consentement explicite de recherche publique. La saisie manuelle reste disponible à tout moment. Le géocodeur ne sert ni à calculer ImmoValue ni à calculer ImmoScore.

## Contrat technique observé

Le service annonce la capacité officielle `Suggest`. ImmoRadar appelle `suggest` pendant la frappe pour obtenir au plus huit libellés, puis appelle `findAddressCandidates` seulement lorsqu’une personne choisit une suggestion. Ce second point d’accès annonce les champs candidats `Num`, `Odonyme`, `Dir`, `Unite`, `SufNum`, `City` et `ZIP`, seuls champs utilisés pour remplir les éditeurs d’adresse.

Les coordonnées, le score, `Match_addr`, la requête et le contenu brut de la réponse sont écartés. Ils ne sont ni envoyés à la télémétrie, ni inscrits dans les diagnostics, ni conservés dans un brouillon. Les suggestions restent en mémoire au plus 30 secondes et sont remplacées à chaque saisie.

## Garde-fous et mode dégradé

- HTTPS et hôte MRNF exact obligatoires ; aucun contournement de certificat n’est autorisé.
- Trois caractères utiles au minimum, un délai de 400 ms avant la recherche, huit suggestions au maximum, un délai réseau maximal de trois secondes et un cache mémoire court.
- Si le service est lent, indisponible ou répond avec un schéma incompatible, ImmoRadar affiche un message neutre et laisse le parcours manuel fonctionner.
- Une suggestion remplit les champs; la recherche de renseignements officiels et la sauvegarde ne surviennent qu’après la confirmation normale de l’utilisateur.

Attribution affichée à proximité des suggestions : **MRNF — Adresses Québec**.
