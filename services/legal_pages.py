"""Public, printable product terms and privacy information."""
from html import escape
import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()
OPERATOR = "Loic St-Pierre"
SUPPORT_EMAIL = "loicstpierre29@gmail.com"


def legal_document(kind, environment=None):
    env = os.environ if environment is None else environment
    contact = f'<p>Exploitant : {OPERATOR}<br>Support et demandes concernant les renseignements personnels : <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>.</p>'
    for key, label in (("CENLIO_BUSINESS_ADDRESS", "Adresse commerciale"), ("CENLIO_BUSINESS_PHONE", "Téléphone")):
        value = env.get(key, "").strip()
        if value:
            contact += f"<p>{label} : {escape(value)}</p>"
    if kind == "conditions":
        title = "Conditions d’utilisation et d’abonnement"
        opening = ""
        if env.get("IMMORADAR_BILLING_ENABLED") != "1":
            opening = "<p class='notice'>Ouverture commerciale en préparation : les abonnements payants ne sont pas encore ouverts.</p>"
        body = opening + contact + """
<h2>Le service</h2>
<p>Cenlio est un outil d’aide à la décision immobilière. Les analyses utilisent vos hypothèses et les renseignements publics disponibles. Une valeur municipale est un repère fiscal; ImmoValue est expérimental et nécessite des comparables admissibles. Le service ne fournit pas une évaluation officielle ni une garantie de rendement et ne remplace pas les professionnels de votre projet.</p>
<h2>Compte gratuit et Premium</h2>
<p>Le compte gratuit donne accès aux outils de base selon les limites affichées dans le produit. Premium ajoute les dossiers sauvegardés, comparaisons, scénarios, rapports et suivis disponibles. Les calculs et alertes dépendent des données disponibles; ils ne garantissent pas une couverture de toutes les propriétés ni une mise à jour en temps réel. Les notifications par courriel dépendent de leur activation et de votre consentement.</p>
<h2>Prix et paiement</h2>
<p>L’offre de lancement prévue est de 14,99 $ CAD par mois. L’abonnement est renouvelé automatiquement chaque mois jusqu’à l’annulation du renouvellement. Le prix et le montant total applicable sont affichés avant votre confirmation sur Stripe. Aucun paiement n’est déclenché par la simple consultation d’une page. L’accès payant est activé après vérification du paiement par Cenlio.</p>
<h2>Annulation et remboursements</h2>
<p>Dans Premium, ouvrez « Gérer mon abonnement et mes factures » pour annuler le renouvellement. Un abonnement actif reste accessible jusqu’à la fin de sa période payée. L’annulation du renouvellement ne déclenche pas, à elle seule, un remboursement. Pour un paiement contesté, une erreur ou une demande de remboursement, écrivez au support. Vos droits d’annulation, de remboursement et autres recours prévus par les lois applicables demeurent entiers.</p>
<h2>Votre compte et vos données</h2>
<p>Vous êtes responsable de la confidentialité de votre accès et de l’exactitude des renseignements que vous fournissez. Vous pouvez exporter vos données et demander la suppression de votre compte. Si un abonnement est lié au compte, contactez le support pour régler son statut avant la suppression afin d’éviter une facturation sans accès.</p>
<h2>Disponibilité et changements</h2>
<p>Des interruptions, erreurs ou données manquantes peuvent survenir. Signalez-les au support. Les limites et fonctionnalités disponibles sont indiquées dans le produit. Ces conditions ne suppriment aucune garantie ou protection obligatoire. Tout changement de prix ou de conditions d’un abonnement doit être communiqué conformément aux règles applicables.</p>
"""
    else:
        title = "Politique de confidentialité"
        body = contact + """
<h2>Renseignements utilisés</h2>
<p>Cenlio utilise les renseignements nécessaires à votre compte : nom, courriel, mot de passe sous forme hachée, préférences et consentements. Vos analyses, adresses de propriétés, hypothèses, comparables et critères sauvegardés servent à afficher vos dossiers et à fournir les fonctions demandées. Lors d’un abonnement, Cenlio conserve les identifiants et le statut de facturation; les numéros de carte sont traités par Stripe.</p>
<h2>Pourquoi et avec quels prestataires</h2>
<p>Ces renseignements servent à authentifier votre compte, conserver vos dossiers, gérer votre abonnement et fournir les communications demandées. Render héberge l’application et sa base de données; le service actuel est hébergé aux États-Unis. Stripe traite les paiements. Brevo assure les courriels de récupération et, lorsque vous y consentez et que la fonction est activée, les notifications. Ces traitements peuvent avoir lieu hors du Québec.</p>
<h2>Recherches et communications</h2>
<p>Une recherche d’adresse auprès d’une source publique est effectuée avec votre consentement et transmet à cette source les éléments nécessaires à la recherche. Un courriel de récupération de mot de passe ne vous inscrit pas à une liste marketing. Les mesures analytiques facultatives sont désactivées par défaut et excluent les adresses, montants, comparables, mots de passe et rapports.</p>
<h2>Conservation et sécurité</h2>
<p>Les données de votre compte sont conservées pour fournir le service. Les contrôles de compte permettent leur export et leur suppression, sous réserve du traitement préalable d’un abonnement et des obligations de conservation applicables. Des copies peuvent subsister dans les sauvegardes; contactez le responsable pour toute demande relative à celles-ci. L’application utilise des accès limités et des connexions HTTPS, sans garantie d’absence totale d’incident.</p>
<h2>Vos demandes</h2>
<p>Vous pouvez modifier vos consentements dans Mon compte. Pour demander l’accès, la correction ou la suppression de renseignements, ou poser une question sur leur traitement, écrivez au responsable indiqué ci-dessus. Une vérification de votre identité peut être nécessaire pour protéger votre compte. Le retrait d’un consentement peut rendre indisponibles les fonctions qui en dépendent.</p>
"""
    return f"""<!doctype html><html lang="fr-CA"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — Cenlio</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;max-width:850px;margin:40px auto;padding:0 24px;color:#172337;background:#fafbf9}}a{{color:#3452b5}}h1{{line-height:1.2}}h2{{margin-top:32px}}.notice{{padding:16px;background:#eef0ff}}@media print{{nav{{display:none}}body{{background:white;margin:0}}}}</style>
<nav><a href="/">Cenlio</a> · <a href="/conditions">Conditions</a> · <a href="/confidentialite">Confidentialité</a></nav>
<main><h1>{title}</h1><p>Version du 3 novembre 2026</p>{body}</main></html>"""


@router.get("/conditions", response_class=HTMLResponse)
def conditions():
    return legal_document("conditions")


@router.get("/confidentialite", response_class=HTMLResponse)
def privacy():
    return legal_document("privacy")
