"""Framework configuration resolver.

Provides the primary API for loading framework config files with
``src/local/config/`` sparse-overlay support, plus the deprecated
``resolve_framework_config_path`` shim kept for backward compatibility
until v1.0.0.
"""
import os
import warnings
from typing import Dict

from constants import FrameworkPaths


def load_framework_config(
    name: str,
    framework_path: str,
    fail_on_not_exists: bool = True,
) -> Dict:
    """Load a framework config file with ``src/local/config/`` deep-merge overlay support.

    Resolution order:

    1. Load the full file from ``src/config/default/<name>`` (always authoritative).
    2. If ``src/local/config/<name>`` exists, deep-merge it on top.
       Only the keys present in the overlay file are changed — all other keys
       retain their default values (sparse / partial files are supported).

    Args:
        name: Config file name relative to the config root,
              e.g. ``"global.json"`` or ``"operational_metadata_bronze.json"``.
        framework_path: Absolute path to the framework bundle's ``src/`` directory
                        (the value of ``framework.sourcePath``).
        fail_on_not_exists: When ``True`` (default) raise ``FileNotFoundError`` if
                            the default file is absent.  When ``False`` return ``{}``.
    """
    from utility import load_config_file_auto, deep_merge

    default_path = os.path.join(framework_path, FrameworkPaths.CONFIG_PATH, name)
    local_path = os.path.join(framework_path, FrameworkPaths.LOCAL_CONFIG_PATH, name)

    defaults = load_config_file_auto(default_path, fail_on_not_exists=fail_on_not_exists) or {}

    if os.path.exists(local_path):
        overlay = load_config_file_auto(local_path, fail_on_not_exists=False) or {}
        if overlay:
            return deep_merge(defaults, overlay)

    return defaults


def resolve_framework_config_dir(subdir: str, framework_path: str) -> str:
    """Resolve a config subdirectory path, checking ``src/local/config/`` first.

    If ``src/local/config/<subdir>/`` exists it is returned; otherwise falls
    back to ``src/config/default/<subdir>/``.  Useful for directory-based config
    such as ``dataflow_spec_mapping/``.

    Args:
        subdir: Subdirectory name, e.g. ``"dataflow_spec_mapping"``.
        framework_path: Absolute path to the framework bundle's ``src/`` directory.
    """
    local_path = os.path.join(framework_path, FrameworkPaths.LOCAL_CONFIG_PATH, subdir)
    if os.path.isdir(local_path):
        return local_path
    return os.path.join(framework_path, FrameworkPaths.CONFIG_PATH, subdir)


def _has_visible_children(directory: str) -> bool:
    """Return True if *directory* exists and contains at least one non-hidden child."""
    if not os.path.isdir(directory):
        return False
    try:
        names = os.listdir(directory)
    except OSError:
        return False
    return any(not n.startswith(".") for n in names)


def resolve_framework_config_path(framework_path: str) -> str:
    """
    DEPRECATED (v0.13.0): Use ``load_framework_config()`` or ``resolve_framework_config_dir()``
    instead. Removed in v1.0.0.

    Returns FrameworkPaths.CONFIG_OVERRIDE_PATH when the override directory has at least one
    non-hidden child and mirrors the required layout; otherwise FrameworkPaths.CONFIG_PATH.

    Raises:
        FileNotFoundError: If neither default nor override config roots contain valid files,
            or if the override root is active but incomplete.
    """
    config_dir = os.path.join(framework_path, FrameworkPaths.CONFIG_PATH)
    override_dir = os.path.join(framework_path, FrameworkPaths.CONFIG_OVERRIDE_PATH)
    if not _has_visible_children(override_dir):
        if not _has_visible_children(config_dir):
            raise FileNotFoundError(
                f"No valid files found under {FrameworkPaths.CONFIG_PATH} or "
                f"{FrameworkPaths.CONFIG_OVERRIDE_PATH} in the framework bundle "
                f"({framework_path!s}). Please add framework configuration under "
                f"{FrameworkPaths.CONFIG_PATH} (for example a global config file, "
                f"the {FrameworkPaths.DATAFLOW_SPEC_MAPPING} directory, and related files)."
            )
        return FrameworkPaths.CONFIG_PATH

    warnings.warn(
        f"{FrameworkPaths.CONFIG_OVERRIDE_PATH} is deprecated (v0.13.0) and will be removed "
        f"in v1.0.0. Migrate your overrides to {FrameworkPaths.LOCAL_CONFIG_PATH} — only the "
        "keys you want to change are needed (sparse files are supported). "
        "See the framework configuration documentation for migration steps.",
        DeprecationWarning,
        stacklevel=2,
    )

    mapping_dir = os.path.join(override_dir, FrameworkPaths.DATAFLOW_SPEC_MAPPING)
    global_paths = [
        os.path.join(override_dir, name) for name in FrameworkPaths.GLOBAL_CONFIG
    ]
    if not os.path.isdir(mapping_dir) or not any(os.path.isfile(p) for p in global_paths):
        raise FileNotFoundError(
            f"Using {FrameworkPaths.CONFIG_OVERRIDE_PATH} requires both a global config file "
            f"({' or '.join(FrameworkPaths.GLOBAL_CONFIG)}) and the "
            f"{FrameworkPaths.DATAFLOW_SPEC_MAPPING} directory under that path. "
            f"Copy the full {FrameworkPaths.CONFIG_PATH} tree into {FrameworkPaths.CONFIG_OVERRIDE_PATH}."
        )
    return FrameworkPaths.CONFIG_OVERRIDE_PATH
