# ADR-0006: `src/local/config/` sparse overlay replaces `config/override/`

**Date:** 2026-05-17
**Status:** Accepted
**PR:** feature/local-config-resolver-and-override (v0.15.0)

---

## Context

The original framework config mechanism offered a binary choice: use
`config/default/` (shipped defaults) **or** replace it entirely with
`config/override/` (full-tree copy). This had three significant problems:

1. **Whole-tree requirement.** A customer who wanted to change a single key in
   `global.json` had to copy the entire `config/default/` tree into
   `config/override/` and keep it in sync across framework upgrades. A missed
   sync would silently hide new default values.

2. **Coupling across config files.** The original resolver treated the presence
   of any non-hidden file in `config/override/` as a signal to use that tree
   exclusively for _all_ framework config reads. Adding a `logger.json` override
   inadvertently activated the override tree for global config, requiring the
   override tree to be complete.

3. **Override logic scattered inside the loader.** The loader (`load_framework_config`)
   was responsible for detecting whether `config/override/` was active, emitting
   deprecation warnings, and loading the correct file. This mixed concerns and made
   the detection logic duplicated at every call site (especially for multi-file
   resolution like `GLOBAL_CONFIG`).

The `src/local/` fork-safe area introduced in ADR-0001 provides a natural home
for customer customisations. Config overrides should follow the same pattern.

## Decision

Introduce `src/local/config/` as a **sparse overlay directory** whose files are
**deep-merged on top of their `src/config/default/` equivalents** at runtime.

### Separation of concerns

Override detection and deprecation warnings are the **caller's responsibility**.
`load_framework_config` is a pure loader with no override logic:

- **`DLTPipelineBuilder._load_framework_global_config`** checks
  `config/override/` for global config files, emits the `DeprecationWarning` if
  active, stores the resolved root in `self._active_config_path`, and passes it
  to `load_framework_config`.  `self._active_config_path` is reused by
  `_setup_operational_metadata` so the override detection only runs once per
  pipeline initialisation.

- **`load_framework_logger_config`** independently checks
  `config/override/logger.json`, emits its own `DeprecationWarning` if active,
  and passes the resolved root to `load_framework_config`.  Logger config is
  detected separately from global config because a customer may have one but
  not the other.

### `load_framework_config` API

```python
load_framework_config(
    name: str | Sequence[str],
    framework_path: str,
    config_path: str = FrameworkPaths.CONFIG_PATH,   # caller-resolved active root
    fail_on_not_exists: bool = True,
) -> Dict
```

Behaviour:

1. When `name` is a **sequence** (e.g. `FrameworkPaths.GLOBAL_CONFIG =
   ("global.json", "global.yaml", "global.yml")`):
   - Find all matching files inside `config_path`.
   - Raise `ValueError` if more than one match is found.
   - Raise `FileNotFoundError` (or return `{}` if `fail_on_not_exists=False`)
     if no match is found.
   - Resolve to the single matching filename and proceed.
2. Load the file from `os.path.join(framework_path, config_path, name)`.
3. If `src/local/config/<name>` exists, **deep-merge** it on top:
   - Dict values merged recursively; overlay wins on conflicts.
   - Non-dict values and lists replaced wholesale.
   - Keys absent from the overlay retain their default values.
4. Return the merged dict.

No override detection. No warnings. Callers pass the already-resolved `config_path`.

### `resolve_framework_config_dir` (directory-based config)

For directory-based config (e.g. `dataflow_spec_mapping/`):

1. If `src/local/config/<subdir>/` exists, return it (local wins entirely).
2. Otherwise return `src/config/default/<subdir>/`.

### `resolve_framework_config_path` (legacy shim)

Kept until v1.0.0 for any external callers. Emits a `DeprecationWarning` when
`config/override/` is active. Framework internals no longer call this.

### Deprecation timeline

| Version | Action |
|---------|--------|
| v0.13.0 | `config/override/` deprecated; `DeprecationWarning` added |
| v0.15.0 | `src/local/config/` introduced; all framework call sites migrated to `load_framework_config`; override detection moved to callers |
| v1.0.0  | `config/override/` support and `resolve_framework_config_path` removed |

## Consequences

- A customer who wants to change one key in `global.json` creates a one-field
  `src/local/config/global.json` — no need to maintain a full copy.
- Framework upgrades that add new default keys automatically appear in the
  merged config; only explicitly overridden keys are affected.
- `config/override/` still works during the deprecation window; a
  `DeprecationWarning` is emitted by the caller (not deep inside the loader),
  giving an accurate stack frame in the pipeline logs.
- The multi-file resolution check (preventing duplicate `global.json` and
  `global.yaml` coexisting) now lives inside `load_framework_config` when a
  sequence is passed — consistent with the pipeline bundle's equivalent check in
  `_load_pipeline_bundle_global_config_file`.
- The `logger.json` override (pluggable logger, ADR-0003) now lives in
  `src/local/config/logger.json` rather than `config/override/`.
- Substitutions and secrets files (which include workspace-environment prefixes)
  are not yet covered by `load_framework_config` and remain on the legacy path
  until a follow-up PR addresses the workspace-env prefix complexity.
