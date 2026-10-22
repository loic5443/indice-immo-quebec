# Cenlio — vérification préliminaire et changement de marque

Décision utilisateur du 22 octobre 2026 : retenir Cenlio, effectuer une seconde vérification incluant les boutiques d’applications, puis avancer sur le renommage.

## Résultats vérifiés le 22 octobre 2026

- Recherche Web exacte avec deux moteurs : aucun usage immobilier ou logiciel évident repéré. Des pseudonymes et un modèle de chemise Diega existent. Ce dernier est dans un autre secteur.
- App Store Canada : interrogation publique de https://itunes.apple.com/search?term=cenlio&country=ca&entity=software&limit=200 ; 10 résultats approchants, aucun titre exactement Cenlio. Ce contrôle ne réserve aucun nom et ne couvre pas tous les pays.
- Google Play Canada : recherche publique https://play.google.com/store/search?q=Cenlio&c=apps&hl=fr&gl=CA ; page récupérée, résultats approchants (Calilio, Celo, Canchello, Mycelio, etc.), aucune application exactement Cenlio identifiée. Recherche Web des domaines apps.apple.com et play.google.com également sans résultat exact identifié.
- OPIC : formulaire public de recherche canadienne interrogé via son endpoint POST /cipo/trademark-search/srch avec searchfield1=tmlookup_ext et textfield1=CENLIO, sans restriction de classe/statut. Réponse HTTP 200 : numFound=0, docs=[], numReturned=0, empty=true. Il s’agit d’une recherche du terme, pas d’une étude juridique des ressemblances visuelles ou phonétiques.
- Registre .com Verisign : cenlio.com enregistré (HTTP 200 RDAP).
- Registre .ca : cenlio.ca non trouvé (HTTP 404 RDAP). Vérifier la disponibilité effective lors de la réservation. Aucun domaine acheté.
- Registre des entreprises du Québec : recherche directe officielle non terminée ; l’absence de résultat dans un moteur Web ne vaut pas vérification du registre.

## Mise en œuvre locale

Marque visible Cenlio/CENLIO dans les pages, titre navigateur, initiales de navigation CE, textes des rapports PDF, noms des fichiers téléchargés, courriels et expéditeur Brevo. Corrections grammaticales des élisions après changement du nom.

Les variables IMMORADAR_*, les clés de session, chemins de stockage, identifiants Stripe sont conservés pour la compatibilité. Les polices PDF sont renommées CenlioSans ; l’image sans texte est renommée cenlio-hero.png et les mentions de marque dans la documentation sont mises à jour. La migration 0029 remplace uniquement l’ancien libellé généré de provenance des analyses, sans modifier les comptes ni les chiffres. Aucun secret, compte externe, produit Stripe, service Render ni dépôt distant renommé. Aucune facturation ni livraison de courriel activée.

## Validation

429 tests de la suite complète réussis après nettoyage final (58,701 s), dont le test de migration des anciens dossiers. Les 11 destinations ont aussi été chargées par AppTest sans exception ni ancienne marque dans les textes contrôlés. Les deux PDF ont été générés et leur texte extrait contrôlé. Dépendances et compilation Python vérifiées ; git diff --check propre.

## Limites avant lancement commercial

Terminer le contrôle officiel au REQ et la recherche des marques proches. Les recherches réalisées ne constituent pas une garantie juridique de disponibilité. La marque et le domaine ne sont ni réservés ni protégés par ce changement de code. Le site hébergé reste sur sa version précédente tant que ce commit local n’est pas synchronisé et déployé.
