# ADR-0004: `mirror_to_stdout` defaults to `false`; default logger silenced when custom logger is active

**Date:** 2026-05-17
**Status:** Accepted
**PR:** feature/pluggable-logger (v0.14.0)

---

## Context

When a custom logger is active there are two potential sources of stdout output:

1. The custom logger itself (e.g. structured JSON written via `print()`).
2. The `lakeflowframework` Python `logging.Logger` which was already writing
   plain-text lines to stdout before the custom logger existed.

Without an explicit policy both sources emit simultaneously, producing duplicate
or mixed-format output in the Databricks pipeline **Logs** UI. This is
confusing and wastes log ingestion quota for customers routing logs to external
systems.

Two use-cases must be supported:

- **Custom logger owns stdout** — structured JSON only; plain-text lines from
  the default logger must be suppressed.
- **Dual output** — custom logger forwards to an external system _and_ the
  plain-text stdout mirror is retained for easy in-UI inspection
  (`mirror_to_stdout: true`).

## Decision

`mirror_to_stdout` defaults to **`false`**.

When a custom logger initialises successfully and `mirror_to_stdout` is `false`
(default):

- All handlers are removed from the `lakeflowframework` `logging.Logger` instance.
- A `logging.NullHandler` is attached so any code holding a direct
  `logging.getLogger("lakeflowframework")` reference stays quiet.
- The custom logger is returned directly — it is the sole output path.

When `mirror_to_stdout` is `true`:

- The custom logger is wrapped in a **`CompositeLogger`** together with the
  default `lakeflowframework` stdout handler.
- Every log call is forwarded to the custom logger first (primary), then to the
  default logger (mirror).
- `CompositeLogger` passes `*args` and `**kwargs` through to the mirror logger
  unchanged so formatting and metadata are not lost.
- `CompositeLogger.close()` closes both loggers.

When the custom logger fails to load, `mirror_to_stdout` has no effect — the
default logger is returned unchanged.

## Consequences

- Customers whose custom logger writes to stdout will not see duplicate lines by
  default.
- Customers who want dual output set `mirror_to_stdout: true` and (if their
  custom logger also writes to stdout) suppress that output via a factory arg
  (e.g. `log_to_output: false`).
- The `lakeflowframework` `logging.Logger` instance is modified in-place when
  silenced. Any code that obtained a direct `logging.getLogger("lakeflowframework")`
  reference before logger resolution will stop producing output — this is the
  intended behaviour.
- `mirror_to_stdout: false` is the breaking change relative to the previous
  hard-coded stdout logger. Teams relying on plain-text stdout output and also
  enabling a custom logger must set `mirror_to_stdout: true` explicitly.
