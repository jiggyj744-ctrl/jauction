<?php
/**
 * Plugin Name: Share Auction Runtime Guard
 * Description: Keeps the public runtime on the share-auction landing and blocks legacy FactoryPro plugins.
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

final class Share_Auction_Runtime_Guard
{
    private const THEME = 'share-auction-landing';

    public static function init(): void
    {
        add_filter('option_active_plugins', [__CLASS__, 'filter_active_plugins'], 1);
        add_filter('site_option_active_sitewide_plugins', [__CLASS__, 'filter_sitewide_plugins'], 1);
        add_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        add_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);
        add_action('admin_init', [__CLASS__, 'persist_active_plugin_filter'], 1);
        add_action('init', [__CLASS__, 'persist_theme'], 1);
    }

    public static function filter_active_plugins($plugins): array
    {
        if (!is_array($plugins)) {
            return [];
        }

        return array_values(array_filter($plugins, static function ($plugin): bool {
            return strpos((string) $plugin, 'factorypro-') !== 0;
        }));
    }

    public static function filter_sitewide_plugins($plugins): array
    {
        if (!is_array($plugins)) {
            return [];
        }

        foreach (array_keys($plugins) as $plugin) {
            if (strpos((string) $plugin, 'factorypro-') === 0) {
                unset($plugins[$plugin]);
            }
        }

        return $plugins;
    }

    public static function force_theme_option($pre_option)
    {
        if (self::theme_exists()) {
            return self::THEME;
        }

        return $pre_option;
    }

    public static function persist_active_plugin_filter(): void
    {
        remove_filter('option_active_plugins', [__CLASS__, 'filter_active_plugins'], 1);
        $plugins = get_option('active_plugins', []);
        add_filter('option_active_plugins', [__CLASS__, 'filter_active_plugins'], 1);

        $filtered = self::filter_active_plugins($plugins);
        if ($filtered !== $plugins) {
            update_option('active_plugins', $filtered, true);
        }
    }

    public static function persist_theme(): void
    {
        if (!self::theme_exists()) {
            return;
        }

        remove_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        remove_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);
        $stylesheet = get_option('stylesheet');
        $template = get_option('template');
        add_filter('pre_option_stylesheet', [__CLASS__, 'force_theme_option'], 999);
        add_filter('pre_option_template', [__CLASS__, 'force_theme_option'], 999);

        if ($stylesheet !== self::THEME || $template !== self::THEME) {
            update_option('stylesheet', self::THEME, true);
            update_option('template', self::THEME, true);
        }
    }

    private static function theme_exists(): bool
    {
        return defined('WP_CONTENT_DIR') && is_readable(WP_CONTENT_DIR . '/themes/' . self::THEME . '/style.css');
    }
}

Share_Auction_Runtime_Guard::init();
