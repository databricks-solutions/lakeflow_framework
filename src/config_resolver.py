"""Framework configuration resolver.

Provides the primary API for loading framework config files with
``src/local/config/`` sparse-overlay support, plus the deprecated
``resolve_framework_config_path`` shim kept for backward compatibility
until v1.0.0.
"""
import os
import warnings
from typing import Dict, Sequence, Union

from constants import FrameworkPaths


def load_framework_config(
    name: Union[str, Sequence[str]],
    framework_path: str,
    config_path: str = FrameworkPaths.CONFIG_PATH,
    fail_on_not_exists: bool = True,
) -> Dict:
    """Load a config file from *config_path* with ``src/local/config/`` deep-merge overlay.

    The caller is responsible for determining the active base path (override or default)
    and passing it via ``config_path``.  This function contains no override-detection
    logic — it only loads from the given path and applies the ``src/local/config/``
    sparse overlay on top.

    When *name* is a sequence (e.g. ``FrameworkPaths.GLOBAL_CONFIG``), the function
    resolves to the single matching file within ``config_path``, raising ``ValueError``
    if more than one match is found.

    Args:
        name: Config file name (e.g. ``"logger.json"``) **or** a sequence of alternative
              filenames (e.g. ``FrameworkPaths.GLOBAL_CONFIG``).
        framework_path: Absolute path to the framework bundle's ``src/`` directory.
        config_path: Relative path segment for the base config directory, e.g.
                     ``FrameworkPaths.CONFIG_PATH`` (default) or
                     ``FrameworkPaths.CONFIG_OVERRIDE_PATH`` when the caller has
                     determined that the deprecated override directory is active.
        fail_on_not_exists: When ``True`` (default) raise ``FileNotFoundError`` if the
                            base file is absent.  When ``False`` return ``{}``.
    """
    from utility import load_config_file_auto, deep_merge

    base_dir = os.path.join(framework_path, config_path)
    local_dir = os.path.join(framework_path, FrameworkPaths.LOCAL_CONFIG_PATH)

    if not isinstance(name, str):
        names = name
        matches = [n for n in names if os.path.exists(os.path.join(base_dir, n))]
        if len(matches) > 1:
            raise ValueError(
                f"Multiple config files found in {config_path}. "
                f"Only one is allowed: {[os.path.join(base_dir, n) for n in matches]}"
            )
        if not matches:
            if fail_on_not_exists:
                raise FileNotFoundError(
                    f"Config file not found. Expected one of {list(names)} under {base_dir}"
                )
            return {}
        name = matches[0]

    base_path = os.path.join(base_dir, name)
    local_path = os.path.join(local_dir, name)

    defaults = load_config_file_auto(base_path, fail_on_not_exists=fail_on_not_exists) or {}

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
