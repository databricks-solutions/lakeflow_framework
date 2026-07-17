"""Tests for docs/scripts/select_versions.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs" / "scripts"))

from build_versioned_docs import _resolve_git_ref, _superset_versions
from select_versions import MIN_MINOR_MAJOR_0, select_versions


def _tags(*versions: str) -> list[str]:
    return [f"v{version}" if not version.startswith("v") else version for version in versions]


def test_resolve_git_ref_uses_origin_main_when_local_main_missing(tmp_path):
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "init"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=work, check=True)
    (work / "VERSION").write_text("0.21.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "VERSION"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=work, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(origin)],
        cwd=work,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "--detach", "HEAD"], cwd=work, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-D", "main"], cwd=work, check=True, capture_output=True)

    assert _resolve_git_ref(work, "main") == "origin/main"
    assert _resolve_git_ref(work, "v9.9.9") == "v9.9.9"


def test_major_0_includes_minors_back_to_0_12_latest_patch_only():
    tags = _tags(
        "0.16.0",
        "0.16.1",
        "0.15.0",
        "0.14.2",
        "0.13.0",
        "0.12.0",
        "0.11.9",
    )
    selected = select_versions(tags)

    assert selected == ["v0.16.1", "v0.15.0", "v0.14.2", "v0.13.0", "v0.12.0"]
    assert "v0.11.9" not in selected


def test_major_0_not_capped_at_five_minors_when_spanning_beyond_0_12():
    tags = _tags(*(f"0.{minor}.0" for minor in range(MIN_MINOR_MAJOR_0, 21)))
    selected = select_versions(tags)

    assert len(selected) == 21 - MIN_MINOR_MAJOR_0
    assert selected[0] == "v0.20.0"
    assert selected[-1] == f"v0.{MIN_MINOR_MAJOR_0}.0"


def test_non_zero_major_still_limits_to_last_five_minors():
    tags = _tags(*(f"1.{minor}.0" for minor in range(10)))
    selected = select_versions(tags)

    assert selected == ["v1.9.0", "v1.8.0", "v1.7.0", "v1.6.0", "v1.5.0"]


def test_superset_versions_include_mike_and_rtd_fields():
    payload = _superset_versions(
        [
            {
                "name": "current",
                "display_version": "0.16.0",
                "status": "current",
                "release_date": "2026-05-01",
            },
            {
                "name": "v0.15.5",
                "display_version": "0.15.5",
                "status": "release",
                "release_date": "2026-04-01",
            },
        ]
    )

    assert payload == [
        {
            "version": "current",
            "title": "0.16.0 (current)",
            "aliases": ["latest"],
            "name": "current",
            "display_version": "0.16.0",
            "url": "current/index.html",
            "is_latest": True,
            "status": "current",
            "release_date": "2026-05-01",
        },
        {
            "version": "v0.15.5",
            "title": "0.15.5",
            "aliases": [],
            "name": "v0.15.5",
            "display_version": "0.15.5",
            "url": "v0.15.5/index.html",
            "is_latest": False,
            "status": "release",
            "release_date": "2026-04-01",
        },
    ]
