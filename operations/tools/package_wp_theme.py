from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=r"work\github-clean\jauction-clean\wordpress\theme\share-auction-landing")
    parser.add_argument("--output", default=r"outputs\share-auction-landing.zip")
    parser.add_argument("--slug", default="share-auction-landing")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.exists():
        raise FileNotFoundError(f"missing theme source: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(source)
            for parent in reversed(arcname.parents):
                if parent == Path("."):
                    continue
                name = parent.as_posix().rstrip("/") + "/"
                if name not in zf.namelist():
                    zf.writestr(name, "")
            zf.write(path, arcname.as_posix())

    print(f"zip={output}")
    print(f"files={sum(1 for _ in source.rglob('*') if _.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
