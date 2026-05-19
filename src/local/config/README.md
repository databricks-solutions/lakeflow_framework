# `src/local/config/`

Fork-safe sparse override directory for framework configuration files.

## How it works

Files placed here are **deep-merged on top of their `src/config/default/`
counterparts** at runtime. You only need to include the keys you want to
change — all other keys retain their default values.

For example, to override a single field in `global.json`:

```json
{
  "dataflow_spec_mapping_version": "0.0.3"
}
```

This is equivalent to the deprecated `config/override/` pattern but with two
key improvements:

- **Sparse files** — no need to copy the entire default file; only include the
  keys being changed.
- **Non-breaking** — keys not present in your override file are never lost.

## Supported files

Any file present in `src/config/default/` can be partially overridden here
using the same filename. Common candidates:

| File | Purpose |
|------|---------|
| `global.json` / `global.yaml` | Global framework configuration |
| `operational_metadata_bronze.json` | Operational metadata schema (bronze layer) |
| `operational_metadata_silver.json` | Operational metadata schema (silver layer) |
| `operational_metadata_gold.json` | Operational metadata schema (gold layer) |
| `logger.json` | Pluggable logger configuration |

For directory-based config (e.g. `dataflow_spec_mapping/`), place the entire
override directory here — the local directory takes full precedence over the
default.

## Migration from `config/override/`

`config/override/` is deprecated (v0.13.0) and will be removed in v1.0.0.

To migrate:

1. Identify which keys in your `config/override/` files differ from
   `config/default/`.
2. Create sparse files here containing only those differing keys.
3. Delete or empty `config/override/`.

## Notes

- This directory is specific to the **framework bundle** (`framework.sourcePath`).
  Pipeline bundles do not have a `local/` directory.
- Files here are **not** committed upstream — they are intended for
  org-specific customisation that stays in your fork.
