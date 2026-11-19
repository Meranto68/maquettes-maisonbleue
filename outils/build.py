#!/usr/bin/env python3
"""
Génère le site à partir de la page française (index.html) :
  - en/index.html et de/index.html (traductions : outils/traductions.json)
  - les pages légales (mentions légales, confidentialité, conditions générales)
  - sitemap.xml, robots.txt, site.webmanifest
  - les données structurées FAQ (Google) dans chaque langue

Utilisation (depuis le dossier du site) :  python3 outils/build.py

MISE EN LIGNE : passer EN_LIGNE à True le jour où le site remplace l'ancien
sur www.clinique-maisonbleue.com. Tant que c'est False, Google n'indexe rien
(la maquette ne doit pas faire concurrence au vrai site).
"""
import json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

EN_LIGNE = False
SITE = "https://www.clinique-maisonbleue.com/"
RACINE = Path(__file__).resolve().parent.parent
ROBOTS = "index,follow,max-image-preview:large" if EN_LIGNE else "noindex,nofollow"
LANGUES = {"en": "en", "de": "de-CH"}

source = (RACINE / "index.html").read_text(encoding="utf-8")
trad = json.loads((RACINE / "outils" / "traductions.json").read_text(encoding="utf-8"))

# BeautifulSoup met les attributs SVG en minuscules : on rétablit leur casse.
CASSE = {"viewbox": "viewBox", "preserveaspectratio": "preserveAspectRatio", "<clippath": "<clipPath", "</clippath": "</clipPath"}
def propre(html):
    for a, b in CASSE.items():
        html = html.replace(a, b)
    return html

def fragment(html):
    return BeautifulSoup(html, "html.parser")

def taille_image(src):
    p = RACINE / src.split("?")[0]
    if p.exists() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        with Image.open(p) as im:
            return im.size
    return None

def corrige_tailles(soup):
    """Met width/height aux vraies proportions des images (évite les sauts de mise en page)."""
    for img in soup.find_all("img", src=True):
        t = taille_image(img["src"].replace("../", ""))
        if not t or not img.get("width") or not img.get("height"):
            continue
        w, h = int(img["width"]), int(img["height"])
        if abs(w / h - t[0] / t[1]) > 0.01:
            img["width"], img["height"] = str(w), str(round(w * t[1] / t[0]))

def faq_jsonld(soup):
    items = []
    for i in range(10):
        q, a = soup.find(attrs={"data-i18n": f"q{i}"}), soup.find(attrs={"data-i18n": f"a{i}"})
        if not q or not a:
            break
        items.append({"@type": "Question", "name": q.get_text(" ", strip=True),
                      "acceptedAnswer": {"@type": "Answer", "text": a.get_text(" ", strip=True)}})
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items}, ensure_ascii=False, indent=2)

def remplace_ld_faq(html, contenu):
    return re.sub(r'(<script type="application/ld\+json" id="ld-faq">)(.*?)(</script>)',
                  lambda m: m.group(1) + contenu + m.group(3), html, flags=re.S)

def prefixe(soup):
    """Les pages /en/ et /de/ sont un dossier plus bas : on ajoute ../ aux liens relatifs."""
    for tag in soup.find_all(["a", "link", "img", "script"]):
        for att in ("href", "src"):
            v = tag.get(att)
            if v and not re.match(r"^(https?:|#|mailto:|tel:|data:|/|\.\./)", v):
                tag[att] = "../" + (v[2:] if v.startswith("./") else v)
    for st in soup.find_all("style"):
        st.string = st.string.replace("url(fonts/", "url(../fonts/").replace("url(images/", "url(../images/")

manquantes = set()

