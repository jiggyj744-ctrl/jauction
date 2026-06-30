from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from urllib import parse

from install_wp_theme import load_env
from wp_rest_admin import WP


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


TARGETS = [
    "factorypro-public-controls/factorypro-public-controls",
    "factorypro-public-controls-runtime/factorypro-public-controls",
    "factorypro-public-controls-livefix/factorypro-public-controls",
    "factorypro-platform/factorypro-platform",
    "factorypro-header-polish/factorypro-header-polish",
    "factorypro-cache-purge-once/factorypro-cache-purge-once",
]


def find_action_url(base_url: str, page: str, plugin: str, action: str) -> str | None:
    encoded_plugin = parse.quote(plugin, safe="")
    for match in re.finditer(r'href=["\']([^"\']*plugins\.php\?[^"\']*)["\']', page, re.I):
        href = html.unescape(match.group(1))
        if f"action={action}" not in href:
            continue
        if plugin in href or encoded_plugin in href:
            return parse.urljoin(base_url + "/wp-admin/", href)
    return None


def main() -> int:
    env = load_env(Path(r"N:\factorypro\deploy\wordpress\.env"))
    base_url = env.get("ROOT_WORDPRESS_URL", "https://factorypro.co.kr").rstrip("/")
    wp = WP(base_url, env.get("WP_ADMIN_USER", ""), env.get("WP_ADMIN_PASSWORD", ""))
    wp.login()

    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)

    for plugin in TARGETS:
        page = wp.open(f"{base_url}/wp-admin/plugins.php").decode("utf-8", errors="replace")
        out_dir.joinpath("wp-admin-plugins-page.html").write_text(page, encoding="utf-8", errors="replace")

        deactivate_url = find_action_url(base_url, page, plugin, "deactivate")
        if deactivate_url:
            wp.open(deactivate_url, headers={"Referer": f"{base_url}/wp-admin/plugins.php"})
            print(f"deactivate={plugin}")
        else:
            print(f"deactivate_url_missing={plugin}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
