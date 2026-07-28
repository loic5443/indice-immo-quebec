# ImmoRadar — Architecture technique
## Architecture cible, données, sécurité et exploitation

**Version :** 1.0  
**Point de départ :** application Streamlit monolithique, SQLite local  
**Principe :** faire évoluer sans réécriture prématurée.

## 1. État actuel vérifié

Le dépôt `IndiceImmo` contient :

- `indice_immo.py` pour la composition des pages;
- `components/` pour l’interface;
- `calculations/real_estate.py` pour les formules;
- `data/database.py` pour SQLite, PBKDF2 et analyses;
- `data/real_data.py` et `data/simulated_data.py`;
- `tests/` pour calculs et persistance;
- `styles/main.css` et une image hero locale.

La base crée `users` et `analyses`. Les mots de passe utilisent PBKDF2-HMAC-SHA256 avec sel aléatoire et 260 000 itérations. L’isolation CRUD se fait par `user_id`. Cette base est convenable pour un prototype local, mais pas suffisante pour un service public.

## 2. Architecture évolutive

### Étape A — Monolithe modulaire

Conserver Streamlit, mais introduire :

- couche `domain/` pour modèles et règles;
- couche `services/` pour cas d’usage;
- couche `repositories/` pour persistance;
- couche `providers/` pour sources externes;
- `migrations/`, configuration et journalisation.

### Étape B — Application web + API

Quand les besoins d’authentification, paiement, mobile ou performance le justifient :

- frontend web;
- API REST ou GraphQL;
- services asynchrones pour rapports et ingestion;
- PostgreSQL;
- stockage d’objets;
- file de tâches;
- observabilité.

Éviter des microservices indépendants avant que l’équipe et la charge ne l’exigent.

## 3. Modules cibles

| Module | Responsabilité |
|---|---|
| Identity | comptes, sessions, vérification, récupération |
| Entitlements | forfaits, quotas, droits |
| Property | adresse, attributs, provenance |
| Market Data | séries, zones, dates, licences |
| Engine | calculs, scores, confiance |
| Analysis | orchestration et instantanés |
| Reports | génération et stockage |
| Billing | Stripe, webhooks, factures |
| Notifications | courriels, préférences, désabonnement |
| Admin | sources, incidents, quotas, versions |

## 4. Modèle de données cible

### 4.1 Identité

`users(id, email, name, status, created_at, deleted_at)`  
`credentials(user_id, password_hash, algorithm, updated_at)`  
`sessions(id, user_id, expires_at, revoked_at, device_hash)`  
`user_profiles(user_id, persona, horizon, risk_tolerance, preferences_json)`

### 4.2 Forfaits

`plans(id, code, version, limits_json)`  
`subscriptions(id, user_id, provider, external_id, status, current_period_end)`  
`entitlements(user_id, key, value, source, expires_at)`  
`usage_events(id, user_id, metric, quantity, period_key, idempotency_key)`

### 4.3 Propriétés et sources

`properties(id, canonical_address, lat, lon, property_type, created_at)`  
`property_facts(id, property_id, fact_key, value_json, source_id, observed_at, valid_from, valid_to, confidence)`  
`data_sources(id, name, license_code, terms_url, refresh_policy)`  
`source_runs(id, source_id, started_at, completed_at, status, checksum)`

Le modèle « facts » permet de conserver provenance et évolution sans écraser silencieusement une valeur.

### 4.4 Analyses

`analyses(id, user_id, property_id, engine_version, status, created_at, data_as_of)`  
`analysis_inputs(analysis_id, inputs_json, schema_version)`  
`analysis_outputs(analysis_id, outputs_json, schema_version)`  
`analysis_factors(id, analysis_id, module, factor, direction, impact, source_fact_id)`  
`saved_views(id, user_id, analysis_id, label, favorite, notes)`

### 4.5 Marchés et comparables

`geographies(id, type, code, name, geometry_ref)`  
`market_series(id, geography_id, metric, period, value, unit, source_id)`  
`transactions(id, property_id, sale_date, price, transaction_type, source_id, admissibility)`  
`comparable_sets(id, analysis_id, algorithm_version)`  
`comparable_items(set_id, transaction_id, similarity, adjustments_json, included, reason)`

## 5. API interne

### Analyse

`POST /v1/analyses` crée une demande idempotente.  
`GET /v1/analyses/{id}` retourne statut et résultat autorisé.  
`POST /v1/analyses/{id}/scenarios` calcule un scénario.  
`GET /v1/analyses/{id}/report` retourne une URL temporaire.

### Compte

`POST /v1/auth/register`, `verify-email`, `login`, `logout`, `forgot-password`, `reset-password`.  
Les réponses ne révèlent pas si une adresse existe.

### Quotas

L’API vérifie un droit avant de lancer une estimation, réserve une unité, puis confirme ou libère la réservation selon le résultat.

## 6. Pipeline d’analyse

1. Valider l’autorisation et le quota.
2. Normaliser l’entrée.
3. Résoudre la propriété.
4. Collecter les faits autorisés.
5. Contrôler qualité, fraîcheur et compatibilité.
6. Construire l’instantané immuable.
7. Exécuter les modules déterministes.
8. Générer les explications structurées.
9. Persister résultats et trace.
10. Confirmer le quota.
11. Déclencher rapport/notification.

