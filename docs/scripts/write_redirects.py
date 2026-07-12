#!/usr/bin/env python3
"""Write HTML redirect stubs from docs/redirects.yaml and docs/redirects/*.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

DOCS_BASEURL = "https://databricks-solutions.github.io/lakeflow_framework/"

_STUB_MARKER = "docs-redirect-stub"


def _docs_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def load_redirects(docs_dir: Path | None = None) -> list[dict[str, str]]:
    """Load and merge redirect entries from the central manifest."""
    docs_dir = docs_dir or _docs_dir()
    entries: list[dict[str, str]] = []

    single = docs_dir / "redirects.yaml"
    if single.is_file():
        data = yaml.safe_load(single.read_text(encoding="utf-8")) or {}
        entries.extend(data.get("redirects", []))

    redirects_dir = docs_dir / "redirects"
    if redirects_dir.is_dir():
        for path in sorted(redirects_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            entries.extend(data.get("redirects", []))

    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for entry in entries:
        src = entry.get("from", "").strip()
        dst = entry.get("to", "").strip()
        if not src or not dst or src in seen:
            continue
        seen.add(src)
        deduped.append({"from": src, "to": dst})
    return deduped


def _is_redirect_stub(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return _STUB_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _redirect_html(*, target: str, canonical: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="{_STUB_MARKER}" content="true">
    <title>Page moved</title>
    <meta http-equiv="refresh" content="0; url={target}">
    <link rel="canonical" href="{canonical}">
  </head>
  <body>
    <p>This page has moved to <a href="{target}">{target}</a>.</p>
  </body>
</html>
"""


def write_redirects(
    version_outdir: Path,
    *,
    version_name: str,
    baseurl: str = DOCS_BASEURL,
    docs_dir: Path | None = None,
) -> int:
    """Write redirect stubs into a built version directory. Returns count written."""
    version_outdir = version_outdir.resolve()
    written = 0

    for entry in load_redirects(docs_dir):
        from_rel = entry["from"]
        to_rel = entry["to"]
        stub_path = version_outdir / from_rel
        target_path = version_outdir / to_rel

        if stub_path.exists() and stub_path.is_dir():
            print(f"skip redirect (directory exists): {from_rel}", file=sys.stderr)
            continue
        if stub_path.exists() and not _is_redirect_stub(stub_path):
            print(f"skip redirect (real page exists): {from_rel}", file=sys.stderr)
            continue
        if not target_path.exists():
            print(f"warning: redirect target missing: {to_rel}", file=sys.stderr)

        stub_path.parent.mkdir(parents=True, exist_ok=True)
        canonical = f"{baseurl.rstrip('/')}/{version_name}/{to_rel}"
        stub_path.write_text(
            _redirect_html(target=to_rel, canonical=canonical),
            encoding="utf-8",
        )
        written += 1

    return written


def write_root_mirror_redirects(
    output_root: Path,
    *,
    version_name: str = "current",
    baseurl: str = DOCS_BASEURL,
    docs_dir: Path | None = None,
) -> int:
    """Mirror redirect stubs at site root for links that omit the version prefix."""
    output_root = output_root.resolve()
    version_dir = output_root / version_name
    if not version_dir.is_dir():
        return 0

    written = 0
    for entry in load_redirects(docs_dir):
        from_rel = entry["from"]
        to_rel = entry["to"]
        stub_path = output_root / from_rel
        target_path = version_dir / to_rel

        if stub_path.exists():
            continue
        if not target_path.exists():
            continue

        stub_path.parent.mkdir(parents=True, exist_ok=True)
        target_url = f"{version_name}/{to_rel}"
        canonical = f"{baseurl.rstrip('/')}/{target_url}"
        stub_path.write_text(
            _redirect_html(target=target_url, canonical=canonical),
            encoding="utf-8",
        )
        written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Write HTML redirect stubs for docs.")
    parser.add_argument(
        "version_outdir",
        type=Path,
        help="Built version directory (e.g. docs/build/html/current)",
    )
    parser.add_argument(
        "--version-name",
        default="current",
        help="Version folder name for canonical URLs (default: current)",
    )
    parser.add_argument(
        "--baseurl",
        default=DOCS_BASEURL,
        help="Site base URL for canonical links",
    )
    args = parser.parse_args()

    count = write_redirects(
        args.version_outdir,
        version_name=args.version_name,
        baseurl=args.baseurl,
    )
    print(f"Wrote {count} redirect stub(s) to {args.version_outdir}", file=sys.stderr)


if __name__ == "__main__":
    main()
