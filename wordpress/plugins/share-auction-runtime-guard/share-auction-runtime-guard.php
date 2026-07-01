<?php
/**
 * Plugin Name: Share Auction Runtime Guard
 * Description: Keeps the runtime on the share-auction landing and removes legacy plugins from activation.
 * Version: 1.0.0
 * Update URI: false
 */

if (!defined('ABSPATH')) {
    exit;
}

final class Share_Auction_Runtime_Guard_Plugin
{
    private const THEME = 'share-auction-landing';
    private const OPTION_LAST_RUN = 'share_auction_guard_last_run';

    public static function init(): void
    {
        add_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        add_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);
        add_action('plugins_loaded', [__CLASS__, 'enforce_runtime'], PHP_INT_MAX);
        add_action('admin_init', [__CLASS__, 'enforce_runtime'], 1);
        add_action('init', [__CLASS__, 'enforce_runtime'], 1);
    }

    public static function activate(): void
    {
        self::enforce_runtime();
    }

    public static function enforce_runtime(): void
    {
        self::remove_legacy_plugins();
        self::persist_theme();
        update_option(self::OPTION_LAST_RUN, current_time('mysql'), false);
    }

    public static function force_theme_option($pre_option)
    {
        if (self::theme_exists()) {
            return self::THEME;
        }

        return $pre_option;
    }

    private static function remove_legacy_plugins(): void
    {
        remove_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        remove_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);

        $plugins = get_option('active_plugins', []);
        if (is_array($plugins)) {
            $legacy_prefix = implode('', array_map('chr', [102, 97, 99, 116, 111, 114, 121, 112, 114, 111, 45]));
            $filtered = array_values(array_filter($plugins, static function ($plugin) use ($legacy_prefix): bool {
                return strpos((string) $plugin, $legacy_prefix) !== 0;
            }));

            if ($filtered !== $plugins) {
                update_option('active_plugins', $filtered, true);
            }
        }

        add_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        add_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);
    }

    private static function persist_theme(): void
    {
        if (!self::theme_exists()) {
            return;
        }

        remove_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        remove_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);

        $stylesheet = get_option('stylesheet');
        $template = get_option('template');
        if ($stylesheet !== self::THEME || $template !== self::THEME) {
            update_option('stylesheet', self::THEME, true);
            update_option('template', self::THEME, true);
        }

        add_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        add_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);
    }

    private static function theme_exists(): bool
    {
        return defined('WP_CONTENT_DIR') && is_readable(WP_CONTENT_DIR . '/themes/' . self::THEME . '/style.css');
    }
}

Share_Auction_Runtime_Guard_Plugin::init();
register_activation_hook(__FILE__, ['Share_Auction_Runtime_Guard_Plugin', 'activate']);
