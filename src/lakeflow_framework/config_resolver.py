"""Framework configuration resolver.

Provides the primary API for loading framework config files and bundled
JSON schemas with ``src/local/config/`` sparse-override support, plus the
deprecated ``resolve_framework_config_path`` shim kept for backward
compatibility until v1.0.0.

Strategy B resolver
-------------------
:func:`load_framework_default_json` implements the canonical two-source
resolution with Workspace Files-first priority:

1. **Workspace Files** — ``{framework_path}/lakeflow_framework/config/default/<name>``
   when *framework_path* is provided and the file exists.  Explicit beats
   implicit: if the customer has deployed the framework files in Workspace
   Files, that copy is used.
2. **Package data** (``importlib.resources``) — always present after
   ``pip install lakeflow-framework``; also resolves correctly for
   flat-deploy when ``src/`` is on ``sys.path`` and the file was not found
   under *framework_path*.
3. **``src/local/config/`` custom override** — deep-merged on top when
   *framework_path* is provided and the sparse fragment exists.

:func:`load_framework_schema` returns an ``importlib.resources`` traversable
for a bundled JSON schema file, suitable for ``jsonschema.RefResolver`` and
similar validators.
"""
import importlib.resources
import json
import os
import warnings
from typing import Dict, Optional, Sequence, Union

from lakeflow_framework.constants import FrameworkPaths


def load_framework_default_json(
    name: str,
    framework_path: Optional[str] = None,
) -> Dict:
    """Load a framework default JSON config file using Strategy B (Workspace Files-first).

    Resolution order:

    1. Workspace Files — ``{framework_path}/lakeflow_framework/config/default/<name>``
       when *framework_path* is provided and the file exists on disk.
    2. Package data — ``importlib.resources`` (wheel install or flat-deploy
       with ``src/`` on ``sys.path``) if disk path is unavailable.
    3. ``src/local/config/<name>`` custom override — deep-merged on top when
       *framework_path* is provided and the sparse fragment exists.

    Args:
        name: Config filename, e.g. ``"global.json"`` or
              ``"operational_metadata_bronze.json"``.
        framework_path: Absolute path to the framework bundle's ``src/``
                        directory.  When ``None`` only package data is used
                        (no custom override merging possible).

    Returns:
        Parsed config dict (base config deep-merged with custom override if present).

    Raises:
        FileNotFoundError: If the file cannot be found either on disk or via
                           ``importlib.resources``.
    """
    from lakeflow_framework.utility import deep_merge

    # 1. Workspace Files-first: explicit framework_path takes priority over package data.
    base: Optional[Dict] = None
    file_path: Optional[str] = None
    if framework_path:
        file_path = os.path.normpath(
            os.path.join(
                framework_path,
                FrameworkPaths.CONFIG_PATH.lstrip("./"),
                name,
            )
        )
        if os.path.isfile(file_path):
            with open(file_path, encoding="utf-8") as fh:
                base = json.load(fh)

    # 2. importlib.resources fallback when disk path absent or no framework_path.
    if base is None:
        try:
            ref = importlib.resources.files("lakeflow_framework").joinpath(
                f"config/default/{name}"
            )
            base = json.loads(ref.read_text("utf-8"))
        except (FileNotFoundError, TypeError, ModuleNotFoundError) as exc:
            raise FileNotFoundError(
                f"Framework default config '{name}' not found on disk ({file_path!r}) "
                f"or via package data."
            ) from exc

    # 3. Sparse local/config override — only when framework_path is known.
    if framework_path:
        override_path = os.path.join(
            framework_path, FrameworkPaths.LOCAL_CONFIG_PATH.lstrip("./"), name
        )
        if os.path.isfile(override_path):
            with open(override_path, encoding="utf-8") as fh:
                override = json.load(fh)
            if override:
                base = deep_merge(base, override)

    return base


def load_framework_schema(name: str):
    """Return an ``importlib.resources`` traversable for a bundled schema file.

    Resolves to ``lakeflow_framework/schemas/<name>`` inside the installed
    package, which is equivalent to the Workspace Files path when ``src/`` is
    on ``sys.path`` (flat deploy) and to wheel package data when installed via
    ``pip install lakeflow-framework``.

    Args:
        name: Schema filename, e.g. ``"main.json"`` or ``"flow_group.json"``.

    Returns:
        An ``importlib.resources.abc.Traversable`` that can be read with
        ``.read_text("utf-8")`` or converted to a ``Path`` via
        ``importlib.resources.as_file()``.

    Example::

        schema = load_framework_schema("main.json")
        data = json.loads(schema.read_text("utf-8"))
    """
    return importlib.resources.files("lakeflow_framework").joinpath(f"schemas/{name}")


def load_framework_config(
    name: Union[str, Sequence[str]],
    framework_path: str,
    config_path: str = FrameworkPaths.CONFIG_PATH,
    fail_on_not_exists: bool = True,
) -> Dict:
    """Load a config file from *config_path* with ``src/local/config/`` deep-merge override.

    The caller is responsible for determining the active base path (override or default)
    and passing it via ``config_path``.  This function contains no override-detection
    logic — it only loads from the given path and applies the ``src/local/config/``
    sparse override on top.

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
    from lakeflow_framework.utility import load_config_file_auto, deep_merge

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
        override = load_config_file_auto(local_path, fail_on_not_exists=False) or {}
        if override:
            return deep_merge(defaults, override)

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