# ---------- Pages traduites ----------
for code, html_lang in LANGUES.items():
    t = trad[code]
    soup = BeautifulSoup(source, "html.parser")
    soup.html["lang"] = html_lang
    for el in soup.find_all(attrs={"data-i18n": True}):
        k = el["data-i18n"]
        if k not in t:
            manquantes.add(f"{code}:{k}"); continue
        el.clear(); el.append(fragment(t[k]))
    for el in soup.find_all(attrs={"data-i18n-attr": True}):
        for paire in el["data-i18n-attr"].split(";"):
            att, k = paire.split(":", 1)
            if k not in t:
                manquantes.add(f"{code}:{k}"); continue
            el[att] = t[k] if att != "class" else t[k].split()
    for a in soup.select("#langues a"):
        if a.get("hreflang") == html_lang:
            a["aria-current"] = "page"
        elif a.has_attr("aria-current"):
            del a["aria-current"]
    soup.find("meta", attrs={"name": "robots"})["content"] = ROBOTS
    soup.find("script", id="ld-faq").string = faq_jsonld(soup)
    corrige_tailles(soup)
    prefixe(soup)
    out = RACINE / code / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(propre(str(soup)), encoding="utf-8")
    print("écrit", out.relative_to(RACINE))

if manquantes:
    sys.exit("Traductions manquantes : " + ", ".join(sorted(manquantes)))

# ---------- Page française : robots, FAQ Google, tailles d'images ----------
fr = re.sub(r'<meta name="robots" content="[^"]*" id="robots">', f'<meta name="robots" content="{ROBOTS}" id="robots">', source)
fr = remplace_ld_faq(fr, faq_jsonld(BeautifulSoup(fr, "html.parser")))
def fix_img(m):
    tag = m.group(0); s = re.search(r'src="([^"]+)"', tag); w = re.search(r'width="(\d+)"', tag); h = re.search(r'height="(\d+)"', tag)
    if not (s and w and h): return tag
    t = taille_image(s.group(1))
    if not t: return tag
    W, H = int(w.group(1)), int(h.group(1))
    if abs(W / H - t[0] / t[1]) > 0.01:
        tag = tag.replace(h.group(0), f'height="{round(W * t[1] / t[0])}"')
    return tag
fr = re.sub(r"<img\b[^>]*>", fix_img, fr)
if fr != source:
    (RACINE / "index.html").write_text(fr, encoding="utf-8")
    print("mis à jour index.html")

# ---------- Pages légales (en français) ----------
STYLE = """@font-face{font-family:'Barlow';font-weight:400;font-display:swap;src:url(fonts/barlow-latin-400-normal.woff2) format('woff2')}
@font-face{font-family:'Barlow';font-weight:600;font-display:swap;src:url(fonts/barlow-latin-600-normal.woff2) format('woff2')}
@font-face{font-family:'Barlow Semi Condensed';font-weight:600;font-display:swap;src:url(fonts/barlow-semi-condensed-latin-600-normal.woff2) format('woff2')}
:root{--bleu:#2b3990;--nuit:#1b2363;--facade:#5aa3dc;--brume:#f1f3f9;--papier:#fbfaf7;--encre:#1e1b18;--gris:#565c6c;--trait:#e2e5ee}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Barlow',system-ui,sans-serif;font-size:1.05rem;line-height:1.65;color:var(--encre);background:var(--papier)}
a{color:var(--bleu)}:focus-visible{outline:3px solid var(--facade);outline-offset:3px}
header{border-bottom:1px solid var(--trait);background:#fff}header .w{display:flex;align-items:center;justify-content:space-between;gap:16px;height:80px}
header img{height:56px;width:auto}header a.retour{font-weight:600;text-decoration:none}
.w{max-width:820px;margin:0 auto;padding:0 24px}main{padding:56px 0 80px}
h1,h2{font-family:'Barlow Semi Condensed',system-ui,sans-serif;font-weight:600;color:var(--bleu);line-height:1.15}
h1{font-size:clamp(2.1rem,4vw,2.8rem);margin-bottom:10px}h2{font-size:1.45rem;margin:40px 0 10px}
p,ul{margin-bottom:12px;color:#33363f}ul{padding-left:22px}li{margin-bottom:4px}
.maj{color:var(--gris);font-size:.95rem;margin-bottom:28px}
.bloc{background:#fff;border:1px solid var(--trait);border-radius:14px;padding:20px 24px;margin:14px 0}
.bloc p{margin-bottom:4px}
.a-completer{background:#fff3cd;border-radius:4px;padding:0 4px;color:#6b4b00}
nav.legal{display:flex;flex-wrap:wrap;gap:10px 20px;margin-top:48px;padding-top:20px;border-top:1px solid var(--trait)}
footer{background:var(--bleu);color:#d3d8f1;padding:26px 0;font-size:.9rem}footer a{color:#fff}"""

