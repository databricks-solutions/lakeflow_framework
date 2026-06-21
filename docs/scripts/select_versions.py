#!/usr/bin/env python3
"""Select which git tags to include in the versioned docs build.

Strategy
--------
* For the current release major (highest major present), include the latest
  patch release for the last 5 minor series.
* Also include the latest available release for each of the last 3 major
  versions.

The selected tags are printed as JSON by default so they can be consumed by
other scripts. A regex mode is still provided for compatibility.

Usage
-----
    python docs/scripts/select_versions.py
    python docs/scripts/select_versions.py --format regex
"""
from __future__ import annotations

import argparse
import json
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


def _sort_tags_desc(tags: set[str]) -> list[str]:
    parsed = [_parse(tag) for tag in tags]
    valid = [item for item in parsed if item is not None]
    valid.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    return [t[3] for t in valid]


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

    # Latest release per major (based on latest minor, then latest patch).
    best_per_major: dict[int, tuple[int, int, str]] = {}
    for (major, minor), (patch, tag) in best_per_minor.items():
        if (
            major not in best_per_major
            or minor > best_per_major[major][0]
            or (minor == best_per_major[major][0] and patch > best_per_major[major][1])
        ):
            best_per_major[major] = (minor, patch, tag)

    majors_desc = sorted(best_per_major.keys(), reverse=True)
    current_major = majors_desc[0]

    # Last 5 minor series for current major (latest patch in each minor).
    current_major_minors = sorted(
        [minor for (major, minor) in best_per_minor if major == current_major],
        reverse=True,
    )
    current_major_last_5 = {
        best_per_minor[(current_major, minor)][1] for minor in current_major_minors[:5]
    }

    # Last 3 major versions (latest release per major).
    last_3_major_latest = {best_per_major[major][2] for major in majors_desc[:3]}

    return _sort_tags_desc(current_major_last_5 | last_3_major_latest)


def tags_to_regex(tags: list[str]) -> str:
    if not tags:
        return r"^$"
    escaped = [re.escape(t) for t in tags]
    return r"^(" + "|".join(escaped) + r")$"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=["json", "regex"],
        default="json",
        help="Output format for selected versions.",
    )
    args = parser.parse_args()

    tags = _get_tags()
    selected = select_versions(tags)
    pattern = tags_to_regex(selected)

    print(f"All tags found  : {tags}", file=sys.stderr)
    print(f"Selected tags   : {selected}", file=sys.stderr)
    print(f"Selected regex  : {pattern}", file=sys.stderr)

    # Backward-compat environment export for existing callers.
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as fh:
            fh.write(f"SMV_TAG_WHITELIST={pattern}\n")
        print(f"Written to $GITHUB_ENV ({github_env})", file=sys.stderr)

    if args.format == "regex":
        print(pattern)
    else:
        print(json.dumps(selected))


if __name__ == "__main__":
    main()
