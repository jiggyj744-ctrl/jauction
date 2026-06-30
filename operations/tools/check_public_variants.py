from __future__ import annotations

import re
import sys
from urllib import request


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


URLS = [
    "https://factorypro.co.kr/",
    "https://factorypro.co.kr/?verify=stable_105",
]

USER_AGENTS = {
    "plain": "Mozilla/5.0",
    "chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "bot": "FactoryProbe/1.0",
}


def check(url: str, label: str, user_agent: str) -> None:
    req = request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    data = request.urlopen(req, timeout=30).read()
    text = data.decode("utf-8", errors="replace")
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    print(
        " ".join(
            [
                f"url={url}",
                f"ua={label}",
                f"theme={str(b'share-auction-landing' in data).lower()}",
                f"astra={str(b'wp-content/themes/astra' in data).lower()}",
                f"v105={str(b'ver=1.0.5' in data).lower()}",
                f"factorypro={str('FactoryPro' in text).lower()}",
                f"bytes={len(data)}",
                "title=" + (title.group(1).strip()[:220] if title else "NONE"),
            ]
        )
    )


def main() -> int:
    for url in URLS:
        for label, user_agent in USER_AGENTS.items():
            check(url, label, user_agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
