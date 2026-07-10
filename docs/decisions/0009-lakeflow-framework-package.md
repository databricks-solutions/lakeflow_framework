# ADR-0009: `lakeflow_framework` pip-installable package

**Date:** 2026-05-23
**Status:** Accepted
**PR:** refactor/lakeflow-framework-package (v0.16.0)

---

## Context

The framework shipped as a flat collection of `.py` files directly under `src/`.
Consumers cloned the repository and added `src/` to `sys.path` via
`framework.sourcePath` — effectively a "copy the source" distribution model.

This had three structural problems:

1. **No stable import namespace.** All modules were importable as bare names
   (`from constants import ...`, `from bundle_loader import ...`). Any module
   name in a customer's pipeline bundle could shadow a framework module.

2. **No pip distribution path.** Teams that manage Python dependencies via PyPI,
   a UC Volume, or Artifactory had no clean way to consume the framework. Every
   consumer was forced to clone the repository and re-deploy it as a DAB bundle.

3. **Data files (config, schemas) lived outside any package.** `src/config/default/`
   and `src/schemas/` were loaded via hard-coded `os.path` joins relative to
   `framework.sourcePath`. There was no mechanism to bundle these files with a
   wheel and access them portably.

The project's `pyproject.toml` did not exist; `setup.py` or any standard packaging
entry point was absent.

## Decision

Introduce a proper Python package under `src/lakeflow_framework/` and a
`pyproject.toml` at the repository root.

### Package layout

```
src/
  lakeflow_framework/
    __init__.py                        ← public API + __version__
    constants.py                       ← FrameworkPaths, enums
    config_resolver.py
    bundle_loader.py
    logger.py
    dlt_pipeline_builder.py
    ...
    config/
      default/                         ← bundled default config (package data)
    schemas/                           ← bundled JSON schemas (package data)
    dataflow/
      flows/
    dataflow_spec_builder/
    contrib/
      __init__.py                      ← scaffold; empty until first module lands
      README.rst
```

All imports inside the package use **absolute `lakeflow_framework.*` names**.
No bare imports remain inside `src/lakeflow_framework/`.

### Compat shims

The old flat `src/*.py` locations (e.g. `src/constants.py`,
`src/bundle_loader.py`) are replaced by thin re-export shims:

```python
# src/constants.py  — compat shim, remove at v1.0.0
from lakeflow_framework.constants import *  # noqa: F401,F403
```

Existing pipeline notebooks and bundles that import bare names continue to work
without change until `v1.0.0`.

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "lakeflow-framework"
dynamic = ["version"]
...

[tool.setuptools.dynamic]
version = { file = "VERSION" }

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
lakeflow_framework = [
    "config/default/**/*",
    "schemas/**/*",
]
```

`VERSION` is the single source of truth for the release version; both
`importlib.metadata` (wheel installs) and a direct file read (editable / flat
deploy) converge on it.

### `contrib` subpackage

`src/lakeflow_framework/contrib/` is introduced as a scaffold with an empty
`__init__.py` and a support-policy `README.rst`. No modules land in this PR.
See `docs/decisions/0009-*` (this file) for the publish model and
`docs/source/contributor_contrib.rst` for the contributor guide.

### Optional extras

```
pip install lakeflow-framework          # core only
pip install "lakeflow-framework[contrib]"   # + future contrib extras
pip install "lakeflow-framework[all]"       # everything
```

The `contrib` extra is currently empty; installing it is a no-op until a contrib
module is added.

### Deprecation timeline

| Version | Action |
|---------|--------|
| v0.16.0 | `src/lakeflow_framework/` package introduced; bare `src/` imports still work via shims |
| v1.0.0  | Compat shims at old flat `src/*.py` paths removed |

## Consequences

- Teams can now `pip install lakeflow-framework` from PyPI, a UC Volume, or
  Artifactory. The wheel bundles default config and schemas; no separate file
  deployment is required.
- The `lakeflow_framework.*` import namespace is globally unique; no shadow-import
  risk with customer code.
- Existing flat-deploy customers are unaffected: the `src/` shims preserve
  backward compatibility, and `framework.sourcePath` + disk-first resolution
  (ADR-0010) means behaviour is identical to pre-v0.16.0.
- Editable installs (`pip install -e ".[contrib]"`) are supported for local
  development; the `src/` layout ensures the installed package and the source
  tree are the same directory.
- `docs/conf.py` reads `release` from the `VERSION` file at build time — the
  version shown in HTML headers is always current without manual edits.
