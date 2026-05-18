# ADR-0001: Canonical pipeline bundle `src/` layout

**Date:** 2026-05-16
**Status:** Accepted
**PR:** feature/init-hooks-extensions-layout (PR1 / v0.13.0)

---

## Context

The framework previously used a single `extensions/` tree for both importable Python
modules and lifecycle scripts. This caused:

- No separation between "code that gets installed on the cluster" and "code that spec
  references by module path".
- No clear, fork-safe area for customer customisation.
- Ambiguity between `extensions/` (sys.path) and `extensions/libraries/` (a variant
  that was never released to `main`).

OSS consumers also expected a predictable, documented `src/` layout rather than a
single catch-all directory.

## Decision

Introduce a canonical `src/` layout for pipeline bundles:

| Path | Role |
|------|------|
| `src/libraries/` | **Optional** location for wheel files bundled with the pipeline. The directory is also added to `sys.path` for loose `.py` / packages (secondary role). |
| `src/python/` | All customer Python referenced by Data Flow Specs (`pythonModule`, `pythonTransform.module`). Added to `sys.path`. |
| `src/init/pre/` | Lifecycle scripts run **before** SDP declarations inside `initialize_pipeline()`. |
| `src/init/post/` | Lifecycle scripts run **after** SDP declarations. |

The **framework bundle** (`framework.sourcePath`) follows a different layout — custom
code lives exclusively under `src/local/`:

| Path | Role |
|------|------|
| `src/local/libraries/` | Org-wide cluster-install wheels / loose `.py` (sys.path). |
| `src/local/python/` | Org-wide spec-referenced Python (sys.path). |
| `src/local/init/pre/` | Org-wide pre-init lifecycle scripts. |
| `src/local/init/post/` | Org-wide post-init lifecycle scripts. |

Pipeline bundles do **not** have a `src/local/` directory.

**Init script execution model:** `runpy.run_path(..., run_name='__main__')`, sorted
filename order, files starting with `_` skipped. Framework bundle scripts run before
pipeline bundle scripts at each phase.

**Naming:** These directories are called **"init scripts"** (not "hooks") in all
user-facing documentation to avoid confusion with callback-registration APIs.

**`src/local/` name rationale:** Follows the `git config --local` / Django
`local_settings.py` convention — "local" signals "not for upstream".

## Consequences

- Cluster library installation is handled via the DAB pipeline **`environment.dependencies`**
  section — the framework is not involved. Customers choose from any supported source:

  | Source | Example `environment.dependencies` entry |
  |--------|------------------------------------------|
  | Bundle wheel (file in `src/libraries/`) | `- /Workspace/${workspace.file_path}/src/libraries/my_pkg.whl` |
  | UC Volumes path | `- /Volumes/catalog/schema/my_pkg.whl` |
  | PyPI | `- requests>=2.28` |
  | Artifact repo (Artifactory/Nexus) | `- https://artifactory.example.com/my_pkg.whl` |

  `src/libraries/` is only needed when the wheel is bundled alongside the pipeline
  code. It is **not** required if libraries are sourced from PyPI, UC Volumes, or an
  artifact repository.
- New bundles should place spec-referenced Python in `src/python/` and cluster-install
  artefacts in `src/libraries/` (if bundled).
- The `pipeline_bundle_template/` and samples are migrated to this layout in this PR.
- Existing bundles using `extensions/` continue to work until `v1.0.0` (see ADR-0002).
