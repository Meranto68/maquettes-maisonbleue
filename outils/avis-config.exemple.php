<?php
/*
 * Copier ce fichier sous le nom avis-config.php (même dossier) et y mettre la clé Google.
 * avis-config.php ne doit jamais être publié sur GitHub (il est dans .gitignore).
 *
 * Obtenir la clé (gratuit à ce volume : 1 appel par jour) :
 *   1. https://console.cloud.google.com → créer un projet
 *   2. « API et services » → activer « Places API (New) »
 *   3. « Identifiants » → « Créer une clé API »
 *   4. Restreindre la clé à « Places API (New) »
 *      (et, si possible, à l'adresse IP de l'hébergement OVH)
 */
return [
    'cle'       => 'COLLER-ICI-LA-CLE-GOOGLE',
    'place_id'  => '',   // facultatif : identifiant Google de la clinique ; vide = recherche par nom et adresse
    'recherche' => 'Clinique Vétérinaire de la Maison Bleue, 10 Faubourg de Mulhouse, Altkirch',
];
