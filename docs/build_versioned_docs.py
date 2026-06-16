#!/usr/bin/env python3
"""Build versioned docs without sphinx-multiversion.

Build strategy:
- Always build `main` as the default development docs, published as `current`.
- Build selected release tags from docs/select_versions.py.
- Write per-version output under docs/build/html/<version>/.
- Generate docs/build/html/versions.json for the sidebar switcher.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _run_capture(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _repo_root(docs_dir: Path) -> Path:
    return docs_dir.parent


def _selected_tags(repo_root: Path) -> list[str]:
    output = _run_capture([sys.executable, "docs/select_versions.py"], cwd=repo_root)
    return json.loads(output) if output else []


def _list_preview_branches(repo_root: Path) -> list[str]:
    raw = _run_capture(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"],
        cwd=repo_root,
    )
    branches = [line.strip() for line in raw.splitlines() if line.strip()]
    return [b for b in branches if b != "main"]


def _safe_remove(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _normalize_name(ref: str) -> str:
    return ref.replace("/", "-")


def _build_ref(
    *,
    repo_root: Path,
    docs_dir: Path,
    worktrees_root: Path,
    output_root: Path,
    ref: str,
    version_name: str,
) -> None:
    worktree_path = worktrees_root / _normalize_name(version_name)
    _run(["git", "worktree", "add", "--detach", str(worktree_path), ref], cwd=repo_root)
    try:
        out_dir = output_root / version_name
        out_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["DOCS_CURRENT_VERSION"] = version_name
        env["DOCS_VERSIONS_FILE"] = str(output_root / "versions.json")
        _run(
            [
                "sphinx-build",
                "-b",
                "html",
                "-c",
                str(docs_dir),
                str(worktree_path / "docs" / "source"),
                str(out_dir),
            ],
            cwd=repo_root,
            env=env,
        )
    finally:
        _run(["git", "worktree", "remove", "--force", str(worktree_path)], cwd=repo_root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Include local branches in build.")
    args = parser.parse_args()

    docs_dir = Path(__file__).resolve().parent
    repo_root = _repo_root(docs_dir)
    build_root = docs_dir / "build"
    output_root = build_root / "html"
    worktrees_root = build_root / ".worktrees"

    _safe_remove(output_root)
    _safe_remove(worktrees_root)
    output_root.mkdir(parents=True, exist_ok=True)
    worktrees_root.mkdir(parents=True, exist_ok=True)

    tags = _selected_tags(repo_root)
    versions = [{"name": "current", "ref": "main"}] + [{"name": t, "ref": t} for t in tags]
    if args.preview:
        for branch in _list_preview_branches(repo_root):
            versions.append({"name": _normalize_name(branch), "ref": branch})

    # De-duplicate while preserving order.
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in versions:
        if item["name"] in seen:
            continue
        seen.add(item["name"])
        deduped.append(item)

    links = [{"name": item["name"], "url": f"{item['name']}/index.html", "is_latest": item["name"] == "current"} for item in deduped]
    (output_root / "versions.json").write_text(json.dumps(links, indent=2) + "\n", encoding="utf-8")

    for item in deduped:
        print(f"Building docs for {item['ref']} -> {item['name']}", file=sys.stderr)
        _build_ref(
            repo_root=repo_root,
            docs_dir=docs_dir,
            worktrees_root=worktrees_root,
            output_root=output_root,
            ref=item["ref"],
            version_name=item["name"],
        )

    # Root redirect for GitHub Pages.
    index_html = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Lakeflow Framework Docs</title>
    <meta http-equiv="refresh" content="0; url=current/index.html">
  </head>
  <body>
    <p>Redirecting to <a href="current/index.html">latest docs</a>...</p>
  </body>
</html>
"""
    (output_root / "index.html").write_text(index_html, encoding="utf-8")

    _safe_remove(worktrees_root)
    _run(["git", "worktree", "prune"], cwd=repo_root)


if __name__ == "__main__":
    main()
