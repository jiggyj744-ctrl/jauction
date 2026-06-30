from __future__ import annotations

import re
import sys
from urllib import request


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

html = request.urlopen(
    request.Request("https://factorypro.co.kr/", headers={"User-Agent": "Mozilla/5.0"}),
    timeout=30,
).read().decode("utf-8", errors="replace")

patterns = [
    ("title", r"<title>(.*?)</title>"),
    ("description", r'<meta name="description" content="(.*?)"'),
    ("og:title", r'<meta property="og:title" content="(.*?)"'),
    ("og:description", r'<meta property="og:description" content="(.*?)"'),
]

for label, pattern in patterns:
    match = re.search(pattern, html, re.S)
    print(f"{label}={match.group(1)[:500] if match else 'NONE'}")

checks = {
    "has_theme": "share-auction-landing" in html,
    "has_new_hero": "지분경매와 공유물 지분 매입" in html,
    "has_share_buy": "공유물 지분 매입" in html,
    "has_auction": "지분경매" in html,
    "has_old_factory_auction": "공장경매" in html,
    "has_astra_theme": "wp-content/themes/astra" in html,
    "has_style_105": "ver=1.0.5" in html,
}

for key, value in checks.items():
    print(f"{key}={str(value).lower()}")

print(f"bytes={len(html.encode('utf-8'))}")
