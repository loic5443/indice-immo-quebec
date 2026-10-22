# Courriels — préparation du 21 octobre 2026

## Mise à jour vérifiée du 22 octobre 2026

### Résultat après l'accord réseau

- Le propriétaire a explicitement autorisé l'ajout de l'adresse de test précise en /128. Brevo l'a enregistrée avec la méthode Manual; la protection contre les IP non autorisées reste active.
- Une nouvelle requête API a été refusée car l'environnement de travail utilise une autre adresse IPv6 sortante. Aucune autorisation de plage réseau, autre IP ni désactivation de protection n'a été effectuée. Le test API de l'application reste donc bloqué dans cet environnement.
- Un seul test a ensuite été envoyé par le bouton natif **Send Test** de Brevo, au seul destinataire préalablement approuvé. Sujet : **Cenlio - test de livraison**. Texte : « Bonjour Loïc, ceci est le test de livraison Cenlio par Brevo. Aucun paiement. »
- **Réception confirmée par le connecteur Gmail** : message du 22 octobre 2026 à 20:53:28 UTC, libellés INBOX, CATEGORY_UPDATES et UNREAD. Aucun second envoi n'a été lancé.
- Brevo a utilisé son domaine d'expédition `brevosend.com` pour l'expéditeur Gmail non authentifié. Ceci valide la livraison du test fournisseur; ce n'est pas une validation de domaine commercial ni de l'intégration API du site.
- Modèle de test séparé : `Cenlio - test de livraison 2026-10-22`, enregistré sans activation. Aucun automatisme ni campagne n'a été activé.
- La connexion automatique de l'application, les IP sortantes de production et un lien réel de récupération de mot de passe avec comptes persistants restent à valider. Les puces ci-dessous décrivent la situation avant cet accord et cet envoi.

- La connexion intégrée Render accède au service gratuit existant. La connexion navigateur GitHub a été autorisée par le propriétaire, mais aboutit à une création de compte Render : aucun nouveau compte n'a été créé.
- Après validation du code de sécurité par le propriétaire, la clé `Cenlio courriels transactionnels` a été créée : Restricted, Transactional email All et Account Read uniquement. Expiration le **5 novembre 2026** : durée raccourcie à 14 jours pour ne pas dépasser la période initialement autorisée. Les quatre anciennes clés sont inchangées.
- Le connecteur Render a accepté l'ajout de `BREVO_API_KEY` et `BREVO_SENDER_EMAIL`, avec fusion des variables existantes (`replace=false`). Aucune valeur secrète n'est inscrite ici ou dans Git.
- Contrairement à l'option Dashboard « Save only », cette mise à jour par connecteur a déclenché un déploiement API. Déploiement `dep-dbd7aq4ipgvc73eapbsg`, commit distant `43cc54cf887ce3579649b94c1bf7e7ed40fcdb69`, confirmé **live**. Aucun plan payant n'a été activé. Les changements locaux plus récents ne sont pas inclus dans ce déploiement.
- Le contrôle réel GET `/v3/account` a reçu HTTP 401 pour une adresse IP non autorisée, et non pour une clé invalide. La protection API reste active. Une autorisation pour une seule adresse de test (/128) est préparée dans Brevo et attend l'accord explicite du propriétaire. Les autres adresses n'ont pas été modifiées.
- **Aucun courriel de test n'a encore été envoyé.** L'acceptation par Brevo et la réception restent à vérifier après autorisation réseau. Ceci ne valide pas encore les adresses sortantes du futur hébergement de production.
- Vérification locale de la version courante : `.venv/bin/python -m unittest discover -s tests -q` : **428 tests réussis, 65,154 s**. Un premier essai avec le Python global a échoué pour dépendances absentes; la suite complète a ensuite réussi dans l'environnement du projet. Aucun code applicatif n'a été changé pendant cette séance.
- La mise en service commerciale, le stockage permanent des comptes, le domaine authentifié pour les courriels et les paiements réels ne sont pas déclarés terminés.
- Après le redéploiement, vérification dans le navigateur de `https://immoradar-apercu.onrender.com/` : page d'accueil chargée, navigation présente et avertissement explicite « Paiements et courriels désactivés ». Les comptes restent présentés comme temporaires.

