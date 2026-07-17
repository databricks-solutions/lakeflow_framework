# Tests

Fast unit tests and slower integration checks for the Lakeflow Framework.

## Quick start

From the repository root (after `pip install --require-hashes --no-deps -r requirements-dev.lock` or `pip install -e ".[contrib]"`):

```bash
# Unit tests (default local/CI command)
pytest tests/ -m "not integration and not spark"

# Integration tests (samples layout, validate_dataflows script, feature-samples builder)
pytest tests/ -m integration

# Optional coverage report
pytest tests/ -m "not integration and not spark" --cov=lakeflow_framework --cov-report=term-missing
```

Use **Python 3.12** for development; newer Python versions may break PySpark-related dependencies.

## Test architecture

The suite is layered so local runs and CI stay fast by default:

| Layer | Location | Marker | Depends on |
|-------|----------|--------|------------|
| **Unit** | `tests/unit/` | (none) | `tests/fixtures/` only; mocks via `pipeline_context` |
| **Integration** | `tests/integration/` | `integration` | Full `samples/` checkout |

**Import policy:** all tests use `lakeflow_framework.*` imports. The compat shim layer at `src/*.py` is not exercised — see `docs/source/contributor_imports.rst`.


## Layout

```
tests/
├── conftest.py              # Shared fixtures (pipeline_context, bundle trees)
├── helpers.py               # make_tree() for temp directory layouts
├── fixtures/                # Minimal JSON/YAML — not full samples/
│   ├── specs/
│   ├── bundles/
│   └── golden/
├── unit/                    # Fast, isolated module tests
│   └── dataflow/            # mirrors src/lakeflow_framework/dataflow/
└── integration/             # Sample-dependent tests (require samples/ checkout)
```

### Key fixtures (`conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `pipeline_context` | Bootstrap `pipeline_config` singletons with mocks; always use instead of inline `initialize_core()` |
| `framework_package_path` | Path to `src/lakeflow_framework/` (canonical package tree) |
| `framework_src_path` | Path to `src/` (`framework.sourcePath` in flat deploy) |
| `minimal_framework_tree` | Temp tree with default config copied from the package |
| `minimal_bundle_tree` / `dataflow_bundle_tree` / `template_bundle_tree` | Minimal pipeline bundle layouts under `tmp_path` |

## Markers

| Marker | Purpose |
|--------|---------|
| `integration` | Needs `samples/` checkout; validates real bundle specs and builders |
| `spark` | Reserved for future local Spark tests; excluded from default CI |
| `bdd` | Reserved for future pytest-bdd spec-contract scenarios |

Configure in `pytest.ini`. CI runs: `-m "not integration and not spark"`.

## Conventions

1. **Use `pipeline_context`** — do not call `initialize_core()` inline in test modules.
2. **Prefer `tests/fixtures/`** — unit tests should not depend on `samples/` paths.
3. **Mirror the package** — `tests/unit/test_<module>.py` maps to `src/lakeflow_framework/<module>.py`; `tests/unit/dataflow/` mirrors `src/lakeflow_framework/dataflow/`. Use `lakeflow_framework.*` imports (not compat shims). See `docs/source/contributor_imports.rst` for the full policy.
4. **One concern per test** — name tests `test_<behavior>_when_<condition>`.
5. **No DLT mocks** — tests that need `@dp.table` belong in samples/E2E, not unit tests.
6. **Script helpers vs integration** — pure functions from `scripts/validate_dataflows.py` belong in `test_validate_dataflows_helpers.py`; subprocess runs against `samples/` belong in `tests/integration/`.

## CI

Pull requests to `main` run [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

| Job | Runs when |
|-----|-----------|
| **Unit tests** | Always |
| **Docs spelling** | `docs/**` (or docs requirements) changed |
| **Docs HTML** | Same; fails if Sphinx reports more than 19 warnings |
| **Validate sample dataflows** | `samples/**` changed — runs `validate_dataflows.py samples/` |

Sample validation uses `scripts/validate_dataflows.py` directly in CI.
The composite action at `.github/actions/validate-dataflows` is for **downstream repos**.

Local equivalents:

```bash
pytest tests/ -m "not integration and not spark"
pytest tests/ -m integration
make -C docs spelling
bash scripts/ci/docs_html_check.sh 19
python scripts/validate_dataflows.py samples/
```
