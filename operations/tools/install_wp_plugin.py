from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from urllib import parse

from install_wp_theme import WpSession, compact_html, find_nonce, load_env, multipart, write_debug


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_plugin_activation_url(base_url: str, plugin_file: str, *pages: str) -> str | None:
    encoded = parse.quote(plugin_file, safe="")
    for page in pages:
        for match in re.finditer(r'href=["\']([^"\']*plugins\.php\?[^"\']*)["\']', page, re.I):
            href = html.unescape(match.group(1))
            if "action=activate" not in href:
                continue
            if plugin_file in href or encoded in href:
                return parse.urljoin(base_url.rstrip("/") + "/wp-admin/", href)
    return None


def find_plugin_overwrite_url(base_url: str, page: str) -> str | None:
    match = re.search(r'href=["\']([^"\']*overwrite=update-plugin[^"\']*)["\']', page, re.I)
    if not match:
        return None

    return parse.urljoin(base_url.rstrip("/") + "/wp-admin/", html.unescape(match.group(1)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=r"N:\factorypro\deploy\wordpress\.env")
    parser.add_argument("--zip", default=r"outputs\share-auction-runtime-guard.zip")
    parser.add_argument("--plugin", default="share-auction-runtime-guard/share-auction-runtime-guard.php")
    args = parser.parse_args()

    zip_path = Path(args.zip).resolve()
    if not zip_path.exists():
        raise FileNotFoundError(f"missing plugin zip: {zip_path}")

    env = load_env(Path(args.env))
    base_url = env.get("ROOT_WORDPRESS_URL", "https://factorypro.co.kr").rstrip("/")
    wp = WpSession(base_url, env.get("WP_ADMIN_USER", ""), env.get("WP_ADMIN_PASSWORD", ""))
    wp.login()

    upload_page = wp.open(f"{base_url}/wp-admin/plugin-install.php?tab=upload", timeout=30)
    nonce = find_nonce(upload_page)
    body, content_type = multipart(
        {
            "_wpnonce": nonce,
            "_wp_http_referer": "/wp-admin/plugin-install.php?tab=upload",
            "install-plugin-submit": "Install Now",
        },
        "pluginzip",
        zip_path,
    )
    print("upload=attempt")
    upload_response = wp.open(
        f"{base_url}/wp-admin/update.php?action=upload-plugin",
        data=body,
        method="POST",
        headers={"Content-Type": content_type, "Referer": f"{base_url}/wp-admin/plugin-install.php?tab=upload"},
        timeout=180,
    )
    write_debug("wp-plugin-upload-response.html", upload_response)

    overwrite_url = find_plugin_overwrite_url(base_url, upload_response)
    if overwrite_url:
        print("replace=attempt")
        upload_response = wp.open(
            overwrite_url,
            headers={"Referer": f"{base_url}/wp-admin/plugin-install.php?tab=upload"},
            timeout=180,
        )
        write_debug("wp-plugin-replace-response.html", upload_response)

    failure_pattern = r"Plugin installation failed|Package could not be installed|플러그인 설치 실패|패키지를 설치할 수 없습니다"
    if re.search(failure_pattern, upload_response, re.I):
        raise RuntimeError("plugin upload failed: " + compact_html(upload_response, 1600))

    print("upload=ok")
    plugins_page = wp.open(f"{base_url}/wp-admin/plugins.php", timeout=30)
    activation_url = find_plugin_activation_url(base_url, args.plugin, upload_response, plugins_page)
    if activation_url:
        wp.open(activation_url, headers={"Referer": f"{base_url}/wp-admin/plugins.php"}, timeout=60)
        print("activate=attempted")
    elif args.plugin in plugins_page and re.search(re.escape(args.plugin) + r"[\s\S]{0,800}deactivate", plugins_page, re.I):
        print("activate=already_active")
    else:
        write_debug("wp-plugin-activation-missing.html", plugins_page)
        raise RuntimeError("plugin activation link not found")

    print(f"wordpress={base_url}")
    print(f"plugin={args.plugin}")
    print(f"zip={zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
