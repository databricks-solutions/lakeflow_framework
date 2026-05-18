# Log Style Fix Plan — `fix/log-fstring-to-percent`

Branch off `main` after `feature/pluggable-logger` merges.

## Background

Python's `logging.Logger` stores `msg` and `args` separately and only evaluates
`msg % args` if the record is actually emitted. f-strings are evaluated at the
call site — before the logger is even called — so level filtering never prevents
the string allocation.

With ~130 f-string log calls concentrated at DEBUG level, every suppressed DEBUG
call still pays the cost of building the string. This is fixed by converting to
`%s` positional args:

```python
# Before (eager — always allocates)
logger.debug(f"Found {len(files)} files for version {target_version}")

# After (lazy — allocates only if DEBUG is active)
logger.debug("Found %d files for version %s", len(files), target_version)
```

## Conversion Rules

| f-string pattern | `%s` equivalent |
|---|---|
| `f"text {var}"` | `"text %s", var` |
| `f"text {obj.__dict__}"` | `"text %s", obj.__dict__` |
| `f"text {len(x)}"` | `"text %d", len(x)` |
| `f"text {val!r}"` | `"text %r", val` |
| `f"text {json.dumps(x)}"` | `"text %s", json.dumps(x)` |
| Multi-line f-string | Split into single `%s` call with all vars as positional args |

> **Note:** `json.dumps()` calls in f-strings at DEBUG level are a double hit —
> both the JSON serialisation and the string interpolation are eager. After
> conversion they remain eager (the positional arg is still evaluated before the
> call). These should stay as `%s` args since there is no way to defer arbitrary
> expressions; the level guard in the custom logger will at least skip
> `_format()` for the string interpolation step.

## Files and Counts

| File | Count | Priority |
|---|---|---|
| `src/dataflow/cdc_snapshot.py` | ~30 | High — all DEBUG |
| `src/dataflow/table_migration.py` | ~20 | High — mostly DEBUG |
| `src/dataflow_spec_builder/spec_mapper.py` | ~15 | High — DEBUG/WARNING |
| `src/dataflow_spec_builder/dataflow_spec_builder.py` | ~12 | Medium — INFO/DEBUG |
| `src/dataflow/sources/delta.py` | ~10 | High — mostly DEBUG |
| `src/dataflow/targets/base.py` | ~8 | Medium — INFO/DEBUG |
| `src/dataflow/dataflow.py` | ~5 | High — DEBUG |
| `src/dataflow/sources/python.py` | ~5 | High — all DEBUG |
| `src/dataflow/table_import.py` | ~5 | Medium — INFO/DEBUG |
| `src/dataflow/targets/sink_foreach_batch.py` | ~4 | Medium — INFO/DEBUG |
| `src/dataflow_spec_builder/template_processor.py` | ~4 | Medium — INFO/DEBUG |
| `src/dataflow/sources/base.py` | ~3 | High — all DEBUG |
| `src/dataflow/sources/kafka.py` | 2 | High — all DEBUG |
| `src/dataflow/sources/batch_files.py` | 2 | High — all DEBUG |
| `src/dataflow/sources/cloud_files.py` | 2 | High — all DEBUG |
| `src/dataflow/sources/sql.py` | 1 | High — DEBUG |
| `src/dataflow/sources/delta.py` | 1 | Low — ERROR |
| `src/dataflow_spec_builder/transformer/materialized_views.py` | 1 | Low — ERROR |

## Implementation Steps

1. Create branch `fix/log-fstring-to-percent` off `main` (post pluggable-logger merge).

2. Work file-by-file in priority order (High first). For each file:
   - Search: `logger\.(debug|info|warning|error|critical|exception)\(f["\']`
   - Convert each match following the conversion rules table above.
   - Pay special attention to multi-line f-strings and chained attribute access.

3. Run the test suite after each file to catch any conversion mistakes:
   ```bash
   pytest tests/ -x -q
   ```

4. Run `make clean && make html` in `docs/` to confirm no doc regressions.

5. Commit with:
   ```
   fix(logging): convert f-string log calls to %s positional args

   f-strings are evaluated eagerly before the logger is called, so level
   filtering never prevents the string allocation. ~130 calls converted,
   ~80% at DEBUG level where the impact is highest.
   ```

## Verification

After the full conversion, confirm no f-string log calls remain:

```bash
rg 'logger\.(debug|info|warning|error|critical|exception)\(f["\']' src/
```

Expected output: no matches.

## Exclusions

- `src/local/libraries/structured_stdout_logger.py` — this is example customer
  code, not framework code. Conversion is optional and at the customer's discretion.
- Any `print(f"...")` statements — handled separately.
- Test files — lower priority; eager formatting in tests is not a concern.
