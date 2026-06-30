from __future__ import annotations

import argparse
import html
import http.cookiejar
import re
import secrets
import sys
from pathlib import Path
from urllib import parse, request
from urllib.error import HTTPError, URLError


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"missing env file: {path}")
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def compact_html(text: str, limit: int = 1600) -> str:
    text = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:limit]


def write_debug(name: str, text: str) -> None:
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    (out_dir / name).write_text(text, encoding="utf-8", errors="replace")


def extract_notices(text: str) -> str:
    notices = re.findall(r'(?is)<div[^>]+(?:notice|error|updated)[^>]*>(.*?)</div>', text)
    compacted = [compact_html(item, 600) for item in notices]
    compacted = [item for item in compacted if item]
    return " | ".join(compacted[:5])


def multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = "----shareauction" + secrets.token_hex(12)
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'
            "Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(file_path.read_bytes())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def find_nonce(text: str, name: str = "_wpnonce") -> str:
    pattern = (
        r'name=["\']' + re.escape(name) + r'["\']\s+value=["\']([^"\']+)["\']'
        r'|value=["\']([^"\']+)["\']\s+name=["\']' + re.escape(name) + r'["\']'
    )
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError(f"nonce not found: {name}; page={compact_html(text)}")
    return html.unescape(match.group(1) or match.group(2))


def find_activation_url(base_url: str, theme_slug: str, *pages: str) -> str | None:
    slug_pattern = re.escape(theme_slug)
    patterns = [
        r'href=["\']([^"\']*action=activate[^"\']*stylesheet=' + slug_pattern + r'[^"\']*)["\']',
        r'href=["\']([^"\']*stylesheet=' + slug_pattern + r'[^"\']*action=activate[^"\']*)["\']',
    ]
    for page in pages:
        for pattern in patterns:
            match = re.search(pattern, page)
            if match:
                href = html.unescape(match.group(1))
                return parse.urljoin(base_url.rstrip("/") + "/wp-admin/", href)
    return None


def find_overwrite_url(base_url: str, page: str) -> str | None:
    patterns = [
        r'href=["\']([^"\']*overwrite=update-theme[^"\']*)["\']',
        r'action=["\']([^"\']*update\.php\?action=upload-theme[^"\']*)["\'][\s\S]{0,4000}?overwrite["\']?\s+value=["\']update-theme',
    ]
    for pattern in patterns:
        match = re.search(pattern, page)
        if match:
            href = html.unescape(match.group(1))
            return parse.urljoin(base_url.rstrip("/") + "/wp-admin/", href)
    return None