def page_legale(fichier, titre, description, corps):
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titre} | Clinique Vétérinaire de la Maison Bleue</title>
<meta name="description" content="{description}">
<meta name="robots" content="{ROBOTS}">
<link rel="canonical" href="{SITE}{fichier}">
<link rel="icon" href="favicon.ico" sizes="any"><link rel="apple-touch-icon" href="images/apple-touch-icon.png">
<meta name="theme-color" content="#2b3990">
<style>{STYLE}</style>
</head>
<body>
<header><div class="w"><a href="./"><img src="images/logo-bleu.png" alt="Clinique Vétérinaire de la Maison Bleue — accueil" width="600" height="460"></a><a class="retour" href="./">Retour au site</a></div></header>
<main><div class="w">
<h1>{titre}</h1>
<p class="maj">Dernière mise à jour : <span class="a-completer">[date de mise en ligne]</span></p>
{corps}
<nav class="legal" aria-label="Informations légales"><a href="mentions-legales.html">Mentions légales</a><a href="confidentialite.html">Confidentialité</a><a href="conditions-generales.html">Conditions générales de fonctionnement</a></nav>
</div></main>
<footer><div class="w">© Clinique Vétérinaire de la Maison Bleue · SELARL Grandjean · 10 Faubourg de Mulhouse, 68130 Altkirch · <a href="tel:+33389406606">03&nbsp;89&nbsp;40&nbsp;66&nbsp;06</a></div></footer>
</body>
</html>
"""
    (RACINE / fichier).write_text(html, encoding="utf-8")
    print("écrit", fichier)

AC = lambda s: f'<span class="a-completer">[{s}]</span>'

page_legale("mentions-legales.html", "Mentions légales",
"Mentions légales du site de la Clinique Vétérinaire de la Maison Bleue (SELARL Grandjean) à Altkirch.", f"""
<p>Conformément à l'article 6 de la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique, voici l'identité des intervenants du site www.clinique-maisonbleue.com.</p>

<h2>Éditeur du site</h2>
<div class="bloc">
<p><strong>SELARL Grandjean</strong> — Clinique Vétérinaire de la Maison Bleue</p>
<p>Société d'exercice libéral à responsabilité limitée au capital de 1 000 €</p>
<p>Siège : 10 Faubourg de Mulhouse, 68130 Altkirch, France</p>
<p>RCS Mulhouse 515 123 859 · SIRET 515 123 859 00016 · TVA intracommunautaire FR84 515 123 859</p>
<p>Téléphone : <a href="tel:+33389406606">03 89 40 66 06</a> · Courriel : <a href="mailto:contact@clinique-maisonbleue.com">contact@clinique-maisonbleue.com</a></p>
</div>
<p><strong>Directeur de la publication :</strong> Mathieu Grandjean, gérant.</p>

<h2>Profession réglementée</h2>
<p>Les vétérinaires de la clinique sont inscrits au tableau de l'Ordre national des vétérinaires, auprès du Conseil régional de l'Ordre des vétérinaires du Grand Est. Numéros d'inscription : {AC("à compléter pour chaque vétérinaire")}.</p>
<p>Ils exercent dans le respect du code de déontologie vétérinaire (articles R242-32 et suivants du code rural et de la pêche maritime), consultable sur <a href="https://www.legifrance.gouv.fr" rel="noopener">legifrance.gouv.fr</a> et sur le site de l'Ordre, <a href="https://www.veterinaire.fr" rel="noopener">veterinaire.fr</a>.</p>

