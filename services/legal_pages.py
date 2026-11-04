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
<p>Premium coûte 14,99 $ CAD par mois. L’abonnement est renouvelé automatiquement chaque mois jusqu’à l’annulation du renouvellement. Le prix et le montant total applicable sont affichés avant votre confirmation sur Stripe. Aucun paiement n’est déclenché par la simple consultation d’une page. L’accès payant est activé après vérification du paiement par Cenlio.</p>
<h2>Annulation de l’abonnement</h2>
<p>Dans Premium, ouvrez « Gérer mon abonnement et mes factures » pour annuler le renouvellement. Un abonnement actif reste accessible jusqu’à la fin de sa période payée. L’annulation du renouvellement ne déclenche pas, à elle seule, un remboursement. Pour une erreur de paiement ou un recours prévu par la loi, écrivez au support. Vos droits d’annulation, de remboursement et autres recours prévus par les lois applicables demeurent entiers.</p>
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
<h2>Programme créateurs</h2><p>Si vous utilisez un code à l’inscription, Cenlio conserve le créateur associé au compte, la date et les commissions liées au premier paiement. Le créateur voit des références et des montants, jamais votre nom, votre courriel ou vos analyses. Aucun cookie publicitaire n’est nécessaire à ce suivi. Les écritures liées aux paiements peuvent devoir être conservées; contactez le responsable pour vos demandes.</p>
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


