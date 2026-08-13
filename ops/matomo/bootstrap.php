<?php

/**
 * Deployed to /var/www/html/bootstrap.php on the Matomo host (Liara app
 * didargold-fnebllvlkk, persistent disk). Matomo's index.php loads this
 * file natively when present.
 *
 * Why: Apache mod_php drops non-Basic Authorization headers from $_SERVER,
 * but Matomo core reads Bearer tokens only from HTTP_AUTHORIZATION
 * (core/Request/AuthenticationToken.php). Without this shim the McpServer
 * plugin's Bearer auth always 401s. Copy the header over when Apache has it.
 */
if (empty($_SERVER['HTTP_AUTHORIZATION']) && function_exists('apache_request_headers')) {
    $headers = apache_request_headers();
    if (!empty($headers['Authorization'])) {
        $_SERVER['HTTP_AUTHORIZATION'] = $headers['Authorization'];
    }
}
