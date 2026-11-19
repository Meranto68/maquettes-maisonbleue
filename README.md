# Clinique Vétérinaire de la Maison Bleue — nouveau site

Maquette du nouveau site (temporaire, non indexée par Google).

## Pages
- `index.html` — page d'accueil en français (**c'est le fichier à modifier**)
- `en/index.html`, `de/index.html` — anglais et allemand suisse (générés, ne pas modifier à la main)
- `mentions-legales.html`, `confidentialite.html`, `conditions-generales.html` — pages légales (générées)

## Modifier le site
1. Changer le texte français dans `index.html`.
2. Changer les traductions dans `outils/traductions.json` (même clé que l'attribut `data-i18n`).
3. Lancer : `python3 outils/build.py` (régénère EN, DE, pages légales, sitemap, FAQ Google).

## Mise en ligne sur www.clinique-maisonbleue.com
1. Dans `outils/build.py`, passer `EN_LIGNE = True`, puis lancer `python3 outils/build.py`.
2. Mettre tous les fichiers chez l'hébergeur, à la racine du domaine.
3. Dans Google Search Console : ajouter le domaine et envoyer `sitemap.xml`.
4. Compléter et vérifier la fiche Google Business Profile de la clinique (horaires, photos, lien du site).
5. Remplir les zones surlignées en jaune `[...]` dans les pages légales.


## Formulaire de contact
`contact.php` envoie les messages par e-mail à la clinique (fonction mail() de l'hébergement OVH, rien à configurer).
- Adresses réglables en haut du fichier : `DESTINATAIRE` (qui reçoit) et `EXPEDITEUR` (contact@clinique-maisonbleue.com, adresse du domaine).
- Protections : champ piège anti-robots, envoi trop rapide refusé, un message par minute et par adresse IP.
- Sur GitHub Pages (pas de PHP), le formulaire affiche l'adresse e-mail de la clinique à la place.
