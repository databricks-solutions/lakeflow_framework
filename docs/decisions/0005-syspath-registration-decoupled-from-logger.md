# ADR-0005: `sys.path` registration decoupled from logger initialisation

**Date:** 2026-05-17
**Status:** Accepted
**PR:** feature/pluggable-logger (v0.14.0)

---

## Context

`DLTPipelineBuilder.__init__` must perform two steps in sequence:

1. Register `src/local/libraries/` and other bundle paths on `sys.path`
   (`register_bundle_sys_paths`) so that custom modules are importable.
2. Resolve the pipeline logger (`resolve_pipeline_logger`), which may import a
   custom logger module from one of those paths.

The original implementation of `register_bundle_sys_paths` required a fully
initialised logger to emit `INFO` messages about which paths were registered.
This created a circular dependency:

- The logger cannot be resolved until `sys.path` is registered (the custom
  logger module may live in `src/local/libraries/`).
- `sys.path` registration required a logger to report what it was doing.

The temporary fix of passing a bare `logging.getLogger` instance worked but
meant the framework always emitted plain-text `INFO` lines during bootstrap
regardless of whether a custom logger was configured — the opposite of the
intent.

## Decision

Make the `logger` parameter **optional** (`logger=None`) in
`register_bundle_sys_paths`, `_add_if_dir`, and `_warn_legacy_extensions`
in `bundle_loader.py`. All logging calls inside these functions are guarded by
`if logger is not None:`.

`DLTPipelineBuilder.__init__` calls `register_bundle_sys_paths` **silently**
(without a logger) early in bootstrap, before `resolve_pipeline_logger` is
called. The log messages about which paths were registered are therefore emitted
only when the caller explicitly passes a logger — for example, during
reregistration triggered by a reload.

```python
# bootstrap order in DLTPipelineBuilder.__init__
self._load_mandatory_paths()
register_bundle_sys_paths(self.framework_path, self.bundle_path)  # silent
self.logger = pipeline_logger.resolve_pipeline_logger(...)        # custom module now importable
self.logger.info("Initializing Pipeline...")
```

## Consequences

- Custom logger modules placed in `src/local/libraries/` are guaranteed to be
  on `sys.path` before the factory import is attempted.
- Bootstrap `sys.path` registration produces no log output. This is acceptable
  because any misconfiguration (missing path, permission error) raises an
  exception rather than a log message.
- Callers that want diagnostic output from `register_bundle_sys_paths` must pass
  a logger explicitly — the function signature is backward-compatible (existing
  callers passing a logger continue to work unchanged).
- Future extensions to `bundle_loader` should follow the same optional-logger
  pattern to avoid reintroducing the circular dependency.