class WpSession:
    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.cookies = http.cookiejar.CookieJar()
        self.opener = request.build_opener(request.HTTPCookieProcessor(self.cookies))

    def open(
        self,
        url: str,
        data: bytes | None = None,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        timeout: int = 120,
    ) -> str:
        req = request.Request(url, data=data, method=method, headers={"User-Agent": UA, **(headers or {})})
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                body = resp.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {method} {url}: {compact_html(body)}") from exc
        except URLError as exc:
            raise RuntimeError(f"request failed {method} {url}: {exc}") from exc
        return body.decode("utf-8", errors="replace")

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
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{self.base_url}/wp-login.php",
            },
            timeout=30,
        )
        admin = self.open(f"{self.base_url}/wp-admin/", timeout=30)
        if not re.search(r"wp-admin/profile\.php|wpadminbar|Dashboard|알림판", admin):
            raise RuntimeError("login did not reach wp-admin")
        print("login=ok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=r"N:\factorypro\deploy\wordpress\.env")
    parser.add_argument("--url")
    parser.add_argument("--zip", default=r"outputs\share-auction-landing.zip")
    parser.add_argument("--theme", default="share-auction-landing")
    parser.add_argument("--force-upload", action="store_true")
    parser.add_argument("--skip-activate", action="store_true")
    args = parser.parse_args()

    env_path = Path(args.env)
    zip_path = Path(args.zip).resolve()
    if not zip_path.exists():
        raise FileNotFoundError(f"missing theme zip: {zip_path}")

    env = load_env(env_path)
    base_url = (args.url or env.get("ROOT_WORDPRESS_URL") or "https://factorypro.co.kr").rstrip("/")
    user = env.get("WP_ADMIN_USER", "")
    password = env.get("WP_ADMIN_PASSWORD", "")
    if not user or not password:
        raise RuntimeError(f"missing WP_ADMIN_USER/WP_ADMIN_PASSWORD in {env_path}")

    wp = WpSession(base_url, user, password)
    wp.login()

    themes_page = wp.open(f"{base_url}/wp-admin/themes.php", timeout=30)
    upload_page = ""
    upload_response = ""
    if args.theme in themes_page and not args.force_upload:
        print("theme=already_present")
    else:
        upload_page = wp.open(f"{base_url}/wp-admin/theme-install.php?browse=upload", timeout=30)
        nonce = find_nonce(upload_page)
        body, content_type = multipart(
            {
                "_wpnonce": nonce,
                "_wp_http_referer": "/wp-admin/theme-install.php?browse=upload",
                "install-theme-submit": "Install Now",
            },
            "themezip",
            zip_path,
        )
        print("upload=attempt")
        upload_response = wp.open(
            f"{base_url}/wp-admin/update.php?action=upload-theme",
            data=body,
            method="POST",
            headers={"Content-Type": content_type, "Referer": f"{base_url}/wp-admin/theme-install.php?browse=upload"},
            timeout=180,
        )
        write_debug("wp-theme-upload-response.html", upload_response)
        overwrite_url = find_overwrite_url(base_url, upload_response)
        if overwrite_url:
            print("replace=attempt")
            upload_response = wp.open(
                overwrite_url,
                headers={"Referer": f"{base_url}/wp-admin/theme-install.php?browse=upload"},
                timeout=180,
            )
            write_debug("wp-theme-replace-response.html", upload_response)
        notices = extract_notices(upload_response)
        failure_pattern = r"Theme installation failed|Package could not be installed|style\.css stylesheet|테마 설치 실패|패키지를 설치할 수 없습니다|스타일시트가 없습니다"
        success_pattern = r"Theme installed successfully|Theme updated successfully|테마가 성공적으로 설치|테마가 성공적으로 업데이트"
        if re.search(failure_pattern, upload_response, re.I):
            raise RuntimeError("theme upload failed: " + (notices or compact_html(upload_response)))
        if re.search(success_pattern, upload_response, re.I):
            print("upload=ok")
        else:
            print("upload=unknown " + (notices or compact_html(upload_response)))
        themes_page = wp.open(f"{base_url}/wp-admin/themes.php", timeout=30)
        write_debug("wp-theme-themes-page.html", themes_page)

    if not args.skip_activate:
        activation_url = find_activation_url(base_url, args.theme, upload_response, themes_page, upload_page)
        if activation_url:
            wp.open(activation_url, headers={"Referer": f"{base_url}/wp-admin/themes.php"}, timeout=30)
            print("activate=attempted")
        elif re.search(re.escape(args.theme) + r"[\s\S]{0,800}(current-theme|Active:|활성)", themes_page, re.I):
            print("activate=already_active")
        else:
            write_debug("wp-theme-activation-missing-themes-page.html", themes_page)
            raise RuntimeError("activation link not found")

    front = wp.open(f"{base_url}/", timeout=30)
    front_has_theme = bool(re.search(r"share-auction-landing|공유물 지분 매입|지분경매", front))
    print(f"wordpress={base_url}")
    print(f"theme={args.theme}")
    print(f"zip={zip_path}")
    print(f"front_has_theme_signals={str(front_has_theme).lower()}")
    if not front_has_theme and not args.skip_activate:
        raise RuntimeError("public front page did not show expected theme signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