@router.get("/createurs", response_class=HTMLResponse)
def creator_landing():
    return """<!doctype html><html lang="fr-CA"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Créateurs — Gagnez avec Cenlio</title>
<style>body{margin:0;background:#101d28;color:#edf7ee;font:18px/1.65 system-ui}main{max-width:980px;margin:auto;padding:60px 24px}h1{font-size:clamp(36px,6vw,64px);line-height:1.08;max-width:850px}h2{line-height:1.25}.lead{font-size:23px;max-width:760px}.tag{color:#a8e6ba;letter-spacing:2px;font-size:14px}.cta{display:inline-block;background:#b8f07b;color:#102016;padding:15px 23px;border-radius:10px;font-weight:700;text-decoration:none}a{color:#c9f5ae}.grid{display:flex;flex-wrap:wrap;gap:16px;margin:32px 0}.card{flex:1;min-width:180px;background:#20333e;padding:24px;border-radius:16px}.card strong{font-size:36px;display:block}.rules{background:#f3f6f0;color:#152b24;padding:30px;border-radius:18px;margin-top:48px}.rules a{color:#214f39}li{margin:12px 0}footer{font-size:15px;margin-top:32px}</style>
<main><a href="/">CENLIO</a><p class="tag">POUR LES CRÉATEURS IMMOBILIERS</p>
<h1>Vous partagez le bon outil.<br>Chaque nouveau client peut vous rapporter 10 $.</h1>
<p class="lead">Aidez votre communauté à vérifier les chiffres d’une propriété avec Cenlio. Un nouveau client prend Premium avec votre lien ? Vous gagnez <b>10 $ CA une seule fois</b>, si son premier paiement est admissible.</p>
<a class="cta" href="/?createur=1">Obtenir mon lien gratuit</a><p>Aucun frais pour participer. Aucun abonnement Premium à acheter.</p>
<div class="grid"><div class="card">10 clients validés<strong>100 $</strong></div><div class="card">50 clients validés<strong>500 $</strong></div><div class="card">100 clients validés<strong>1 000 $</strong></div></div>
<p>Exemples : nombre de clients admissibles × 10 $. Ce ne sont pas des revenus garantis. Vos résultats dépendent de vos ventes.</p>
<h2>L’angle à présenter à votre communauté</h2><p><b>« Vous magasinez une maison sur Centris ? Avant de vous décider, regardez aussi ses chiffres sur Cenlio. »</b></p><p>Adresse, prix demandé, budget : montrez comment passer d’une propriété qui plaît à un projet qu’on comprend. Cenlio s’adresse aux premiers acheteurs, aux gens qui regardent des maisons et aux investisseurs au Québec.</p>
<h2>Vidéo courte : prête à adapter avec votre voix</h2><p>« Cette maison vous plaît sur Centris ? Le prix affiché ne dit pas tout sur votre projet. Relevez l’adresse et les chiffres, puis faites votre analyse sur Cenlio. Regardez les renseignements municipaux disponibles, testez votre budget et comparez vos options. Avec au moins trois ventes comparables admissibles que vous fournissez, ImmoValue peut aussi calculer une estimation. Vous hésitez entre plusieurs maisons ? Premium garde vos dossiers, vos comparaisons et vos rapports pour 14,99 $ CA par mois. Avant votre prochaine visite, prenez le réflexe Cenlio. Commencez gratuitement avec mon lien. »</p>
<p><b>À dire ou afficher :</b> « Publicité — je reçois une commission si vous vous abonnez avec mon lien. » Le créateur peut montrer le produit sans prétendre l’avoir utilisé personnellement. Toute expérience personnelle racontée doit être réelle.</p>
<p><b>Pour filmer :</b> utilisez une propriété fictive dans la démonstration publique. N’affichez pas de photos, de logo ou de captures d’une annonce Centris sans les autorisations nécessaires. Aucun import automatique des annonces. Cenlio est indépendant de Centris.</p>
<p><b>Sur la valeur :</b> l’évaluation municipale est un repère fiscal, pas la valeur marchande. ImmoValue est une estimation expérimentale : au moins trois ventes comparables admissibles fournies par l’utilisateur sont nécessaires. La couverture des données municipales varie. Ne promettez pas une valeur automatique pour toutes les propriétés, un prix exact ou une économie garantie.</p>
<p>Premium coûte 14,99 $ CA par mois et réunit les comparaisons, scénarios, rapports et suivis disponibles. Les calculs dépendent des chiffres saisis : ne promettez ni rendement ni achat gagnant.</p>
<h2>Votre preuve, dans votre espace</h2><p>Un lien et un code pour vous. Chaque nouveau compte inscrit avec ce code est lié à vous. Stripe confirme le paiement; votre espace affiche ensuite une référence, 10 $ et l’état de la commission. Vous pouvez télécharger votre relevé.</p>
<a class="cta" href="/?createur=1">Créer mon espace créateur</a>
<section class="rules"><h2>Les règles, simplement</h2><p>Version du 4 novembre 2026 · Programme exploité par Loic St-Pierre / Cenlio.</p><ol>
<li><b>Votre lien, votre client.</b> Le client doit utiliser votre lien ou saisir votre code quand il crée son nouveau compte. Le premier code enregistré reste associé au compte. Aucun ajout après l’inscription. Le lien est mémorisé dans la session en cours, sans cookie publicitaire; changer d’appareil peut perdre ce lien. Le code à l’inscription sert de solution de rechange.</li>
<li><b>10 $ CA une seule fois.</b> Le premier abonnement doit être payé dans les 30 jours de l’inscription, avec un premier paiement d’au moins 14,99 $ CA hors crédits gratuits. Pas de commission sur les renouvellements, réabonnements, essais, comptes existants, comptes de test, votre propre compte ou les ventes frauduleuses. Le client conserve le même prix.</li>
<li><b>Validation de 30 jours après le paiement.</b> Un paiement remboursé, contesté ou signalé pour fraude place la commission en vérification. Une commission non admissible n’est pas versée. Une commission déjà payée reste inscrite au relevé; toute correction est examinée avec le créateur.</li>
<li><b>Versements manuels chaque mois.</b> Les commissions validées sont réglées au plus tard à la fin du mois suivant la fin de leur validation. Aucun minimum. Contactez Cenlio avec votre code pour convenir d’un moyen de versement et fournir les renseignements nécessaires. Aucun virement automatique dans l’application. Une fois le versement fait, sa confirmation apparaît dans votre espace.</li>
<li><b>Annoncez la collaboration.</b> Indiquez clairement « Publicité — je reçois une commission si vous vous abonnez avec mon lien ». Ne vous présentez pas comme un client satisfait si vous n’avez pas utilisé le service. Pas de promesses de gains immobiliers, de faux avis ou de messages non sollicités en masse.</li>
<li><b>Des données limitées.</b> Vous voyez vos inscriptions et commissions avec des références; aucun nom, courriel ou renseignement de carte des clients. Cenlio conserve les liens de recommandation et les écritures de commission pour gérer le programme. Demandes d’accès ou de correction au support.</li>
<li><b>Vous pouvez arrêter de partager.</b> Les commissions déjà admissibles restent dues. Cenlio peut suspendre un lien en cas d’abus et vous en expliquer la raison; les règles d’une commission déjà acquise ne sont pas changées rétroactivement. Chaque partie reste responsable de ses obligations fiscales.</li></ol>
<p>Une attribution manquante ? Contactez <a href="mailto:loicstpierre29@gmail.com">loicstpierre29@gmail.com</a> avec votre code et la référence de votre relevé, sans envoyer de données de carte.</p></section>
<footer><a href="/conditions">Conditions d’abonnement</a> · <a href="/confidentialite">Confidentialité</a> · <a href="/">Essayer Cenlio</a></footer></main></html>"""