<h2>Hébergement</h2>
<div class="bloc">
<p>{AC("nom de l'hébergeur du nouveau site — par exemple : OVH SAS, 2 rue Kellermann, 59100 Roubaix, France, www.ovhcloud.com")}</p>
</div>

<h2>Conception du site</h2>
<p>{AC("nom et coordonnées du concepteur du site")}</p>

<h2>Propriété intellectuelle</h2>
<p>L'ensemble du site (textes, photographies, logo, mise en page) est protégé par le droit d'auteur. Toute reproduction, totale ou partielle, est interdite sans l'autorisation écrite de la SELARL Grandjean. Crédits photos : {AC("à compléter")}.</p>

<h2>Responsabilité</h2>
<p>Les informations de ce site sont données à titre indicatif et ne remplacent pas une consultation vétérinaire. En cas d'urgence, appelez directement la clinique. La clinique s'efforce de tenir ces informations à jour mais ne peut garantir leur exhaustivité. Les liens vers d'autres sites (prise de rendez-vous en ligne, réseaux sociaux, cartes) relèvent de la responsabilité de leurs éditeurs.</p>

<h2>Médiation de la consommation</h2>
<p>En cas de litige non résolu avec la clinique, vous pouvez saisir gratuitement le Médiateur de la consommation de la profession vétérinaire : <a href="https://www.mediateur-consommation-veterinaire.fr" rel="noopener">mediateur-consommation-veterinaire.fr</a> — CNOV, 34 rue Bréguet, 75011 Paris.</p>

<h2>Données personnelles</h2>
<p>Voir la page <a href="confidentialite.html">Confidentialité</a>.</p>
""")

page_legale("confidentialite.html", "Politique de confidentialité",
"Comment la Clinique Vétérinaire de la Maison Bleue protège vos données personnelles (RGPD).", f"""
<p>Cette page explique quelles données personnelles sont traitées lorsque vous utilisez ce site, et quels sont vos droits, conformément au Règlement général sur la protection des données (RGPD) et à la loi « Informatique et libertés ».</p>

<h2>Responsable du traitement</h2>
<p>SELARL Grandjean — Clinique Vétérinaire de la Maison Bleue, 10 Faubourg de Mulhouse, 68130 Altkirch. Contact : <a href="mailto:contact@clinique-maisonbleue.com">contact@clinique-maisonbleue.com</a>.</p>

<h2>Ce que fait ce site</h2>
<ul>
<li><strong>Formulaire de contact :</strong> les informations que vous saisissez (nom, e-mail, téléphone et animal si vous les indiquez, message) sont envoyées par e-mail à la clinique, uniquement pour vous répondre. Elles ne sont pas enregistrées sur le site et sont conservées dans la messagerie de la clinique le temps nécessaire au suivi de votre demande.</li>
<li><strong>Aucun compte, aucune mesure d'audience.</strong></li>
<li><strong>Aucun cookie</strong> n'est déposé par le site lui-même. Les polices de caractères sont hébergées sur le site, sans appel à un service extérieur.</li>
<li><strong>Carte Google Maps :</strong> elle ne se charge que si vous cliquez sur « Afficher la carte ». Google peut alors recevoir votre adresse IP et déposer des cookies, selon sa propre <a href="https://policies.google.com/privacy?hl=fr" rel="noopener">politique de confidentialité</a>.</li>
<li><strong>Prise de rendez-vous en ligne :</strong> le bouton ouvre le service MonRendezVousVéto, qui traite vos données pour gérer votre rendez-vous selon ses propres conditions.</li>
<li><strong>Facebook et Instagram :</strong> ce sont de simples liens. Aucune donnée n'est transmise à ces réseaux tant que vous ne cliquez pas.</li>
<li><strong>Hébergement :</strong> comme tout site, l'hébergeur enregistre des journaux techniques (adresse IP, date, page demandée) pour la sécurité du service, conservés {AC("durée selon l'hébergeur, en général 12 mois maximum")}.</li>
</ul>

