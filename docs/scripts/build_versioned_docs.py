#!/usr/bin/env python3
"""Build versioned docs without sphinx-multiversion.

Build strategy:
- Always build ``main`` as ``current``.
- Build selected release tags from docs/scripts/select_versions.py.
- ``current`` and release tags use **main's** ``docs/conf.py`` (and templates)
  with that ref's ``docs/source``, so the RTD version selector stays available
  even for tags that predate versioning UI.
- ``--preview`` builds the current branch as ``local-branch-preview`` using
  **that branch's** conf + source (e.g. immaterial rebrand).
- Write per-version output under docs/build/html/<version>/.
- Generate docs/build/html/versions.json as a **superset** manifest consumed by
  both sphinx-immaterial (mike fields) and legacy RTD ``versions.html``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DOCS_BASEURL = "https://databricks-solutions.github.io/lakeflow_framework/"
PREVIEW_VERSION_NAME = "local-branch-preview"
MAIN_CONF_WORKTREE = "_conf_main"


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _run_capture(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _repo_root(docs_dir: Path) -> Path:
    return docs_dir.parent


def _selected_tags(repo_root: Path) -> list[str]:
    output = _run_capture([sys.executable, "docs/scripts/select_versions.py"], cwd=repo_root)
    return json.loads(output) if output else []


def _current_branch(repo_root: Path) -> str:
    try:
        return _run_capture(["git", "branch", "--show-current"], cwd=repo_root)
    except subprocess.CalledProcessError:
        return ""


def _safe_remove(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _normalize_name(ref: str) -> str:
    return ref.replace("/", "-")


def _release_date_for_ref(repo_root: Path, ref: str) -> str:
    # ISO-style date (YYYY-MM-DD) for deterministic display in docs headers.
    return _run_capture(["git", "log", "-1", "--format=%cs", ref], cwd=repo_root)


def _version_for_ref(repo_root: Path, ref: str, fallback: str) -> str:
    # Resolve display version from the VERSION file in the selected ref.
    try:
        raw = _run_capture(["git", "show", f"{ref}:VERSION"], cwd=repo_root)
        value = raw.splitlines()[0].strip().lstrip("v")
        return value or fallback
    except Exception:
        return fallback


def _superset_versions(links: list[dict[str, str]]) -> list[dict[str, object]]:
    """Build a versions.json entry set readable by immaterial and legacy RTD.

    Immaterial / mike fields: ``version``, ``title``, ``aliases``
    Legacy RTD fields: ``name``, ``display_version``, ``url``, ``is_latest``,
    ``status``, ``release_date``
    """
    payload: list[dict[str, object]] = []
    for item in links:
        name = item["name"]
        display = item["display_version"]
        is_current = item.get("status") == "current"
        title = f"{display} (current)" if is_current else display
        aliases: list[str] = ["latest"] if is_current else []
        payload.append(
            {
                # mike / sphinx-immaterial
                "version": name,
                "title": title,
                "aliases": aliases,
                # legacy RTD versions.html (via conf.py _load_versions)
                "name": name,
                "display_version": display,
                "url": f"{name}/index.html",
                "is_latest": is_current,
                "status": "current" if is_current else item.get("status", "release"),
                "release_date": item.get("release_date", ""),
            }
        )
    return payload


def _ensure_worktree(
    *,
    repo_root: Path,
    worktrees_root: Path,
    name: str,
    ref: str,
) -> Path:
    path = worktrees_root / name
    if path.exists():
        return path
    _run(["git", "worktree", "add", "--detach", str(path), ref], cwd=repo_root)
    return path


def _sphinx_build(
    *,
    repo_root: Path,
    conf_dir: Path,
    source_dir: Path,
    out_dir: Path,
    version_name: str,
    versions_file: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DOCS_CURRENT_VERSION"] = version_name
    # Legacy RTD conf.py loads the shared manifest at build time.
    env["DOCS_VERSIONS_FILE"] = str(versions_file)
    _run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-c",
            str(conf_dir),
            str(source_dir),
            str(out_dir),
        ],
        cwd=repo_root,
        env=env,
    )


def _build_ref(
    *,
    repo_root: Path,
    worktrees_root: Path,
    output_root: Path,
    versions_file: Path,
    ref: str,
    version_name: str,
    conf_from_main: bool,
) -> None:
    """Build one version folder.

    When ``conf_from_main`` is True, use main's docs conf/templates with this
    ref's source (keeps the RTD version selector on historical tags).
    Preview uses the **working tree** conf + source.
    """
    if version_name == PREVIEW_VERSION_NAME:
        # Working tree: pick up local conf.py / theme edits immediately.
        source_wt = repo_root
        conf_dir = repo_root / "docs"
        conf_label = f"{ref} (working tree)"
    else:
        source_wt = _ensure_worktree(
            repo_root=repo_root,
            worktrees_root=worktrees_root,
            name=_normalize_name(version_name),
            ref=ref,
        )
        if conf_from_main:
            conf_wt = _ensure_worktree(
                repo_root=repo_root,
                worktrees_root=worktrees_root,
                name=MAIN_CONF_WORKTREE,
                ref="main",
            )
            conf_dir = conf_wt / "docs"
            conf_label = "main"
        else:
            conf_dir = source_wt / "docs"
            conf_label = ref

    source_dir = source_wt / "docs" / "source"
    print(
        f"Building docs for {ref} -> {version_name} (conf={conf_label})",
        file=sys.stderr,
    )
    _sphinx_build(
        repo_root=repo_root,
        conf_dir=conf_dir,
        source_dir=source_dir,
        out_dir=output_root / version_name,
        version_name=version_name,
        versions_file=versions_file,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "Also build the current git branch as ``local-branch-preview`` "
            "using that branch's own conf/source. "
            "``current`` and release tags keep main's conf (RTD selector)."
        ),
    )
    args = parser.parse_args()

    docs_dir = Path(__file__).resolve().parent.parent
    repo_root = _repo_root(docs_dir)
    build_root = docs_dir / "build"
    output_root = build_root / "html"
    worktrees_root = build_root / ".worktrees"
    versions_file = output_root / "versions.json"

    _safe_remove(output_root)
    _safe_remove(worktrees_root)
    output_root.mkdir(parents=True, exist_ok=True)
    worktrees_root.mkdir(parents=True, exist_ok=True)

    tags = _selected_tags(repo_root)
    versions: list[dict[str, str]] = [{"name": "current", "ref": "main"}]
    versions.extend({"name": t, "ref": t} for t in tags)
    if args.preview:
        preview_branch = _current_branch(repo_root)
        if not preview_branch:
            print(
                "Warning: --preview ignored (detached HEAD; no current branch).",
                file=sys.stderr,
            )
        elif preview_branch == "main":
            print(
                "Warning: --preview ignored (already on main; current covers it).",
                file=sys.stderr,
            )
        else:
            versions.append({"name": PREVIEW_VERSION_NAME, "ref": preview_branch})

    # De-duplicate while preserving order.
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in versions:
        if item["name"] in seen:
            continue
        seen.add(item["name"])
        deduped.append(item)

    links = []
    for item in deduped:
        is_current = item["name"] == "current"
        is_preview = item["name"] == PREVIEW_VERSION_NAME
        if is_preview:
            display_version = f"{PREVIEW_VERSION_NAME} ({item['ref']})"
        else:
            display_version = _version_for_ref(repo_root, item["ref"], item["name"].lstrip("v"))
        links.append(
            {
                "name": item["name"],
                "display_version": display_version,
                "url": f"{item['name']}/index.html",
                "is_latest": is_current,
                "status": "current" if is_current else "release",
                "release_date": _release_date_for_ref(repo_root, item["ref"]),
                "ref": item["ref"],
            }
        )

    # If current resolves to the same semantic version as the newest tag,
    # keep only the current entry to avoid duplicate selector items.
    current_version = next((item["display_version"] for item in links if item["name"] == "current"), None)
    if current_version:
        links = [
            item
            for item in links
            if item["name"] == "current" or item["display_version"] != current_version
        ]

    versions_file.write_text(
        json.dumps(_superset_versions(links), indent=2) + "\n",
        encoding="utf-8",
    )

    for item in deduped:
        _build_ref(
            repo_root=repo_root,
            worktrees_root=worktrees_root,
            output_root=output_root,
            versions_file=versions_file,
            ref=item["ref"],
            version_name=item["name"],
            conf_from_main=item["name"] != PREVIEW_VERSION_NAME,
        )

    # Immaterial's mike client resolves version_json relative to the version
    # folder. Copy the site-root manifest into each version dir so both
    # ``versions.json`` and ``../versions.json`` resolve successfully.
    for item in deduped:
        dest = output_root / item["name"] / "versions.json"
        if (output_root / item["name"]).is_dir():
            shutil.copy2(versions_file, dest)

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

    # Basic crawl artifacts for search engines.
    sitemap_entries: list[tuple[str, str]] = [("", _release_date_for_ref(repo_root, "main"))]
    for item in links:
        sitemap_entries.append((f"{item['name']}/index.html", item.get("release_date", "")))

    sitemap_xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for rel_path, lastmod in sitemap_entries:
        url = DOCS_BASEURL.rstrip("/") + "/" + rel_path
        sitemap_xml.append("  <url>")
        sitemap_xml.append(f"    <loc>{url}</loc>")
        if lastmod:
            sitemap_xml.append(f"    <lastmod>{lastmod}</lastmod>")
        sitemap_xml.append("  </url>")
    sitemap_xml.append("</urlset>")
    (output_root / "sitemap.xml").write_text("\n".join(sitemap_xml) + "\n", encoding="utf-8")

    robots_txt = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {DOCS_BASEURL.rstrip('/')}/sitemap.xml",
            "",
        ]
    )
    (output_root / "robots.txt").write_text(robots_txt, encoding="utf-8")

    _safe_remove(worktrees_root)
    _run(["git", "worktree", "prune"], cwd=repo_root)


if __name__ == "__main__":
    main()
