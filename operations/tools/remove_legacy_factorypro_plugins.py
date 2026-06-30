from __future__ import annotations

import json
import sys
from urllib import parse

from wp_rest_admin import build_client


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


PLUGINS = [
    "factorypro-public-controls/factorypro-public-controls",
    "factorypro-cache-purge-once/factorypro-cache-purge-once",
]


def main() -> int:
    wp = build_client(r"N:\factorypro\deploy\wordpress\.env")
    for plugin in PLUGINS:
        encoded = parse.quote(plugin, safe="/")
        try:
            result = wp.rest("POST", f"/wp/v2/plugins/{encoded}", {"status": "inactive"})
            print(json.dumps({"action": "deactivate", "plugin": plugin, "status": result.get("status")}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"action": "deactivate_failed", "plugin": plugin, "error": str(exc)[:700]}, ensure_ascii=False))

        try:
            result = wp.rest("DELETE", f"/wp/v2/plugins/{encoded}")
            print(json.dumps({"action": "delete", "plugin": plugin, "result": result}, ensure_ascii=False)[:1200])
        except Exception as exc:
            print(json.dumps({"action": "delete_failed", "plugin": plugin, "error": str(exc)[:700]}, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
