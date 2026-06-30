<?php
/**
 * Plugin Name: Jauction Lead Mail Bridge
 * Description: Receives Jauction landing leads through a protected REST endpoint and sends email through wp_mail/WP Mail SMTP.
 * Version: 1.0.0
 * Author: Jauction
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Update URI: false
 */

if (!defined('ABSPATH')) {
    exit;
}

const JAUCTION_LEAD_MAIL_TO = 'jauction_lead_mail_to';
const JAUCTION_LEAD_MAIL_TOKEN = 'jauction_lead_mail_token';
const JAUCTION_LEAD_MAIL_FROM_NAME = 'jauction_lead_mail_from_name';
const JAUCTION_LEAD_MAIL_LAST_STATUS = 'jauction_lead_mail_last_status';
const JAUCTION_LEAD_MAIL_LAST_ERROR = 'jauction_lead_mail_last_error';
const JAUCTION_LEAD_MAIL_LAST_AT = 'jauction_lead_mail_last_at';

register_activation_hook(__FILE__, 'jauction_lead_mail_ensure_defaults');
add_action('plugins_loaded', 'jauction_lead_mail_ensure_defaults');
add_action('rest_api_init', 'jauction_lead_mail_register_routes');
add_action('admin_menu', 'jauction_lead_mail_admin_menu');

function jauction_lead_mail_ensure_defaults(): void
{
    if (!get_option(JAUCTION_LEAD_MAIL_TO)) {
        update_option(JAUCTION_LEAD_MAIL_TO, jauction_lead_mail_default_recipient());
    }
    if (!get_option(JAUCTION_LEAD_MAIL_FROM_NAME)) {
        update_option(JAUCTION_LEAD_MAIL_FROM_NAME, jauction_lead_mail_default_from_name());
    }
    $external_token = jauction_lead_mail_external_token();
    if ($external_token !== '') {
        if ((string) get_option(JAUCTION_LEAD_MAIL_TOKEN, '') !== $external_token) {
            update_option(JAUCTION_LEAD_MAIL_TOKEN, $external_token);
        }
    } elseif (!get_option(JAUCTION_LEAD_MAIL_TOKEN)) {
        update_option(JAUCTION_LEAD_MAIL_TOKEN, wp_generate_password(40, false, false));
    }
}

function jauction_lead_mail_default_recipient(): string
{
    $configured = getenv('INQUIRY_RECIPIENT_EMAIL');
    return sanitize_text_field($configured ?: get_option('admin_email'));
}

function jauction_lead_mail_default_from_name(): string
{
    $configured = getenv('SMTP_FROM_NAME');
    return sanitize_text_field($configured ?: 'Jauction 상담 접수');
}

function jauction_lead_mail_external_token(): string
{
    $token = getenv('JAUCTION_LEAD_MAIL_TOKEN');
    if (is_string($token) && $token !== '') {
        return sanitize_text_field($token);
    }

    $token_file = trailingslashit(WPMU_PLUGIN_DIR) . 'jauction-lead-mail-bridge-token.php';
    if (is_readable($token_file)) {
        $loaded = include $token_file;
        if (is_string($loaded) && $loaded !== '') {
            return sanitize_text_field($loaded);
        }
    }

    return '';
}

function jauction_lead_mail_register_routes(): void
{
    register_rest_route('jauction/v1', '/lead', [
        'methods' => WP_REST_Server::CREATABLE,
        'callback' => 'jauction_lead_mail_rest_lead',
        'permission_callback' => 'jauction_lead_mail_permission',
    ]);
}

function jauction_lead_mail_permission(WP_REST_Request $request)
{
    $configured = jauction_lead_mail_current_token();
    if ($configured === '') {
        return new WP_Error('jauction_token_missing', 'Bridge token is not configured.', ['status' => 403]);
    }

    $received = jauction_lead_mail_request_token($request);
    if ($received === '' || !hash_equals($configured, $received)) {
        return new WP_Error('jauction_forbidden', 'Invalid bridge token.', ['status' => 403]);
    }

    return true;
}

