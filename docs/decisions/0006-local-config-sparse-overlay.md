# ADR-0006: `src/local/config/` sparse overlay replaces `config/override/`

**Date:** 2026-05-17
**Status:** Accepted
**PR:** feature/local-config-resolver-and-override (v0.15.0)

---

## Context

The original framework config mechanism offered a binary choice: use
`config/default/` (shipped defaults) **or** replace it entirely with
`config/override/` (full-tree copy). This had two significant problems:

1. **Whole-tree requirement.** A customer who wanted to change a single key in
   `global.json` had to copy the entire `config/default/` tree into
   `config/override/` and keep it in sync across framework upgrades. A missed
   sync would silently hide new default values.

2. **Coupling to the override tree.** The original resolver treated the presence
   of any non-hidden file in `config/override/` as a signal to use that tree
   exclusively for _all_ framework config reads. Adding a `logger.json` override
   inadvertently activated the override tree for global config, requiring the
   override tree to be complete.

The `src/local/` fork-safe area introduced in ADR-0001 provides a natural home
for customer customisations. Config overrides should follow the same pattern.

## Decision

Introduce `src/local/config/` as a **sparse overlay directory** whose files are
**deep-merged on top of their `src/config/default/` equivalents** at runtime.

**`load_framework_config(name, framework_path)`** — new primary API:

1. Load the full file from `src/config/default/<name>` (always authoritative).
2. If `src/local/config/<name>` exists, deep-merge it on top.
   - Dict values are merged recursively; overlay wins on conflicts.
   - Non-dict values and lists are replaced wholesale.
   - Keys absent from the overlay retain their default values.

**`resolve_framework_config_dir(subdir, framework_path)`** — for directory-based
config (e.g. `dataflow_spec_mapping/`):

1. If `src/local/config/<subdir>/` exists, return it (local wins entirely).
2. Otherwise return `src/config/default/<subdir>/`.

**`resolve_framework_config_path`** (legacy) — emits a `DeprecationWarning`
when `config/override/` contains non-hidden files, then preserves the original
binary-switch behaviour for backward compatibility until v1.0.0 removal.

**Deprecation timeline:**

| Version | Action |
|---------|--------|
| v0.13.0 | `config/override/` deprecated; `DeprecationWarning` added |
| v0.15.0 | `src/local/config/` introduced; all framework call sites migrated to `load_framework_config` |
| v1.0.0 | `config/override/` support and `resolve_framework_config_path` removed |

## Consequences

- A customer who wants to change one key in `global.json` creates a one-field
  `src/local/config/global.json` — no need to maintain a full copy.
- Framework upgrades that add new default keys automatically appear in the
  merged config; only explicitly overridden keys are affected.
- The `logger.json` override (pluggable logger, ADR-0003) now lives in
  `src/local/config/logger.json` rather than `config/override/`.
- The deep-merge is deterministic: default values always form the base; local
  overlay always wins on present keys. No precedence ambiguity.
- Substitutions and secrets files (which include workspace-environment prefixes)
  are not yet covered by `load_framework_config` and continue to use
  `_framework_config_path` until a follow-up PR addresses the workspace-env
  prefix complexity.
