#!/usr/bin/env python3
"""Select which git tags to include in the versioned docs build.

Strategy
--------
* Latest patch of each *major* version — always included so that users on any
  major series always have an up-to-date docs URL.
* The 5 most recent *minor* series (regardless of major) — keeps the switcher
  short while still covering recent history.

The union of those two sets is written as a ``smv_tag_whitelist`` regex to
``$GITHUB_ENV`` (so the next workflow step can read it) and also printed to
stdout for local debugging.

Usage
-----
    python docs/select_versions.py

The regex is then picked up by ``conf.py`` via::

    smv_tag_whitelist = os.environ.get('SMV_TAG_WHITELIST', r'^v\\d+\\.\\d+\\.\\d+$')
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def _get_tags() -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [t.strip() for t in result.stdout.splitlines() if t.strip()]


def _parse(tag: str) -> tuple[int, int, int, str] | None:
    m = TAG_RE.match(tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), tag) if m else None


def select_versions(tags: list[str]) -> list[str]:
    parsed = [p for t in tags if (p := _parse(t))]
    if not parsed:
        return []

    # Best (highest) patch within each (major, minor) series.
    best_per_minor: dict[tuple[int, int], tuple[int, str]] = {}
    for major, minor, patch, tag in parsed:
        key = (major, minor)
        if key not in best_per_minor or patch > best_per_minor[key][0]:
            best_per_minor[key] = (patch, tag)

    # Latest minor series per major — ensures every major has representation.
    best_per_major: dict[int, tuple[int, str]] = {}
    for (major, minor), (patch, tag) in best_per_minor.items():
        if major not in best_per_major or minor > best_per_major[major][0]:
            best_per_major[major] = (minor, tag)

    always_include = {tag for _, tag in best_per_major.values()}

    # Last 5 distinct minor series overall (sorted newest-first).
    sorted_minor_keys = sorted(best_per_minor.keys(), reverse=True)
    last_5 = {best_per_minor[k][1] for k in sorted_minor_keys[:5]}

    return sorted(always_include | last_5)


def tags_to_regex(tags: list[str]) -> str:
    if not tags:
        return r"^$"
    escaped = [re.escape(t) for t in tags]
    return r"^(" + "|".join(escaped) + r")$"


def main() -> None:
    tags = _get_tags()
    selected = select_versions(tags)
    pattern = tags_to_regex(selected)

    print(f"All tags found  : {tags}", file=sys.stderr)
    print(f"Selected tags   : {selected}", file=sys.stderr)
    print(f"SMV_TAG_WHITELIST={pattern}", file=sys.stderr)

    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as fh:
            fh.write(f"SMV_TAG_WHITELIST={pattern}\n")
        print(f"Written to $GITHUB_ENV ({github_env})", file=sys.stderr)

    # Print pattern to stdout so callers can capture it if needed.
    print(pattern)


if __name__ == "__main__":
    main()