Les sections suivantes décrivent les étapes historiques du 21 octobre; leurs attentes d'autorisation sont remplacées par la mise à jour ci-dessus.

## État vérifié dans Brevo

- Connexion sécurisée au compte Cenlio réussie, puis vérification du nouvel appareil par le propriétaire.
- Expéditeur nommé Cenlio, adresse Gmail existante, statut **Verified**. L'adresse personnelle n'est pas recopiée dans ce document public.
- Brevo signale une limite de délivrabilité liée au domaine gratuit. Aucun domaine acheté, configuré ou authentifié pendant cette préparation.
- Quatre anciennes clés API actives sont présentes et masquées. Aucune n'a été révélée, modifiée ou révoquée.
- Le blocage des adresses IP API non autorisées est actif. Aucun changement de cette protection n'a été effectué.

## Connexion préparée, non créée

Un formulaire de création de clé est préparé avec :

- Nom : `Cenlio courriels transactionnels`.
- Type : Restricted.
- Expiration : 21 novembre 2026.
- Transactional email : All, nécessaire à l'envoi; cette catégorie permet aussi la gestion des modèles et journaux transactionnels.
- Account : Read, pour vérifier le compte, les expéditeurs et les domaines.
- Autres catégories : None.

Le bouton Generate n'a pas été validé. La création d'un nouvel accès attend la confirmation à l'action imposée par la sécurité du navigateur. Aucun secret nouveau n'existe à ce stade.

## Validation de l'application

Le projet utilise déjà `providers/brevo_email.py`, les services de récupération de mot de passe et d'alertes consenties. Les 19 tests de récupération et d'alertes ont réussi lors de la vérification du 20 octobre; aucun code n'a été changé depuis pour cette préparation.

Les variables de connexion n'étaient pas présentes dans l'environnement de travail lors de cette vérification. La connexion réelle à l'application, l'éventuelle autorisation de l'IP du serveur, l'envoi d'un courriel de test au propriétaire et la vérification de réception restent à effectuer. Aucun courriel n'a été envoyé par l'assistant pendant cette préparation.

L'aperçu Render conserve les courriels désactivés. La validation d'un lien de récupération sur un hébergement avec comptes persistants reste une étape de mise en service distincte.

## Accord reçu et connexion Render en attente

Le propriétaire a confirmé la création de la clé restreinte avec expiration au 21 novembre, son stockage dans les secrets Render et l'envoi d'un seul courriel de test à son adresse explicitement confirmée. Cet accord est conservé; il n'est pas à redemander.

Le service cible a été relu via le connecteur Render : `srv-dbaj03rbc2fs73bj2eug` (`immoradar-apercu`), espace `tea-db98dkcs728c73fdacl0`, plan gratuit, déploiement automatique désactivé. La documentation Render actuelle confirme l'option Dashboard « Save only », qui permet de conserver un secret sans redéployer.

La session navigateur Render demande une connexion. Le propriétaire a choisi GitHub dans le formulaire sécurisé. GitHub présente ensuite une autorisation pour Render, identité `loic5443`, adresses courriel en lecture. Le contrôle automatique a refusé le clic Authorize et exige un accord explicite pour cet accès OAuth. Aucune autorisation n'a été validée par l'assistant.

La création effective de la clé Brevo est différée jusqu'à ce que son stockage sécurisé soit accessible, pour éviter une clé générée sans destination disponible. Aucun nouveau secret n'a été créé, aucune variable Render n'a été modifiée et aucun courriel de test n'a été envoyé à ce stade.