function jauction_lead_mail_request_token(WP_REST_Request $request): string
{
    $token = (string) $request->get_header('x-jauction-token');
    if ($token !== '') {
        return trim($token);
    }

    $authorization = (string) $request->get_header('authorization');
    if (preg_match('/^Bearer\s+(.+)$/i', $authorization, $matches)) {
        return trim($matches[1]);
    }

    return '';
}

function jauction_lead_mail_current_token(): string
{
    return jauction_lead_mail_external_token() ?: (string) get_option(JAUCTION_LEAD_MAIL_TOKEN, '');
}

function jauction_lead_mail_rest_lead(WP_REST_Request $request)
{
    $params = $request->get_json_params();
    if (!is_array($params)) {
        return new WP_Error('jauction_invalid_json', 'Invalid JSON payload.', ['status' => 400]);
    }

    $lead = jauction_lead_mail_sanitize_lead($params);
    if ($lead['event'] !== '' && $lead['event'] !== 'lead.created') {
        return new WP_Error('jauction_invalid_event', 'Unsupported event.', ['status' => 400]);
    }
    if ($lead['name'] === '' || $lead['phone'] === '') {
        return new WP_Error('jauction_required_field', 'Name and phone are required.', ['status' => 400]);
    }

    $result = jauction_lead_mail_send($lead);
    if (!$result['ok']) {
        return new WP_REST_Response([
            'ok' => false,
            'mail_sent' => false,
            'error' => $result['error'],
        ], 500);
    }

    return new WP_REST_Response([
        'ok' => true,
        'mail_sent' => true,
    ], 200);
}

function jauction_lead_mail_sanitize_lead(array $params): array
{
    return [
        'event' => jauction_lead_mail_clean($params['event'] ?? '', 80),
        'id' => jauction_lead_mail_clean($params['id'] ?? '', 80),
        'created_at' => jauction_lead_mail_clean($params['created_at'] ?? '', 120),
        'name' => jauction_lead_mail_clean($params['name'] ?? '', 120),
        'phone' => jauction_lead_mail_clean($params['phone'] ?? '', 80),
        'type' => jauction_lead_mail_clean($params['type'] ?? '', 160),
        'case_or_address' => jauction_lead_mail_clean($params['case_or_address'] ?? '', 500),
        'share' => jauction_lead_mail_clean($params['share'] ?? '', 80),
        'owners' => jauction_lead_mail_clean($params['owners'] ?? '', 80),
        'status' => jauction_lead_mail_clean($params['status'] ?? '', 160),
        'message' => jauction_lead_mail_clean_textarea($params['message'] ?? '', 2000),
        'source' => esc_url_raw((string) ($params['source'] ?? '')),
    ];
}

function jauction_lead_mail_clean($value, int $limit): string
{
    return jauction_lead_mail_limit(sanitize_text_field((string) $value), $limit);
}

function jauction_lead_mail_clean_textarea($value, int $limit): string
{
    return jauction_lead_mail_limit(sanitize_textarea_field((string) $value), $limit);
}

function jauction_lead_mail_limit(string $value, int $limit): string
{
    if (function_exists('mb_substr')) {
        return mb_substr($value, 0, $limit);
    }
    return substr($value, 0, $limit);
}

function jauction_lead_mail_send(array $lead): array
{
    $to = jauction_lead_mail_recipients();
    if (!$to) {
        return jauction_lead_mail_record_result(false, 'recipient_not_configured');
    }

    $subject = sprintf('[Jauction 상담] %s / %s', $lead['type'] ?: '상담', $lead['name']);
    $body = jauction_lead_mail_body($lead);
    $headers = [
        'Content-Type: text/plain; charset=UTF-8',
        'X-Jauction-Mail: lead-notification',
    ];

    $GLOBALS['jauction_lead_mail_last_wp_error'] = '';
    add_action('wp_mail_failed', 'jauction_lead_mail_capture_wp_error');
    add_filter('wp_mail_from_name', 'jauction_lead_mail_from_name', 20);

    $sent = wp_mail($to, $subject, $body, $headers);

    remove_filter('wp_mail_from_name', 'jauction_lead_mail_from_name', 20);
    remove_action('wp_mail_failed', 'jauction_lead_mail_capture_wp_error');

    if (!$sent) {
        $error = (string) ($GLOBALS['jauction_lead_mail_last_wp_error'] ?? '');
        return jauction_lead_mail_record_result(false, $error ?: 'wp_mail_returned_false');
    }

    return jauction_lead_mail_record_result(true, '');
}

