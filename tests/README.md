# Tests

Fast unit tests and slower integration checks for the Lakeflow Framework.

## Quick start

From the repository root (after `pip install --require-hashes --no-deps -r requirements-dev.lock`):

```bash
# Unit tests (default local/CI command)
pytest tests/ -m "not integration and not spark"

# Integration tests (samples layout, validate_dataflows script, feature-samples builder)
pytest tests/ -m integration

# Optional coverage report
pytest tests/ -m "not integration and not spark" --cov=src --cov-report=term-missing
```

Use **Python 3.12** for development; newer Python versions may break PySpark-related dependencies.

## Layout

```
tests/
├── conftest.py          # Shared fixtures (pipeline_context, bundle trees)
├── helpers.py           # make_tree() for temp directory layouts
├── fixtures/            # Minimal JSON/YAML — not full samples/
│   ├── specs/
│   ├── bundles/
│   └── golden/
├── unit/                # Fast, isolated module tests
└── integration/         # Sample-dependent tests (require samples/ checkout)
    ├── conftest.py      # validate_bundle(), bundle paths, feature-samples fixtures
    ├── test_validate_dataflows.py      # Script helpers + all specs per JSON bundle
    └── test_feature_samples_spec_builder.py  # DataflowSpecBuilder on feature-samples
```

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
3. **Mirror `src/`** — `tests/unit/test_<module>.py` maps to `src/<module>.py`.
4. **One concern per test** — name tests `test_<behavior>_when_<condition>`.
5. **No DLT mocks** — tests that need `@dp.table` belong in samples/E2E, not unit tests.

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