<h2>Vos échanges avec la clinique</h2>
<p>Si vous nous écrivez ou nous appelez, les informations transmises servent uniquement à vous répondre et à assurer le suivi de votre animal. Les données des clients de la clinique (coordonnées, dossiers médicaux des animaux, facturation) sont traitées pour l'exécution des soins et pour respecter nos obligations légales, et ne sont jamais vendues. Elles sont conservées pendant la durée nécessaire à ces finalités et aux obligations comptables et réglementaires.</p>

<h2>Vos droits</h2>
<p>Vous disposez d'un droit d'accès, de rectification, d'effacement, de limitation, d'opposition et de portabilité de vos données. Pour les exercer, écrivez à <a href="mailto:contact@clinique-maisonbleue.com">contact@clinique-maisonbleue.com</a> ou à l'adresse de la clinique. Si vous estimez que vos droits ne sont pas respectés, vous pouvez adresser une réclamation à la CNIL : <a href="https://www.cnil.fr" rel="noopener">cnil.fr</a>.</p>
""")

page_legale("conditions-generales.html", "Conditions générales de fonctionnement",
"Conditions générales de fonctionnement de la Clinique Vétérinaire de la Maison Bleue à Altkirch : horaires, équipe, prestations, urgences, tarifs.", f"""
<p>Ces conditions générales de fonctionnement s'appliquent à toutes les prestations réalisées par la Clinique Vétérinaire de la Maison Bleue. Elles sont affichées à l'accueil et peuvent être remises sur simple demande. Toute prise en charge d'un animal vaut acceptation de ces conditions.</p>
<p class="bloc">{AC("Modèle préparé à partir des informations publiques de la clinique : à relire et valider par le Dr Grandjean avant la mise en ligne")}</p>

<h2>1. L'établissement</h2>
<p>Clinique Vétérinaire de la Maison Bleue, exploitée par la SELARL Grandjean, 10 Faubourg de Mulhouse, 68130 Altkirch. Téléphone : 03 89 40 66 06. Catégorie d'établissement de soins vétérinaires déclarée à l'Ordre : {AC("à confirmer — clinique vétérinaire")}.</p>

<h2>2. Horaires</h2>
<ul>
<li>Consultations sur rendez-vous du lundi au vendredi de 9h à 12h et de 14h à 19h, le samedi de 9h à 12h.</li>
<li>Rendez-vous par téléphone ou en ligne sur MonRendezVousVéto.</li>
</ul>

<h2>3. Équipe</h2>
<p><strong>Vétérinaires :</strong> Dr Mathieu Grandjean (gérant), Dr Pauline Cambier, Dr Jeanne Kleinmann, Dr Cheryl Lang, Dr Anne-Laure Piquard, Dr Laura Tafforeau. Diplômes et numéros d'inscription à l'Ordre : {AC("à compléter")}.</p>
<p><strong>Auxiliaires spécialisées vétérinaires :</strong> Marina Burgart, Amandine Hetzlen, Melina Hurth, Helen Lacan, Morgane Sauner, Anne-Sophie Simon.</p>

<h2>4. Prestations et espèces soignées</h2>
<p>Médecine générale et préventive, vaccination, chirurgie, radiologie, échographie, hospitalisation, analyses de laboratoire sur place, délivrance de médicaments vétérinaires dans le respect de la réglementation, vente d'aliments et de produits d'hygiène. La clinique soigne les chats, les chiens et les rongeurs (« NAC » : {AC("préciser les espèces acceptées")}).</p>