function jauction_lead_mail_body(array $lead): string
{
    return implode("\n", [
        'Jauction 새 상담이 접수되었습니다.',
        '',
        '접수번호: ' . ($lead['id'] ?: '-'),
        '접수시각: ' . ($lead['created_at'] ?: current_time('mysql')),
        '이름: ' . ($lead['name'] ?: '-'),
        '연락처: ' . ($lead['phone'] ?: '-'),
        '상담유형: ' . ($lead['type'] ?: '-'),
        '주소/사건번호: ' . ($lead['case_or_address'] ?: '-'),
        '지분율: ' . ($lead['share'] ?: '-'),
        '공유자 수: ' . ($lead['owners'] ?: '-'),
        '현재 상태: ' . ($lead['status'] ?: '-'),
        '출처: ' . ($lead['source'] ?: '-'),
        '',
        '상담 내용',
        $lead['message'] ?: '-',
    ]);
}

function jauction_lead_mail_recipients(): array
{
    $raw = (string) get_option(JAUCTION_LEAD_MAIL_TO, get_option('admin_email'));
    $parts = preg_split('/[\s,;]+/', $raw);
    $emails = [];
    foreach ($parts as $part) {
        $email = sanitize_email($part);
        if ($email && is_email($email)) {
            $emails[] = $email;
        }
    }
    return array_values(array_unique($emails));
}

function jauction_lead_mail_from_name(string $name): string
{
    $configured = sanitize_text_field((string) get_option(JAUCTION_LEAD_MAIL_FROM_NAME, 'Jauction 상담 접수'));
    return $configured ?: $name;
}

function jauction_lead_mail_capture_wp_error(WP_Error $error): void
{
    $GLOBALS['jauction_lead_mail_last_wp_error'] = $error->get_error_message();
}

function jauction_lead_mail_record_result(bool $ok, string $error): array
{
    update_option(JAUCTION_LEAD_MAIL_LAST_STATUS, $ok ? 'sent' : 'failed');
    update_option(JAUCTION_LEAD_MAIL_LAST_ERROR, $error);
    update_option(JAUCTION_LEAD_MAIL_LAST_AT, current_time('mysql'));

    return [
        'ok' => $ok,
        'error' => $error,
    ];
}

function jauction_lead_mail_admin_menu(): void
{
    add_options_page(
        'Jauction Mail Bridge',
        'Jauction Mail',
        'manage_options',
        'jauction-lead-mail',
        'jauction_lead_mail_admin_page'
    );
}

