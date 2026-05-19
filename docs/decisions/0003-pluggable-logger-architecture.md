# ADR-0003: Pluggable logger architecture (factory pattern + CompositeLogger)

**Date:** 2026-05-17
**Status:** Accepted
**PR:** feature/pluggable-logger (v0.14.0)

---

## Context

The framework previously used a single hard-coded `logging.Logger` instance
(`lakeflowframework`) writing plain-text records to stdout. Customers with structured
logging infrastructure (Application Insights, Splunk, Datadog, internal JSON
pipelines) had no way to integrate the framework's log output without patching
the framework itself.

Requirements gathered from customer scenarios:

- Zero-code integration for loggers whose factory signature is compatible with
  `factory(dbutils, spark, **kwargs)` — config-only.
- A thin wrapper path for loggers whose signature is incompatible.
- Pipeline-level `logLevel` must propagate to the custom logger.
- Misconfiguration must never crash the pipeline.
- The default logger must remain the out-of-the-box experience — no opt-out
  required from customers who do not need a custom logger.

## Decision

Introduce a **factory-based pluggable logger** configured entirely via
`logger.json` files:

```json
{
  "enabled": true,
  "module": "my_logger_module",
  "factory": "get_logger",
  "level": "INFO",
  "factory_args": {
    "log_to_output": false
  }
}
```

**Resolution sequence** (`src/logger.py`, `resolve_pipeline_logger`):

1. Load `logger.json` from the framework bundle (`src/local/config/` overlay on top of
   `src/config/default/`, or `src/config/override/` if still present — deprecated v0.13.0)
   and the pipeline bundle (`pipeline_configs/`); deep-merge per precedence rules
   (framework wins by default; `allow_pipeline_logger_override: true` inverts).
2. If `enabled` is `false`, return the default `lakeflowframework` stdout logger.
3. If `library` is set and not importable, fall back to the default logger with a
   warning.
4. Import `module`, call `factory(dbutils, spark, **factory_args)`, validate that
   the returned object exposes `debug`, `info`, `warning`, `error`, `critical`,
   and `exception`.
5. On any failure (import error, factory error, invalid return type), fall back to
   the default logger, emit a `CustomLoggerConfigWarning` (Python `warnings` — visible
   in stderr and catchable with `pytest.warns`), and log an `ERROR` record — the
   pipeline never fails due to logging misconfiguration.
6. Apply `mirror_to_stdout` and `CompositeLogger` wrapping (see ADR-0004).

**Resolved log level injection:** before calling the factory the framework
injects the resolved `level` (Spark `logLevel` pipeline setting wins over the
JSON config value) as a `"level"` key in `factory_args`. Custom factories must
declare `level: str = "INFO"` in their signature.

**`sys.path` ordering:** `register_bundle_sys_paths` is called **before**
`resolve_pipeline_logger` so that modules in `src/local/libraries/` are
importable when the factory is loaded. See ADR-0005.

**Custom logger contract:** the object returned by the factory must implement
`debug`, `info`, `warning`, `error`, `critical`, and `exception`
as `(message, *args, **kwargs)`. It must handle `exc_info`, `stacklevel`, and
`stack_info` kwargs (pop and discard the latter two; resolve `exc_info=True` via
`traceback.format_exc()`). Level checks must be applied before message
formatting (lazy evaluation). See `docs/source/feature_logging.rst` for the
full contract table and reference implementation.

## Consequences

- Customers can integrate any logger whose factory accepts
  `(dbutils, spark, **kwargs)` using only `logger.json` — no code changes.
- Customers whose logger requires adaptation write a thin wrapper module in
  `src/local/libraries/` or as a cluster-installed package; `logger.json`
  points to the wrapper.
- Pipeline startup always succeeds regardless of logging misconfiguration.
- The framework default logger (`lakeflowframework` / plain-text stdout) remains the
  default; no action needed from customers who do not require a custom logger.
- The `level` kwarg injection is part of the public factory contract — custom
  logger authors must handle it.
