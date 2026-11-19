<?php
/*
 * Formulaire de contact du site → mail à la clinique.
 * Fonctionne tel quel sur un hébergement mutualisé OVH (fonction mail() de PHP).
 * Seul réglage possible : les deux adresses ci-dessous.
 */
const DESTINATAIRE = 'contact@clinique-maisonbleue.com';     // qui reçoit les messages
const EXPEDITEUR   = 'site@clinique-maisonbleue.com';        // doit être une adresse du domaine (exigence OVH)

$ajax = ($_POST['ajax'] ?? '') === '1';
function repondre($ok, $erreur = '') {
    global $ajax;
    if ($ajax) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => $ok, 'erreur' => $erreur]);
    } else {   // navigateur sans JavaScript : retour à la page
        $retour = $_SERVER['HTTP_REFERER'] ?? './';
        if (parse_url($retour, PHP_URL_HOST) !== explode(':', $_SERVER['HTTP_HOST'] ?? '')[0]) $retour = './';
        $retour = strtok($retour, '?#');
        header('Location: ' . $retour . '?contact=' . ($ok ? 'envoye' : 'erreur') . '#contact', true, 303);
    }
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') repondre(false, 'methode');

// Anti-robots : champ piège invisible, et envoi trop rapide après l'ouverture de la page
if (!empty($_POST['site_web'])) repondre(true);
$t = (int)($_POST['t'] ?? 0);
if ($t && (time() - $t) < 3) repondre(true);

$ligne = fn($v, $max) => trim(mb_substr(str_replace(["\r", "\n"], ' ', (string)$v), 0, $max));
$nom       = $ligne($_POST['nom'] ?? '', 100);
$email     = $ligne($_POST['email'] ?? '', 150);
$telephone = $ligne($_POST['telephone'] ?? '', 40);
$animal    = $ligne($_POST['animal'] ?? '', 100);
$message   = trim(mb_substr((string)($_POST['message'] ?? ''), 0, 5000));
$langue    = $ligne($_POST['langue'] ?? 'fr', 10);

if ($nom === '' || $message === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) repondre(false, 'champs');

// Limite : un message par minute et par adresse IP
$ip = $_SERVER['REMOTE_ADDR'] ?? '';
$verrou = sys_get_temp_dir() . '/mb-contact-' . md5($ip);
if (is_file($verrou) && time() - filemtime($verrou) < 60) repondre(false, 'trop');
@touch($verrou);

$sujet = 'Message du site — ' . $nom;
$corps = "Nouveau message reçu depuis le site de la clinique.\n\n"
       . "Nom : $nom\nE-mail : $email\n"
       . ($telephone !== '' ? "Téléphone : $telephone\n" : '')
       . ($animal !== '' ? "Animal : $animal\n" : '')
       . "Langue du site : $langue\n\n"
       . "Message :\n$message\n\n"
       . "—\nPour répondre, utilisez simplement « Répondre » : le message ira à $email.";
$entetes = [
    'From: Site Maison Bleue <' . EXPEDITEUR . '>',
    'Reply-To: ' . $nom . ' <' . $email . '>',
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
];
$envoye = mail(DESTINATAIRE, '=?UTF-8?B?' . base64_encode($sujet) . '?=', $corps, implode("\r\n", $entetes), '-f' . EXPEDITEUR);
repondre($envoye, $envoye ? '' : 'envoi');