Chaque étape est rejouable avec un identifiant d’idempotence.

## 7. Sécurité

### 7.1 Authentification

- Utiliser Argon2id ou PBKDF2 avec paramètres réévalués périodiquement.
- Cookies `Secure`, `HttpOnly`, `SameSite`.
- Rotation des sessions après connexion.
- Protection CSRF, limitation de débit et verrouillage progressif.
- MFA facultatif pour comptes Pro, obligatoire pour administrateurs.

### 7.2 Autorisation

La règle propriétaire est appliquée au niveau service et requête. Les tests d’accès croisé sont obligatoires. Les rôles administratifs sont séparés des comptes utilisateurs.

### 7.3 Secrets

Secrets exclusivement dans le gestionnaire de secrets de l’hébergeur; jamais dans Git, base locale ou logs. Rotation documentée.

### 7.4 Chiffrement et sauvegarde

- TLS en transit.
- Chiffrement géré au repos.
- Sauvegardes chiffrées, restauration testée.
- Rétention distincte pour données, logs et rapports.

## 8. Vie privée

- Inventaire des renseignements personnels.
- Finalité explicite et minimisation.
- Consentement distinct pour marketing.
- Accès, rectification, export et suppression.
- Évaluation des facteurs relatifs à la vie privée avant données sensibles ou profilage avancé.
- Contrats avec sous-traitants.
- Journal et procédure d’incident.

Les obligations exactes doivent être validées par un conseiller juridique québécois avant lancement.

## 9. Données et licences

Chaque source doit posséder :

- propriétaire;
- URL et conditions;
- base légale/contractuelle;
- champs autorisés;
- restrictions de redistribution;
- fréquence;
- qualité attendue;
- coût;
- responsable interne;
- procédure de retrait.

Le fait qu’une information soit publiquement consultable ne garantit pas qu’une collecte automatisée ou une réutilisation commerciale soit permise.

## 10. Cache et rafraîchissement

- Taux macro : cache selon fréquence officielle.
- Séries mensuelles/trimestrielles : version immuable par période.
- Faits de propriété : durée selon source et type.
- Résultats d’analyse : ne jamais être recalculés silencieusement.
- Nouvelle version : proposer « actualiser l’analyse » et conserver l’ancienne.

## 11. Observabilité

### Journaux

Événements structurés avec correlation ID, sans mot de passe, adresse complète ou résultat financier inutile.

### Métriques

- latence par étape;
- taux d’échec et refus;
- disponibilité des fournisseurs;
- coût par analyse;
- dérive et confiance;
- webhooks Stripe échoués;
- courriels et rapports.

### Alertes

Définir seuil, canal, propriétaire, délai et runbook pour chaque alerte critique.

## 12. Paiements

- Stripe Checkout hébergé.
- Webhooks signés.
- Idempotence pour chaque événement.
- L’abonnement externe est source de facturation; les droits internes sont dérivés.
- Gérer `active`, `trialing`, `past_due`, `canceled`, remboursements et litiges.
- Le portail client gère carte, facture et annulation.
- Tester avec horloge de test et scénarios de retard.

## 13. Déploiement

Environnements : local, test, staging, production.  
Chaque environnement possède bases, clés et fournisseurs séparés.  
Pipeline : formatage, tests, analyse de dépendances, migrations, déploiement, smoke test, rollback.

## 14. Plan de migration depuis SQLite

1. Ajouter une couche repository sans changer l’UI.
2. Introduire migrations versionnées.
3. Écrire tests contractuels SQLite/PostgreSQL.
4. Exporter et valider les données.
5. Importer en staging.
6. Vérifier comptes, analyses, compteurs.
7. Fenêtre de migration et sauvegarde.
8. Basculer et surveiller.

Les mots de passe existants peuvent être réhachés à la prochaine connexion si le format conserve l’algorithme et les paramètres.

## 15. Qualité

- tests unitaires du domaine;
- tests d’intégration des repositories;
- tests contractuels des fournisseurs;
- E2E du parcours critique;
- tests de sécurité et autorisation;
- tests de charge sur analyse/rapport;
- tests de migration et restauration;
- fixtures ne contenant aucune donnée réelle d’utilisateur.

## 16. Risques techniques prioritaires

| Risque | Impact | Réponse |
|---|---|---|
| Source retirée ou licence modifiée | Résultats incomplets | abstraction fournisseur, inventaire, mode dégradé |
| Mauvais appariement d’adresse | Mauvaise propriété | score de résolution et confirmation utilisateur |
| Données incompatibles | Score trompeur | contrats de schéma et contrôles qualité |
| Quota débité à tort | Friction client | réservation/confirmation idempotente |
| Accès croisé | Incident majeur | filtrage propriétaire et tests |
| Dérive du modèle | Perte de confiance | monitoring segmenté et rollback |

## 17. Décisions d’architecture

- ADR-001 : monolithe modulaire avant microservices.
- ADR-002 : instantanés immuables des analyses.
- ADR-003 : source et date au niveau du fait.
- ADR-004 : moteur déterministe séparé du texte génératif.
- ADR-005 : droits séparés de la facturation.
- ADR-006 : refus explicite quand les données sont insuffisantes.
