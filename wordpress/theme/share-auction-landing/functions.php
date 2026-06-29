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
    wp_enqueue_style('sal-style', get_stylesheet_uri(), [], '1.0.4');
    wp_enqueue_script('sal-lucide', 'https://unpkg.com/lucide@latest/dist/umd/lucide.min.js', [], null, true);
    wp_enqueue_script('sal-main', get_template_directory_uri() . '/main.js', ['sal-lucide'], '1.0.4', true);
}
add_action('wp_enqueue_scripts', 'sal_assets');

function sal_force_front_page_template(string $template): string {
    if (is_front_page()) {
        $front = get_template_directory() . '/front-page.php';
        if (file_exists($front)) {
            return $front;
        }
    }

    return $template;
}
add_filter('template_include', 'sal_force_front_page_template', 100);

function sal_front_title(): string {
    return '지분경매·공유물 지분 매입 상담 | 상속지분·토지지분 정리 - 지분경매 매입센터';
}

function sal_front_description(): string {
    return '공유물 지분 매입, 상속지분 정리, 토지·아파트·상가 지분경매 낙찰 전후 상담을 등기부와 사건자료 기준으로 검토합니다.';
}

function sal_filter_front_title(string $title): string {
    return is_front_page() ? sal_front_title() : $title;
}
add_filter('pre_get_document_title', 'sal_filter_front_title', 999);
add_filter('rank_math/frontend/title', 'sal_filter_front_title', 999);
add_filter('rank_math/opengraph/facebook/title', 'sal_filter_front_title', 999);
add_filter('rank_math/opengraph/twitter/title', 'sal_filter_front_title', 999);

function sal_filter_document_title_parts(array $parts): array {
    if (is_front_page()) {
        $parts['title'] = sal_front_title();
        unset($parts['tagline']);
        unset($parts['site']);
    }

    return $parts;
}
add_filter('document_title_parts', 'sal_filter_document_title_parts', 999);

function sal_filter_front_description(string $description): string {
    return is_front_page() ? sal_front_description() : $description;
}
add_filter('rank_math/frontend/description', 'sal_filter_front_description', 999);
add_filter('rank_math/opengraph/facebook/description', 'sal_filter_front_description', 999);
add_filter('rank_math/opengraph/twitter/description', 'sal_filter_front_description', 999);

function sal_filter_front_site_name(string $site_name): string {
    return is_front_page() ? '지분경매 매입센터' : $site_name;
}
add_filter('rank_math/opengraph/site_name', 'sal_filter_front_site_name', 999);

function sal_filter_rank_math_schema(array $data): array {
    if (!is_front_page()) {
        return $data;
    }

    foreach ($data as &$item) {
        if (!is_array($item)) {
            continue;
        }

        $type = $item['@type'] ?? '';
        $types = is_array($type) ? $type : [$type];
        if (array_intersect($types, ['WebPage', 'WebSite', 'Organization', 'Person'])) {
            $item['name'] = '지분경매 매입센터';
            $item['description'] = sal_front_description();
        }
        if (in_array('WebPage', $types, true)) {
            $item['name'] = sal_front_title();
        }
    }
    unset($item);

    return $data;
}
add_filter('rank_math/json_ld', 'sal_filter_rank_math_schema', 999);

function sal_start_front_cleanup_buffer(): void {
    if (!is_front_page() || is_admin() || wp_doing_ajax() || wp_is_json_request() || is_feed()) {
        return;
    }

    ob_start('sal_clean_front_html');
}
add_action('template_redirect', 'sal_start_front_cleanup_buffer', 0);

function sal_clean_front_html(string $html): string {
    $html = str_replace('content="공장경매"', 'content="지분경매 매입센터"', $html);
    $html = str_replace(' - FactoryPro', ' - 지분경매 매입센터', $html);
    $html = str_replace('content="FactoryPro"', 'content="지분경매 매입센터"', $html);
    $html = str_replace('>FactoryPro<', '>지분경매 매입센터<', $html);
    $html = str_replace(
        'https://factorypro.co.kr/wp-content/uploads/2018/11/factory.jpg',
        get_template_directory_uri() . '/assets/hero-consultation.png',
        $html
    );

    return $html;
}

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
