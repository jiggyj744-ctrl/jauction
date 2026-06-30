from __future__ import annotations

import argparse
import json
import re
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from urllib import parse, request
from urllib.error import HTTPError, URLError

from install_wp_theme import load_env


UA = "Mozilla/5.0 FactoryProWpRestAdmin/1.0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class WP:
    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.cookies = CookieJar()
        self.opener = request.build_opener(request.HTTPCookieProcessor(self.cookies))
        self.nonce = ""

    def open(
        self,
        url: str,
        data: bytes | None = None,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> bytes:
        req = request.Request(url, data=data, method=method, headers={"User-Agent": UA, **(headers or {})})
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                return resp.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {method} {url}: {body[:1000]}") from exc
        except URLError as exc:
            raise RuntimeError(f"request failed {method} {url}: {exc}") from exc

    def login(self) -> None:
        body = parse.urlencode(
            {
                "log": self.user,
                "pwd": self.password,
                "wp-submit": "Log In",
                "redirect_to": f"{self.base_url}/wp-admin/",
                "testcookie": "1",
            }
        ).encode("utf-8")
        self.open(
            f"{self.base_url}/wp-login.php",
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{self.base_url}/wp-login.php"},
        )
        admin = self.open(f"{self.base_url}/wp-admin/").decode("utf-8", errors="replace")
        match = re.search(r'"nonce":"([^"\\]+)"', admin)
        if not match:
            raise RuntimeError("Could not log in or find REST nonce")
        self.nonce = match.group(1)
        print("login=ok")

    def rest(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {"X-WP-Nonce": self.nonce, "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        raw = self.open(f"{self.base_url}/wp-json{path}", data=data, method=method, headers=headers)
        if not raw:
            return None
        return json.loads(raw.decode("utf-8", errors="replace"))


def build_client(env_path: str) -> WP:
    env = load_env(Path(env_path))
    base_url = env.get("ROOT_WORDPRESS_URL", "https://factorypro.co.kr")
    user = env.get("WP_ADMIN_USER", "")
    password = env.get("WP_ADMIN_PASSWORD", "")
    if not user or not password:
        raise RuntimeError(f"missing WP_ADMIN_USER/WP_ADMIN_PASSWORD in {env_path}")
    wp = WP(base_url, user, password)
    wp.login()
    return wp


def list_plugins(wp: WP) -> list[dict]:
    plugins = wp.rest("GET", "/wp/v2/plugins?context=edit&per_page=100")
    if not isinstance(plugins, list):
        return []
    for item in plugins:
        plugin = item.get("plugin")
        name = item.get("name")
        if "factorypro" in str(plugin).lower() or "factorypro" in str(name).lower():
            print(json.dumps({"plugin": plugin, "status": item.get("status"), "name": name, "version": item.get("version")}, ensure_ascii=False))
    return plugins


def deactivate_plugin(wp: WP, plugin: str) -> None:
    result = wp.rest("POST", f"/wp/v2/plugins/{parse.quote(plugin, safe='/')}", {"status": "inactive"})
    print(json.dumps({"plugin": result.get("plugin"), "status": result.get("status"), "name": result.get("name")}, ensure_ascii=False))


def update_landing_settings(wp: WP) -> None:
    settings = wp.rest(
        "POST",
        "/wp/v2/settings",
        {
            "title": "지분경매 매입센터",
            "description": "공유물 지분 매입·상속지분·토지지분·지분경매 상담",
        },
    )
    print(json.dumps({"settings_title": settings.get("title"), "settings_description": settings.get("description")}, ensure_ascii=False))

    page = wp.rest(
        "POST",
        "/wp/v2/pages/524",
        {
            "title": "지분경매·공유물 지분 매입 상담",
            "slug": "share-auction-consulting",
        },
    )
    title = page.get("title", {})
    print(json.dumps({"page_id": page.get("id"), "page_title": title.get("raw") or title.get("rendered"), "slug": page.get("slug")}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=r"N:\factorypro\deploy\wordpress\.env")
    parser.add_argument("--list-plugins", action="store_true")
    parser.add_argument("--deactivate", action="append", default=[])
    parser.add_argument("--update-landing-settings", action="store_true")
    args = parser.parse_args()

    wp = build_client(args.env)
    if args.list_plugins:
        list_plugins(wp)
    for plugin in args.deactivate:
        deactivate_plugin(wp, plugin)
    if args.update_landing_settings:
        update_landing_settings(wp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
