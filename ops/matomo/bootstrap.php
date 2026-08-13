<?php

/**
 * Deployed to /var/www/html/bootstrap.php on the Matomo host (Liara app
 * didargold-fnebllvlkk, persistent disk). Matomo's index.php loads this
 * file natively when present.
 *
 * Why: Matomo core reads Bearer tokens only from HTTP_AUTHORIZATION
 * (core/Request/AuthenticationToken.php), but the Authorization header
 * never reaches PHP here — verified stripped upstream of Apache (Liara
 * edge). Without this shim the McpServer plugin's Bearer auth always 401s.
 *
 * Fix: accept the token via X-Authorization (which proxies pass through)
 * and republish it where core looks. Plain Authorization is also copied
 * from Apache when it does arrive, so nothing breaks if the edge changes.
 */
if (empty($_SERVER['HTTP_AUTHORIZATION'])) {
    if (!empty($_SERVER['HTTP_X_AUTHORIZATION'])) {
        $_SERVER['HTTP_AUTHORIZATION'] = $_SERVER['HTTP_X_AUTHORIZATION'];
    } elseif (function_exists('apache_request_headers')) {
        $headers = apache_request_headers();
        if (!empty($headers['Authorization'])) {
            $_SERVER['HTTP_AUTHORIZATION'] = $headers['Authorization'];
        }
    }
}

// TEMP diagnostic (removed once MCP auth is confirmed). Read-only: reports
// which auth header sources reached PHP, never the token value.
if (isset($_GET['__hdrprobe'])) {
    header('Content-Type: application/json');
    $ah = function_exists('apache_request_headers') ? apache_request_headers() : [];
    $auth = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    echo json_encode([
        'auth_prefix' => substr($auth, 0, 7),          // expect "Bearer "
        'auth_len' => strlen($auth),
        'starts_with_bearer' => strpos($auth, 'Bearer ') === 0,
        'apache_header_names' => array_keys($ah),
    ]);
    exit;
}
