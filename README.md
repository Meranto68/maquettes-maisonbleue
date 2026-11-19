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

## Note Google (avis clients)
La note s'affiche toute seule sous les photos de l'équipe, en haut de la page d'accueil. Elle est mise à jour une fois par jour par `avis.php` (PHP, hébergement OVH).
1. Créer une clé Google « Places API (New) » (voir `outils/avis-config.exemple.php`).
2. Copier `outils/avis-config.exemple.php` en `outils/avis-config.php` **directement chez OVH** et y coller la clé.
   Ce fichier ne doit jamais aller sur GitHub.
3. Tant qu'il n'y a pas de clé (ou sur GitHub Pages, qui ne gère pas le PHP), l'encart reste masqué.
   Aperçu sur la maquette : ajouter `?apercu-avis` à l'adresse (note d'exemple).
