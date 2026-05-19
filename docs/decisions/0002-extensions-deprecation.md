# ADR-0002: Deprecation of `extensions/`

**Date:** 2026-05-16
**Status:** Accepted
**PR:** feature/init-hooks-extensions-layout (PR1 / v0.13.0) — deprecation warnings
       chore/remove-legacy-paths (PR5 / v1.0.0) — removal

---

## Context

One legacy convention was released in `main` before ADR-0001:

**Flat `extensions/`** — top-level `.py` files under `extensions/` added to `sys.path`
for spec-referenced Python.

A second path (`extensions/libraries/`) was only ever on feature branches and was
**never released to `main`**, so it carries no backward-compat obligation and is
dropped without a deprecation window.

The new canonical path (`src/python/`) was introduced in ADR-0001.

## Decision

| Legacy behaviour | Released? | Action in v0.13.0 | Removed in |
|-----------------|-----------|-----------------|------------|
| Flat `extensions/` on `sys.path` | Yes | Emit `DeprecationWarning` + structured log | **v1.0.0** |
| `extensions/libraries/` on `sys.path` | No | Drop immediately, no deprecation window | **v0.13.0** (this PR) |

**One-minor deprecation window:** deprecated behaviour is removed in the first minor
version after the deprecation warning lands — giving consumers one release cycle to
migrate before the path disappears.

**Migration is mechanical:** move `.py` files from `extensions/` to `src/python/`.
Spec `module` strings in Data Flow Specs are unchanged — both directories are on
`sys.path` during the deprecation window. `extensions/` is registered on `sys.path`
unconditionally when it contains `.py` files, regardless of whether `src/python/`
also exists.

## Consequences

- Consumers on `extensions/` receive a `DeprecationWarning` at pipeline startup from
  `v0.13.0` onwards.
- `extensions/` `sys.path` registration is removed in `v1.0.0`.
- No deprecation warning is emitted for `extensions/libraries/` (never shipped).
