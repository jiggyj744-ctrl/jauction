<?php
if (!defined('ABSPATH')) {
    exit;
}

function sal_setup(): void {
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('html5', ['search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script']);
}
add_action('after_setup_theme', 'sal_setup');

function sal_assets(): void {
    wp_enqueue_style('sal-style', get_stylesheet_uri(), [], '1.0.0');
    wp_enqueue_script('sal-lucide', 'https://unpkg.com/lucide@latest/dist/umd/lucide.min.js', [], null, true);
    wp_enqueue_script('sal-main', get_template_directory_uri() . '/main.js', ['sal-lucide'], '1.0.0', true);
}
add_action('wp_enqueue_scripts', 'sal_assets');

function sal_consultation_form(): void {
    if (!isset($_POST['sal_nonce']) || !wp_verify_nonce(sanitize_text_field(wp_unslash($_POST['sal_nonce'])), 'sal_consultation')) {
        wp_safe_redirect(home_url('/?consult=invalid#consult'));
        exit;
    }

    $fields = [
        'name' => '이름',
        'phone' => '연락처',
        'type' => '상담 유형',
        'case_or_address' => '주소 또는 사건번호',
        'share' => '지분율',
        'owners' => '공유자 수',
        'status' => '현재 상태',
        'message' => '상담 내용',
    ];

    $lines = [];
    foreach ($fields as $key => $label) {
        $value = isset($_POST[$key]) ? sanitize_textarea_field(wp_unslash($_POST[$key])) : '';
        $lines[] = $label . ': ' . $value;
    }

    $to = get_option('admin_email');
    $subject = '[지분경매 상담 접수] ' . (isset($_POST['name']) ? sanitize_text_field(wp_unslash($_POST['name'])) : '신규 문의');
    wp_mail($to, $subject, implode("\n", $lines));

    wp_safe_redirect(home_url('/?consult=sent#consult'));
    exit;
}
add_action('admin_post_nopriv_sal_consultation', 'sal_consultation_form');
add_action('admin_post_sal_consultation', 'sal_consultation_form');
