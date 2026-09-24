# Alertes par courriel

Les alertes ImmoRadar sont construites uniquement à partir des instantanés que
l’utilisateur a sauvegardés et choisis de suivre. Elles ne prédisent pas le
marché et ne déclenchent jamais un courriel à partir d’une donnée manquante.

## Conditions d’envoi

- le dossier est suivi ;
- une alerte déterministe est calculable ;
- le compte a le droit Alertes (Premium technique ou administrateur) ;
- l’utilisateur a accepté séparément les alertes par courriel ;
- la livraison Brevo est explicitement activée dans l’environnement local.

Le courriel est volontairement générique : aucune adresse, valeur, donnée
financière ni détail d’alerte n’est mis dans une boîte de réception. Le détail
reste dans « Mes propriétés » après connexion.

## Alertes actuellement prises en charge

- variation entre deux ImmoValue suffisamment fiables ;
- variation entre deux valeurs au rôle municipal sauvegardées ;
- flux de trésorerie devenu négatif dans le scénario sauvegardé « Taux +1 point » ;
- rappel de renouvellement hypothécaire fourni explicitement par l’utilisateur.

Le service dépose une empreinte technique irréversible par alerte. Elle rend
l’envoi idempotent à travers les reruns Streamlit et ne contient ni dossier,
ni adresse, ni montant. La suppression du compte supprime aussi les journaux
de livraison associés.

## Traitement local

`scripts/dispatch_alerts.py` exécute une vérification pour les comptes ayant
déjà accepté les alertes. Il peut être lancé par un opérateur ou planifié dans
l’environnement local. Sa sortie contient uniquement des totaux et des statuts
catégoriels.
