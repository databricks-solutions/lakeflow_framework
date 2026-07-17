"""Test helpers shared across unit and integration tests."""
from __future__ import annotations

import textwrap
from pathlib import Path


def make_tree(base: Path, layout: dict[str, str | None]) -> None:
    """Create a directory tree: {relative_path: file_content}. None = directory only."""
    for rel, content in layout.items():
        full = base / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            full.mkdir(parents=True, exist_ok=True)
        else:
            full.write_text(textwrap.dedent(content))
