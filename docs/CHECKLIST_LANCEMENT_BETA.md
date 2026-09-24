# Checklist bêta privée

- [x] Migrations versionnées et tests automatisés
- [x] Administration réservée aux rôles administrateurs
- [x] Données simulées séparées du parcours Marchés public
- [x] Exports et événements expurgés
- [x] Deux parcours isolés (60 vérifications réelles au niveau des services et du contenu PDF)
- [x] Parcours navigateur isolé du 23 septembre 2026 : accueil, suggestion consentie, rôle municipal, connexion, calcul, sauvegarde, réouverture, Marché, Premium, avis, administration et affichage à 390 px. Comptes et données fictifs dans une base temporaire.
- [x] Recontrôle navigateur isolé du 24 septembre 2026 : suggestion sans Entrée, rôle municipal immédiatement révélé, calcul, inscription, onboarding interrompu puis repris, sauvegarde, relecture, retour, intérêt Premium local, accès Gratuit/Premium/admin et pages secondaires. Aucun compte ni dossier réel modifié; aucune largeur excédentaire constatée à 390 px sur les pages inspectées.
- [ ] Parcours bêta complet de 58 gestes, incluant interface et PDF, à valider séparément
- [x] Revue technique des sources et de la confidentialité documentée dans [l’audit du 23 septembre 2026](AUDIT_TECHNIQUE_SOURCES_SECURITE_2026-09-23.md)
- [ ] Revue humaine des licences et de sécurité, notamment pour la diffusion commerciale
- [ ] Approbation avant publication ou envoi GitHub

Le recontrôle du 24 septembre couvre les actions ci-dessus, mais pas les 58 gestes de la checklist historique. Le bouton du PDF Premium a été exercé dans l'interface; le contenu et la confidentialité du fichier sont vérifiés par les tests automatisés, pas par une revue humaine du document téléchargé. La revue humaine des licences, de la sécurité de déploiement et la décision de fusion restent distinctes des tests techniques.
