"""Public, server-rendered discovery content; no account or property data."""
from html import escape
from base64 import b64decode
import json
from pathlib import Path
import re

ORIGIN = "https://cenlio.onrender.com"
GUIDE_PATH = "/valeur-propriete-quebec"
TITLE = "Cenlio | Valeur des propriétés et analyse immobilière au Québec"
DESCRIPTION = "Une propriété vous intéresse au Québec ? Révélez sa valeur municipale disponible, explorez son estimation ImmoValue lorsqu’elle est calculable et analysez votre budget avec Cenlio."


FAVICON_PNG_BASE64 = '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'


def favicon_png():
    """Stable square Cenlio brand mark, also used by the app browser tab."""
    return b64decode(FAVICON_PNG_BASE64)


def metadata(title=TITLE, description=DESCRIPTION, path="/"):
    url = ORIGIN + path
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": ORIGIN + "/#organization", "name": "Cenlio", "url": ORIGIN + "/", "email": "contactcenlio@gmail.com", "logo": ORIGIN + "/favicon.png"},
        {"@type": "WebSite", "@id": ORIGIN + "/#website", "name": "Cenlio", "url": ORIGIN + "/", "inLanguage": "fr-CA", "publisher": {"@id": ORIGIN + "/#organization"}},
    ]}
    return (f'<title>{escape(title)}</title>\n'
            f'<meta name="description" content="{escape(description, quote=True)}">\n'
            f'<link rel="canonical" href="{url}">\n'
            '<link rel="icon" type="image/png" sizes="192x192" href="/favicon.png">\n'
            '<meta name="google-site-verification" content="ru_zdMYM8dMsKIbKy08xdxPFOB8mIg8LakDqlcDz74M">\n'
            '<meta property="og:type" content="website">\n'
            '<meta property="og:site_name" content="Cenlio">\n'
            '<meta property="og:locale" content="fr_CA">\n'
            f'<meta property="og:title" content="{escape(title, quote=True)}">\n'
            f'<meta property="og:description" content="{escape(description, quote=True)}">\n'
            f'<meta property="og:url" content="{url}">\n'
            '<meta name="twitter:card" content="summary">\n'
            f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>')


def guide_html():
    return '''<!doctype html><html lang="fr-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">''' + metadata(
        "Valeur d’une propriété au Québec : comprendre et analyser | Cenlio", path=GUIDE_PATH
    ) + '''<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#172033;font:18px/1.65 system-ui,sans-serif}header,main,footer{max-width:980px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;gap:20px}a{color:#1d4ed8}a:focus-visible{outline:3px solid #2563eb;outline-offset:5px}.brand{font-size:26px;font-weight:800;text-decoration:none;color:#123765}.hero{background:#123765;color:white;border-radius:24px;padding:clamp(24px,5vw,52px)}h1{font-size:clamp(30px,5vw,48px);line-height:1.15;margin:12px 0 24px}h2{font-size:27px;line-height:1.3}h3{font-size:21px}.eyebrow{font-size:14px;letter-spacing:.09em;text-transform:uppercase}.button{display:inline-block;background:#2563eb;color:#fff;padding:13px 22px;border-radius:10px;text-decoration:none;font-weight:700}.hero .button{background:white;color:#123765}section{margin-bottom:28px}.card{padding:28px;background:white;border:1px solid #d8e1ed;border-radius:18px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid .card{margin:0}footer{font-size:15px}footer nav{display:flex;flex-wrap:wrap;gap:20px}@media(max-width:600px){.grid{grid-template-columns:1fr}header{align-items:flex-start;flex-direction:column}.card{padding:22px}header,main,footer{padding:18px}}
</style></head><body><header><a class="brand" href="/">CENLIO</a><a href="/">Ouvrir Cenlio</a></header><main>
<section class="hero"><p class="eyebrow">Valeur et analyse immobilière au Québec</p><h1>Combien vaut cette propriété ? Commencez par comprendre ses chiffres.</h1><p>Une maison vous plaît ? Vous êtes propriétaire ou vous préparez un achat ? Cenlio vous aide à révéler les renseignements disponibles sur sa valeur et à voir ce qu’elle représente pour votre budget.</p><a class="button" href="/">Commencer sur Cenlio</a></section>
<section class="card"><h2>Le prix affiché ne raconte pas toute l’histoire</h2><p>Le prix demandé est le montant souhaité par le vendeur. Avant de vous engager, prenez le temps de regarder la valeur municipale, les caractéristiques de la propriété et les coûts de votre projet. Cenlio rassemble ces repères pour vous aider à poser les bonnes questions.</p><p>Vous regardez une annonce sur Centris ? Relevez l’adresse, le prix et les caractéristiques, puis saisissez-les dans Cenlio. Les annonces ne sont pas importées automatiquement. Cenlio est indépendant et n’est pas affilié à Centris.</p></section>
<section><h2>Comprendre la valeur révélée par Cenlio</h2><div class="grid"><article class="card"><h3>La valeur municipale</h3><p>Quand les données sont disponibles, Cenlio révèle la valeur inscrite au rôle municipal officiel. C’est un repère fiscal : il ne correspond pas nécessairement au prix auquel une propriété se vendrait aujourd’hui. L’année du rôle et le secteur comptent.</p></article><article class="card"><h3>L’estimation ImmoValue</h3><p>ImmoValue est distincte de la valeur municipale. Cenlio ne la produit que lorsqu’au moins trois comparables admissibles sont disponibles. Si les données ne suffisent pas, aucune estimation ImmoValue n’est présentée comme un résultat calculé.</p></article></div></section>
<section class="card"><h2>Analysez aussi ce que la propriété vous coûtera</h2><p>Une propriété peut vous plaire sans convenir à votre budget. Selon les renseignements saisis, l’analyse Cenlio vous aide à examiner votre scénario financier, à comparer vos options et à lire un score expliqué. Vous voyez les hypothèses utilisées et les points à vérifier avant d’aller plus loin.</p><ol><li><strong>Ajoutez l’adresse et les renseignements.</strong> Vous pouvez saisir les données manuellement ou autoriser la recherche de renseignements publics disponibles.</li><li><strong>Consultez la valeur et l’analyse.</strong> Distinguez la valeur municipale, l’estimation lorsqu’elle est calculable et les chiffres de votre projet.</li><li><strong>Revenez sur votre dossier.</strong> Selon les fonctions et l’abonnement disponibles, sauvegardez vos analyses et consultez les alertes prises en charge.</li></ol><a class="button" href="/">Découvrir l’analyse Cenlio</a></section>
<section class="card"><h2>Vos questions sur l’analyse d’une propriété</h2><h3>Est-ce utile si je suis déjà propriétaire ?</h3><p>Oui. Comprendre les repères de valeur et revoir les chiffres de votre propriété peut aussi servir à préparer votre prochain projet. La disponibilité des résultats dépend des renseignements accessibles et saisis.</p><h3>Puis-je commencer sans compte ?</h3><p>Vous pouvez commencer une analyse sans compte ni document. Vous choisissez ensuite si vous autorisez la consultation de renseignements publics.</p><h3>La valeur municipale est-elle la valeur marchande ?</h3><p>Non. Le rôle municipal sert à l’évaluation fiscale. Une valeur marchande dépend notamment du marché, des caractéristiques et de l’état du bien. Cenlio distingue ces repères au lieu de les confondre.</p><h3>Une estimation est-elle toujours disponible ?</h3><p>Non. Cenlio indique les limites des données. ImmoValue exige au moins trois comparables admissibles. Une analyse reste une aide à la décision et ne remplace pas une évaluation professionnelle.</p></section>
<section class="hero"><h2>Avant votre prochaine visite, prenez le réflexe Cenlio.</h2><p>Regardez la propriété. Révélez les repères disponibles sur sa valeur. Analysez les chiffres avant de décider.</p><a class="button" href="/">Ouvrir Cenlio</a></section>
</main><footer><p>Cenlio — L’immobilier, plus clair.</p><nav><a href="/">Accueil</a><a href="/createurs">Espace créateur</a><a href="/conditions">Conditions</a><a href="/confidentialite">Confidentialité</a><a href="mailto:contactcenlio@gmail.com">contactcenlio@gmail.com</a></nav></footer></body></html>'''


def robots_text():
    return "User-agent: *\nAllow: /\nDisallow: /stripe/\nDisallow: /_deployment/\nSitemap: " + ORIGIN + "/sitemap.xml\n"


def sitemap_xml():
    paths = ("/", GUIDE_PATH, "/createurs", "/conditions", "/confidentialite")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + ORIGIN + path + '</loc></url>' for path in paths) + '</urlset>'


def prepare_streamlit():
    """Set real initial-response metadata, not a script inserted after rendering."""
    import streamlit
    index = Path(streamlit.__file__).parent / "static" / "index.html"
    html = index.read_text(encoding="utf-8")
    (index.parent / "favicon.png").write_bytes(favicon_png())
    if "<!-- cenlio-seo -->" in html:
        return
    html = re.sub(r'<link\b(?=[^>]*\brel=[\"\'](?:shortcut )?icon[\"\'])[^>]*>', "", html, flags=re.I)
    html, count = re.subn(r"<title>.*?</title>", "", html, flags=re.S)
    if count != 1 or "</head>" not in html:
        raise RuntimeError("Unexpected Streamlit HTML template")
    html = re.sub(r'<html\b[^>]*>', '<html lang="fr-CA">', html, count=1)
    html = html.replace("</head>", "<!-- cenlio-seo -->" + metadata() + "</head>", 1)
    index.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    prepare_streamlit()