<h2>5. Permanence et continuité des soins</h2>
<p>Les urgences sont assurées 24h/24 : en dehors des heures d'ouverture, appelez le 03 89 40 66 06, un vétérinaire de permanence vous répond. {AC("préciser si la permanence est assurée par la clinique elle-même ou en partenariat avec un autre établissement")}.</p>

<h2>6. Surveillance des animaux hospitalisés</h2>
<p>Pendant les heures d'ouverture, les animaux hospitalisés sont surveillés par un vétérinaire ou une auxiliaire. En dehors de ces heures, {AC("préciser les modalités de surveillance de nuit")}.</p>

<h2>7. Tarifs et paiement</h2>
<ul>
<li>Les tarifs des actes les plus courants sont consultables à l'accueil. Un devis est remis sur demande, et systématiquement pour les actes importants.</li>
<li>Les honoraires sont payables à la fin de la consultation ou à la sortie de l'animal. Moyens de paiement acceptés : {AC("carte bancaire, espèces, chèque… à préciser")}.</li>
<li>Un acompte peut être demandé pour une hospitalisation ou une intervention chirurgicale.</li>
</ul>

<h2>8. Consentement éclairé et risque thérapeutique</h2>
<p>Le vétérinaire informe le propriétaire de l'état de santé de l'animal, des soins proposés, de leurs risques et de leur coût. Toute anesthésie ou intervention comporte un risque, dont le propriétaire est informé ; un consentement écrit peut lui être demandé.</p>

<h2>9. Décès de l'animal</h2>
<p>En cas de décès, la clinique peut organiser, à la demande du propriétaire, l'incinération collective ou individuelle de l'animal par une société spécialisée, aux frais du propriétaire. {AC("nom du prestataire")}.</p>

<h2>10. Responsabilité civile professionnelle</h2>
<p>La clinique est assurée pour sa responsabilité civile professionnelle auprès de {AC("nom et adresse de l'assureur")}.</p>

<h2>11. Litiges et médiation</h2>
<p>Toute réclamation peut être adressée à la clinique, qui s'engage à y répondre. À défaut d'accord, le client peut saisir gratuitement le Médiateur de la consommation de la profession vétérinaire : <a href="https://www.mediateur-consommation-veterinaire.fr" rel="noopener">mediateur-consommation-veterinaire.fr</a> (CNOV, 34 rue Bréguet, 75011 Paris). Le Conseil régional de l'Ordre des vétérinaires du Grand Est est compétent pour les questions déontologiques.</p>

<h2>12. Données personnelles</h2>
<p>Voir la page <a href="confidentialite.html">Confidentialité</a>.</p>
""")

# ---------- Sitemap, robots.txt, manifeste ----------
alt = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{SITE}{u}"/>' for h, u in [("fr", ""), ("en", "en/"), ("de-CH", "de/"), ("x-default", "")])
urls = "".join(f"\n  <url>\n    <loc>{SITE}{u}</loc>{alt}\n    <priority>1.0</priority>\n  </url>" for u in ["", "en/", "de/"])
urls += "".join(f"\n  <url>\n    <loc>{SITE}{u}</loc>\n    <priority>0.3</priority>\n  </url>" for u in ["mentions-legales.html", "confidentialite.html", "conditions-generales.html"])
(RACINE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">{urls}\n</urlset>\n', encoding="utf-8")
(RACINE / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n" if EN_LIGNE else
    "# Maquette : rien n'est indexé tant que EN_LIGNE = False dans outils/build.py\nUser-agent: *\nDisallow: /\n", encoding="utf-8")
(RACINE / "site.webmanifest").write_text(json.dumps({
    "name": "Clinique Vétérinaire de la Maison Bleue", "short_name": "Maison Bleue", "start_url": "./", "display": "browser",
    "background_color": "#fbfaf7", "theme_color": "#2b3990",
    "icons": [{"src": "images/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "images/icon-512.png", "sizes": "512x512", "type": "image/png"}]
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("écrit sitemap.xml, robots.txt, site.webmanifest")