function jauction_lead_mail_admin_page(): void
{
    if (!current_user_can('manage_options')) {
        return;
    }

    jauction_lead_mail_handle_admin_post();

    $endpoint = esc_url(rest_url('jauction/v1/lead'));
    $token = esc_html(jauction_lead_mail_current_token());
    $to = esc_attr((string) get_option(JAUCTION_LEAD_MAIL_TO, get_option('admin_email')));
    $from_name = esc_attr((string) get_option(JAUCTION_LEAD_MAIL_FROM_NAME, 'Jauction 상담 접수'));
    $last_status = esc_html((string) get_option(JAUCTION_LEAD_MAIL_LAST_STATUS, '-'));
    $last_error = esc_html((string) get_option(JAUCTION_LEAD_MAIL_LAST_ERROR, ''));
    $last_at = esc_html((string) get_option(JAUCTION_LEAD_MAIL_LAST_AT, '-'));
    ?>
    <div class="wrap">
        <h1>Jauction Mail Bridge</h1>
        <?php settings_errors('jauction_lead_mail'); ?>
        <p>Cloudflare Worker 상담 접수를 WordPress <code>wp_mail()</code>로 전달합니다. WP Mail SMTP가 설정되어 있으면 그 발송 경로를 그대로 사용합니다.</p>

        <table class="widefat striped" style="max-width: 980px;">
            <tbody>
                <tr>
                    <th scope="row" style="width: 220px;">REST Endpoint</th>
                    <td><code><?php echo $endpoint; ?></code></td>
                </tr>
                <tr>
                    <th scope="row">Worker Secret Token</th>
                    <td><code style="word-break: break-all;"><?php echo $token; ?></code></td>
                </tr>
                <tr>
                    <th scope="row">마지막 발송 상태</th>
                    <td><?php echo $last_status; ?> / <?php echo $last_at; ?><?php echo $last_error ? ' / ' . $last_error : ''; ?></td>
                </tr>
            </tbody>
        </table>

        <form method="post" style="max-width: 760px; margin-top: 24px;">
            <?php wp_nonce_field('jauction_lead_mail_save'); ?>
            <input type="hidden" name="jauction_lead_mail_action" value="save">
            <table class="form-table" role="presentation">
                <tr>
                    <th scope="row"><label for="jauction_lead_mail_to">수신 이메일</label></th>
                    <td>
                        <input name="jauction_lead_mail_to" id="jauction_lead_mail_to" type="text" class="regular-text" value="<?php echo $to; ?>">
                        <p class="description">여러 개는 쉼표로 구분합니다.</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="jauction_lead_mail_from_name">발신자 이름</label></th>
                    <td>
                        <input name="jauction_lead_mail_from_name" id="jauction_lead_mail_from_name" type="text" class="regular-text" value="<?php echo $from_name; ?>">
                        <p class="description">발신 주소는 WP Mail SMTP 설정을 따릅니다.</p>
                    </td>
                </tr>
            </table>
            <?php submit_button('설정 저장'); ?>
        </form>

        <form method="post" style="display: inline-block; margin-right: 8px;">
            <?php wp_nonce_field('jauction_lead_mail_test'); ?>
            <input type="hidden" name="jauction_lead_mail_action" value="test">
            <?php submit_button('테스트 메일 보내기', 'secondary', 'submit', false); ?>
        </form>

        <form method="post" style="display: inline-block;">
            <?php wp_nonce_field('jauction_lead_mail_rotate'); ?>
            <input type="hidden" name="jauction_lead_mail_action" value="rotate">
            <?php submit_button('토큰 재발급', 'secondary', 'submit', false); ?>
        </form>
    </div>
    <?php
}

function jauction_lead_mail_handle_admin_post(): void
{
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        return;
    }

    $action = sanitize_text_field((string) ($_POST['jauction_lead_mail_action'] ?? ''));
    if ($action === 'save') {
        check_admin_referer('jauction_lead_mail_save');
        update_option(JAUCTION_LEAD_MAIL_TO, sanitize_text_field((string) ($_POST['jauction_lead_mail_to'] ?? '')));
        update_option(JAUCTION_LEAD_MAIL_FROM_NAME, sanitize_text_field((string) ($_POST['jauction_lead_mail_from_name'] ?? '')));
        add_settings_error('jauction_lead_mail', 'saved', '설정을 저장했습니다.', 'updated');
    } elseif ($action === 'rotate') {
        check_admin_referer('jauction_lead_mail_rotate');
        update_option(JAUCTION_LEAD_MAIL_TOKEN, wp_generate_password(40, false, false));
        add_settings_error('jauction_lead_mail', 'rotated', '토큰을 재발급했습니다. Worker secret도 새 토큰으로 다시 설정해야 합니다.', 'updated');
    } elseif ($action === 'test') {
        check_admin_referer('jauction_lead_mail_test');
        $result = jauction_lead_mail_send([
            'event' => 'lead.created',
            'id' => 'wp-test',
            'created_at' => current_time('mysql'),
            'name' => '알림 점검',
            'phone' => '0000000000',
            'type' => '테스트',
            'case_or_address' => 'WordPress 관리자 테스트',
            'share' => '-',
            'owners' => '-',
            'status' => '테스트',
            'message' => 'WP Mail SMTP 발송 경로가 정상인지 확인하는 테스트입니다.',
            'source' => admin_url('options-general.php?page=jauction-lead-mail'),
        ]);
        if ($result['ok']) {
            add_settings_error('jauction_lead_mail', 'test_sent', '테스트 메일을 보냈습니다.', 'updated');
        } else {
            add_settings_error('jauction_lead_mail', 'test_failed', '테스트 메일 발송 실패: ' . esc_html($result['error']), 'error');
        }
    }
}
