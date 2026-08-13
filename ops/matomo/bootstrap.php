<?php

/**
 * Deployed to /var/www/html/bootstrap.php on the Matomo host (Liara app
 * didargold-fnebllvlkk, persistent disk). Matomo's index.php loads this
 * file natively when present.
 *
 * Why: Matomo core reads Bearer tokens only from $_SERVER['HTTP_AUTHORIZATION']
 * (core/Request/AuthenticationToken.php), but Apache mod_php does NOT copy the
 * Authorization request header into $_SERVER (it's withheld unless CGIPassAuth
 * is set). apache_request_headers() still exposes it — as the lowercase key
 * 'authorization' behind Liara's HTTP/2 edge. Republish it under the key core
 * reads so the McpServer plugin's Bearer auth works.
 */
if (empty($_SERVER['HTTP_AUTHORIZATION']) && function_exists('apache_request_headers')) {
    foreach (apache_request_headers() as $name => $value) {
        if (strcasecmp($name, 'Authorization') === 0 && $value !== '') {
            $_SERVER['HTTP_AUTHORIZATION'] = $value;
            break;
        }
    }
}

if (isset($_GET['__hdrprobe'])) {
    header('Content-Type: application/json');
    $a = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    echo json_encode([
        'post_shim_bearer' => strpos($a, 'Bearer ') === 0,
        'post_shim_len' => strlen($a),
        'arh_exists' => function_exists('apache_request_headers'),
    ]);
    exit;
}
