"""
Extension library sys.path setup and pre/post init hook execution.

Importable modules live under extensions/libraries/. Executable hooks live under
extensions/pre_init/ and extensions/post_init/ and are not added to sys.path.
"""

from __future__ import annotations

import os
import runpy
import sys
import warnings
from typing import Literal

from constants import FrameworkPaths

Phase = Literal["pre_init", "post_init"]

_PHASE_SUBDIR = {
    "pre_init": "pre_init",
    "post_init": "post_init",
}

_PHASE_LABEL = {
    "pre_init": "Pre-Init",
    "post_init": "Post-Init",
}


def _legacy_extensions_has_top_level_py(extensions_dir: str) -> bool:
    """True if extensions_dir exists and has at least one top-level .py file."""
    if not os.path.isdir(extensions_dir):
        return False
    for name in os.listdir(extensions_dir):
        full = os.path.join(extensions_dir, name)
        if os.path.isfile(full) and name.endswith(".py"):
            return True
    return False


def add_extensions_libraries_to_sys_path(
    framework_path: str,
    bundle_path: str,
    logger,
) -> None:
    """
    Add extensions/libraries to sys.path for each of framework and bundle.

    If extensions/libraries/ exists, it is used. Otherwise, if the legacy flat
    extensions/ directory contains top-level .py files, that directory is added
    and a deprecation warning is emitted.
    """
    for base, level in ((framework_path, "framework"), (bundle_path, "bundle")):
        libraries = os.path.normpath(os.path.join(base, FrameworkPaths.EXTENSIONS_LIBRARIES_PATH))
        legacy_root = os.path.normpath(os.path.join(base, FrameworkPaths.EXTENSIONS_PATH))

        if os.path.isdir(libraries):
            sys.path.insert(0, libraries)
            logger.info("Added %s extensions libraries to sys.path: %s", level, libraries)
        elif _legacy_extensions_has_top_level_py(legacy_root):
            sys.path.insert(0, legacy_root)
            msg = (
                f"Top-level .py files under {legacy_root} are deprecated. "
                f"Move importable modules to {os.path.join(legacy_root, 'libraries')}. "
                "Support for flat extensions/ without libraries/ will be removed in a future release."
            )
            logger.warning(msg)
            warnings.warn(msg, DeprecationWarning, stacklevel=1)


def run_init_hooks(
    framework_path: str,
    bundle_path: str,
    phase: Phase,
    logger,
) -> None:
    """
    Execute all .py files under extensions/<pre_init|post_init>/ for framework then bundle.

    Files are sorted by filename; files starting with '_' are skipped.
    Each file is run with runpy.run_path(..., run_name='__main__').
    """
    if phase not in _PHASE_SUBDIR:
        raise ValueError(f"Invalid phase: {phase!r}. Expected one of {list(_PHASE_SUBDIR)}.")

    sub = _PHASE_SUBDIR[phase]
    label = _PHASE_LABEL[phase]

    for base, level in ((framework_path, "framework"), (bundle_path, "bundle")):
        folder = os.path.normpath(os.path.join(base, FrameworkPaths.EXTENSIONS_PATH, sub))
        if not os.path.isdir(folder):
            continue
        for filename in sorted(os.listdir(folder)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            path = os.path.join(folder, filename)
            if not os.path.isfile(path):
                continue
            logger.info("Running %s %s hook: %s", level, label, path)
            runpy.run_path(path, run_name="__main__")
