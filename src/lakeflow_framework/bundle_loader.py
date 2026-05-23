"""
Bundle sys.path registration and init script execution.

Framework bundle (framework.sourcePath → src/):
  local/libraries/  — org-wide cluster-install artefacts + loose .py / packages
  local/python/     — org-wide Data Flow Spec-referenced Python
  extensions/       — DEPRECATED (v0.13.0): flat top-level .py files; removed in v1.0.0.
                      Migrate importable modules to local/python/.

Pipeline bundle (bundle.sourcePath → src/):
  src/libraries/    — bundle-local cluster-install artefacts + loose .py / packages
  src/python/       — bundle Data Flow Spec-referenced Python
  extensions/       — DEPRECATED (v0.13.0): flat top-level .py files; removed in v1.0.0.
                      Migrate importable modules to src/python/.

Init scripts executed for framework then bundle per phase:
  Framework: local/init/pre/  — before SDP table/view declarations inside initialize_pipeline()
             local/init/post/ — after all SDP declarations
  Bundle:    src/init/pre/
             src/init/post/

Within each directory, scripts run in sorted filename order; files whose names start
with '_' are skipped. A script that raises an exception fails the pipeline.
"""

from __future__ import annotations

import os
import runpy
import sys
import warnings
from typing import Literal

from lakeflow_framework.constants import FrameworkPaths, PipelineBundlePaths

Phase = Literal["pre", "post"]

_FRAMEWORK_PHASE_PATH: dict[str, str] = {
    "pre": FrameworkPaths.LOCAL_INIT_PRE_PATH,
    "post": FrameworkPaths.LOCAL_INIT_POST_PATH,
}

_BUNDLE_PHASE_PATH: dict[str, str] = {
    "pre": PipelineBundlePaths.INIT_PRE_PATH,
    "post": PipelineBundlePaths.INIT_POST_PATH,
}

_PHASE_LABEL: dict[str, str] = {
    "pre": "pre-init",
    "post": "post-init",
}


def _add_if_dir(path: str, label: str, logger=None) -> None:
    """Insert path at the front of sys.path if it is a directory and not already present."""
    if os.path.isdir(path):
        if path not in sys.path:
            sys.path.insert(0, path)
        if logger is not None:
            logger.info("Registered %s on sys.path: %s", label, path)


def _has_top_level_py(directory: str) -> bool:
    """Return True if directory exists and contains at least one top-level .py file."""
    if not os.path.isdir(directory):
        return False
    return any(
        os.path.isfile(os.path.join(directory, name)) and name.endswith(".py")
        for name in os.listdir(directory)
    )


def _warn_legacy_extensions(ext_path: str, python_path: str, level: str, logger=None) -> None:
    """Register legacy extensions/ on sys.path and emit a deprecation warning.

    extensions/ is always registered when it contains top-level .py files,
    regardless of whether src/python/ (or local/python/) also exists.
    Deprecated means warn-and-still-work until removal in v1.0.0.
    """
    if not _has_top_level_py(ext_path):
        return
    _add_if_dir(ext_path, f"{level} extensions (legacy)", logger)
    msg = (
        f"[{level}] Top-level .py files under {ext_path!r} are deprecated. "
        "Move importable modules to "
        + ("local/python/ (framework) or " if level == "framework" else "")
        + "src/python/ (bundle). "
        "Flat extensions/ sys.path support will be removed in v1.0.0."
    )
    if logger is not None:
        logger.warning(msg)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)


def register_bundle_sys_paths(
    framework_path: str,
    bundle_path: str,
    logger=None,
) -> None:
    """
    Register sys.path roots for framework (local/) then pipeline bundle (src/).

    Framework bundle uses local/ paths (local/libraries/, local/python/).
    Pipeline bundle uses src/ paths (src/libraries/, src/python/).
    Legacy extensions/ is deprecated in both contexts.

    ``logger`` is optional. When omitted, paths are registered silently — useful
    for early bootstrap before the real logger is available.
    """
    # Framework bundle: custom code lives under local/ only
    fw_libraries = os.path.normpath(os.path.join(framework_path, FrameworkPaths.LOCAL_LIBRARIES_PATH))
    fw_python = os.path.normpath(os.path.join(framework_path, FrameworkPaths.LOCAL_PYTHON_PATH))
    fw_legacy = os.path.normpath(os.path.join(framework_path, FrameworkPaths.EXTENSIONS_PATH))
    _add_if_dir(fw_libraries, "framework local/libraries", logger)
    _add_if_dir(fw_python, "framework local/python", logger)
    _warn_legacy_extensions(fw_legacy, fw_python, "framework", logger)

    # Pipeline bundle: custom code lives under src/
    pipe_libraries = os.path.normpath(os.path.join(bundle_path, PipelineBundlePaths.LIBRARIES_PATH))
    pipe_python = os.path.normpath(os.path.join(bundle_path, PipelineBundlePaths.PYTHON_PATH))
    pipe_legacy = os.path.normpath(os.path.join(bundle_path, PipelineBundlePaths.EXTENSIONS_PATH))
    _add_if_dir(pipe_libraries, "bundle src/libraries", logger)
    _add_if_dir(pipe_python, "bundle src/python", logger)
    _warn_legacy_extensions(pipe_legacy, pipe_python, "bundle", logger)


def run_init_scripts(
    framework_path: str,
    bundle_path: str,
    phase: Phase,
    logger,
) -> None:
    """
    Execute all .py lifecycle scripts under the init/<phase>/ directory for framework then bundle.

    Framework bundle uses local/init/<phase>/; pipeline bundle uses src/init/<phase>/.
    Files are sorted by filename; files starting with '_' are skipped.
    Each file is run with runpy.run_path(..., run_name='__main__').
    A script that raises an exception fails the pipeline.

    Args:
        framework_path: Root of the framework bundle (framework.sourcePath).
        bundle_path:    Root of the pipeline bundle (bundle.sourcePath).
        phase:          "pre" (before SDP declarations) or "post" (after).
        logger:         Framework logger instance.
    """
    if phase not in _FRAMEWORK_PHASE_PATH:
        raise ValueError(f"Invalid init phase: {phase!r}. Expected one of {list(_FRAMEWORK_PHASE_PATH)}.")

    label = _PHASE_LABEL[phase]

    for base, level, phase_paths in (
        (framework_path, "framework", _FRAMEWORK_PHASE_PATH),
        (bundle_path, "bundle", _BUNDLE_PHASE_PATH),
    ):
        folder = os.path.normpath(os.path.join(base, phase_paths[phase]))
        if not os.path.isdir(folder):
            continue
        scripts = sorted(
            name for name in os.listdir(folder)
            if name.endswith(".py") and not name.startswith("_")
        )
        for filename in scripts:
            path = os.path.join(folder, filename)
            if not os.path.isfile(path):
                continue
            logger.info("Running %s %s script: %s", level, label, path)
            runpy.run_path(path, run_name="__main__")
