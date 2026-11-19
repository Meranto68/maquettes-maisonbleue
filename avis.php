<?php
/*
 * Note Google de la clinique, servie au site en JSON.
 * - Interroge Google (Places API) au maximum une fois toutes les 24 h.
 * - Garde la dernière note en cache : si Google ne répond pas, l'ancienne note reste affichée.
 * - La clé Google reste sur le serveur (fichier outils/avis-config.php), jamais visible des visiteurs.
 * Fonctionne sur un hébergement mutualisé OVH (PHP 7.4 ou plus).
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=3600');
header('X-Content-Type-Options: nosniff');

$dossier = __DIR__ . '/outils';
$cache   = $dossier . '/avis-cache.json';
$config  = $dossier . '/avis-config.php';
$duree   = 24 * 3600;

function sortir($json) { echo $json ?: '{}'; exit; }

$enCache = is_file($cache) ? file_get_contents($cache) : '';
if ($enCache && (time() - filemtime($cache)) < $duree) sortir($enCache);
if (!is_file($config)) sortir($enCache);

$cfg = require $config;
$cle = $cfg['cle'] ?? '';
if (!$cle) sortir($enCache);

function appel($url, $cle, $champs, $corps = null) {
    $entetes = ['X-Goog-Api-Key: ' . $cle, 'X-Goog-FieldMask: ' . $champs, 'Content-Type: application/json'];
    if (function_exists('curl_init')) {
        $c = curl_init($url);
        curl_setopt_array($c, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 8, CURLOPT_HTTPHEADER => $entetes]);
        if ($corps !== null) { curl_setopt($c, CURLOPT_POST, true); curl_setopt($c, CURLOPT_POSTFIELDS, $corps); }
        $r = curl_exec($c); $code = curl_getinfo($c, CURLINFO_HTTP_CODE); curl_close($c);
    } else {
        $ctx = stream_context_create(['http' => ['method' => $corps === null ? 'GET' : 'POST', 'header' => implode("\r\n", $entetes),
            'content' => $corps ?? '', 'timeout' => 8, 'ignore_errors' => true]]);
        $r = @file_get_contents($url, false, $ctx); $code = 0;
        if (isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m)) $code = (int)$m[1];
    }
    return ($r !== false && $code === 200) ? json_decode($r, true) : null;
}

$champs = 'id,rating,userRatingCount,googleMapsUri';
if (!empty($cfg['place_id'])) {
    $lieu = appel('https://places.googleapis.com/v1/places/' . rawurlencode($cfg['place_id']), $cle, $champs);
} else {
    $res  = appel('https://places.googleapis.com/v1/places:searchText', $cle, implode(',', array_map(fn($c) => 'places.' . $c, explode(',', $champs))),
        json_encode(['textQuery' => $cfg['recherche'] ?? 'Clinique Vétérinaire de la Maison Bleue, 10 Faubourg de Mulhouse, Altkirch', 'languageCode' => 'fr']));
    $lieu = $res['places'][0] ?? null;
}

if (!$lieu || !isset($lieu['rating'])) {
    if ($enCache) touch($cache);          // on réessaiera dans 24 h, l'ancienne note reste affichée
    sortir($enCache);
}

$json = json_encode([
    'note'   => round((float)$lieu['rating'], 1),
    'nombre' => (int)($lieu['userRatingCount'] ?? 0),
    'lien'   => $lieu['googleMapsUri'] ?? '',
    'avis'   => isset($lieu['id']) ? 'https://search.google.com/local/writereview?placeid=' . rawurlencode($lieu['id']) : '',
    'maj'    => date('c'),
], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
@file_put_contents($cache, $json, LOCK_EX);
sortir($json);
