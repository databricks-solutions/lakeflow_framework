# Lakeflow framework — repository layout, packaging & bundle `src/` (plan)

**Status:** Living checklist — companion design: [src-libraries-design.md](./src-libraries-design.md).

This plan covers **packaging (`lakeflow_framework`)**, **contrib**, **fork-safe custom areas**, **`src/libraries/`** + **`src/python/`**, **`src/init/pre/`** + **`src/init/post/`**, **templates/samples**, **docs**, **wheels**, and **[recommended PR / branch sequencing](#recommended-pr-and-branch-sequence)** below.

---

## Locked decisions (reference)

| Decision | Value |
|----------|-------|
| Bundle libraries root | **`src/libraries/`** — primary: wheels for DAB `libraries:` YAML; secondary: `sys.path` for loose `.py`/packages (kept) |
| Bundle spec Python root | **`src/python/`** — all customer Python called by Data Flow Specs |
| Init scripts | **`src/init/pre/`** and **`src/init/post/`** |
| Customer sandbox | **`src/local/`** — framework bundle only (`framework.sourcePath`); not in pipeline bundles |
| Config override convention | **`src/local/config/`** — `config/override/` deprecated v0.13.0, removed v1.0.0 |
| Config resolver | **Strategy B** (package-first; disk fallback for flat; sparse `src/local/config/` merge on top) |
| Config defaults in wheel | Mirror `src/config/default/` as package data — PR3 |
| Import style under `src/python/` | Both flat and package layouts documented; customer chooses |
| Legacy `extensions/` on `sys.path` | Deprecated v0.13.0, removed v1.0.0; `extensions/libraries/` never released — drop in PR1 |
| Constants for new paths | `./src/` prefix for new dirs; existing constants stay at bundle root until PR6 |
| PyPI name | **`lakeflow-framework`** |
| Import name | **`lakeflow_framework`** (no short alias convention) |
| Wheel extras | **`[contrib]`**, **`[all]`** — core install is slim |
| Legacy top-level import shims | **Keep until 1.0** — removed at major version bump only |
| Logger / pluggable factory | Handled by separate logging PR; factory modules live under `src/libraries/` per §7.3 |

---

## Recommended PR and branch sequence

**Context:** Major version **0.x** allows breaking changes under semver, but **forked customers** still feel pain from large combined diffs. Prefer small, reviewable PRs and tags so teams can stay on `v0.x.y` until they adopt the next slice.

### What hurts most (order roughly by merge pain)

| Change | Typical fork impact |
|--------|---------------------|
| **`src/libraries/` / `src/python/` / `src/init/`** + templates | Path + scaffold updates; mechanical |
| **`src/local/`** scaffold + `config/override/` deprecation | Low — empty dirs + warnings |
| **`lakeflow_framework` package + import paths** | **High** — notebooks, `%run`, pipeline config |
| **§5.2 + §5.2.1 packaged config defaults + resolver** | **Medium** — behaviour change + deploy docs |

### Suggested PRs

| PR | Branch | Primary phases | Ships in |
|----|--------|----------------|---------|
| **PR1 — Bundle `src/` layout + docs/templates** | `feature/bundle-src-layout` | **A** → **E**, **E2**, **F**, **G**, **D** (scaffold only). New constants + loader for `src/libraries/`, `src/python/`, `src/init/pre/post/`, `src/local/`. Deprecation warnings: flat `extensions/` on `sys.path` and `config/override/`. Drop `extensions/libraries/` (never released). Full Sphinx docs revamp + template/sample migration. | **`v0.13.0`** |
| **PR2 — `lakeflow_framework` package + `contrib`** | `refactor/lakeflow-framework-package` | **B** + **C** + **H** (partial). Package skeleton, `contrib/`, `pyproject.toml` with extras (`[contrib]`, `[all]`), CI wheel build. Compat shims at old import paths kept until 1.0. | **`0.b.0`** |
| **PR3 — Packaged config + §5.2.1 resolver** | `feat/framework-config-resources` | **D2**. `src/config/default/` bundled as wheel package data. Strategy B resolver: package-first, disk fallback, sparse `src/local/config/` deep-merge. Refactor `resolve_framework_config_path`. Unit tests for all three scenarios. | **`0.c.0`** |
| **PR4 — Wheel / CI hardening** | `ci/wheel-smoke` | **H** (remaining). Smoke install in clean venv; any remaining wheel CI polish. | Patch on respective minor |
| **PR5 — Remove legacy paths** | `chore/remove-legacy-paths` | **I** (full). Remove flat `extensions/` `sys.path` registration and `config/override/` support — both deprecated in PR1 / v0.13.0. Ships with **1.0** (extended deprecation window for `extensions/`). | **`v1.0.0`** |
| **PR6 — Full path / constants refactor** | `refactor/bundle-path-constants` | **J**. Move `dataflows/`, `pipeline_configs/`, `python_functions/` etc. under `src/`; update all constants, samples, docs. | **`0.d.0`** |

### One PR vs split

- **PR1 is the must-have** — customers can stay on it indefinitely without merging PR2+.
- **PR5 ships at v1.0.0** — `extensions/` is kept until 1.0 (extended deprecation window).
- **Avoid** combining PR2 + PR3 — package skeleton and config resolver are separable; forked customers benefit from cherry-picking.
- **PR6 is deliberately last** — most file churn, least urgency.

### Git workflow

1. Keep **`main`** releasable after each merge.
2. **Feature branch** from `main` → PR → merge (squash or merge commit per team policy).
3. **Tag** user-facing milestones per `VERSION` / release policy.
4. Forks that want no upstream until ready: pin a tag or use a maintenance branch.

### Versioning sketch (0.x — illustrative)

| Version | Contents |
|---------|---------|
| **v0.13.0** | New `src/` layout + docs; `src/local/` scaffold; `extensions/` and `config/override/` deprecated |
| **0.b.0** | `import lakeflow_framework`, extras `[contrib]`/`[all]`, compat shims (kept to 1.0) |
| **0.c.0** | Packaged `config/default/` + Strategy B resolver + deploy docs |
| **0.d.0** | Full path / constants refactor (PR6) |
| **v1.0.0** | Legacy `extensions/` + `config/override/` removed (PR5); compat shims removed |
| **0.c.0** | Packaged `config/default/` + Strategy B resolver + deploy docs |
| **0.d.0** | Full path / constants refactor (PR6) |
| **1.0** | Legacy top-level import shims removed |

Design cross-link: **§12** in [src-libraries-design.md](./src-libraries-design.md).

---

## Phase A — Inventory

- [ ] List all entrypoints: notebooks, jobs, `DLTPipelineBuilder`, validators, CLI scripts.
- [ ] Map every `sys.path` mutation and legacy import (`utility`, `constants`, `pipeline_config`, …).
- [ ] Map bundle template and each sample: actual paths for `extensions/`, `src/`, `pipeline_configs/`.
- [ ] List all references to `extensions/` paths in code and docs — align with `src/init/pre`, `src/init/post` and new constants.
- [ ] List all `config/override/` references — document migration to `src/local/config/`.

---

## Phase B — Package skeleton (`lakeflow_framework`)

- [ ] Create `src/lakeflow_framework/` with `__init__.py` and `__version__`.
- [ ] Add `pyproject.toml` with `[project.optional-dependencies]`: `contrib` and `all` extras.
- [ ] Move or re-export modules (builder, config, logger, bundle_loader, …) — keep compat shims at old paths until 1.0.
- [ ] Tests: `import lakeflow_framework` from clean env; smoke test critical APIs.
- [ ] Tests: `pip install lakeflow-framework` (core only) does not install contrib deps.

---

## Phase C — `lakeflow_framework.contrib`

- [ ] Add `src/lakeflow_framework/contrib/` + README (support policy, semver rules, "experimental" labelling).
- [ ] Migrate first optional integration (placeholder) or document empty tree until first contrib lands.
- [ ] CI: contrib tests in optional job or gated behind `[contrib]` extra install.

---

## Phase D — Customer / fork-safe areas (`src/local/`)

- [ ] Document **`src/local/`** (locked name) in Sphinx + template README — include §5.1 wheel + overlay pattern: `framework.sourcePath` = on-disk overlay; `lakeflow_framework` from wheel.
- [ ] Specify layout: `src/local/libraries/`, `src/local/python/`, `src/local/init/pre|post/`, `src/local/config/` — mirroring top-level `src/…` roles (design §5, §5.1).
- [ ] Add empty `src/local/.gitkeep` or README in template; do not wire loader until precedence is defined (§5.1 TBD).
- [ ] Document `src/local/config/` as the replacement for `config/override/`; include migration note in CHANGELOG.
- [ ] Optional: template `.gitignore` suggestion for orgs that commit `local/` on their fork.

---

## Phase D2 — Framework config: package defaults + Strategy B resolver (§5.2)

- [ ] Bundle `src/config/default/` (including `global.json`, `operational_metadata_*.json`, `dataflow_spec_mapping/`) as package data inside `lakeflow_framework` wheel.
- [ ] Implement **Strategy B unified resolver** (`load_framework_default_json(name, framework_path)`):
  1. Load from wheel package data via `importlib.resources` (always present after `pip install`).
  2. If wheel not installed (flat deploy): fall back to `{framework_path}/src/config/default/<file>` on disk.
  3. Deep-merge `{framework_path}/src/local/config/<file>` on top if present — **sparse/partial files supported** (customer provides only the keys being overridden; resolver fills remaining keys from defaults).
- [ ] Apply the same resolver pattern for YAML defaults (`global.yaml`/`.yml`) where supported.
- [ ] Refactor `resolve_framework_config_path` / `utility.load_config_file` / logger bootstrap to use unified API; remove duplicated `os.path.join(framework_path, "config/default", …)` at call sites.
- [ ] Unit tests: flat-only (disk fallback), wheel-only (package data), both present (Strategy B merge), sparse override file.
- [ ] Sphinx: wheel deploy guide — overlay contents checklist (what must be on disk vs what comes from wheel).

---

## Phase E — `src/libraries/` + `src/python/` (constants + registration)

- [ ] Add constants: `LIBRARIES_PATH = "./src/libraries"`, `PYTHON_PATH = "./src/python"` to both `FrameworkPaths` and `PipelineBundlePaths`.
- [ ] Add constants: `PRE_INIT_PATH = "./src/init/pre"`, `POST_INIT_PATH = "./src/init/post"`.
- [ ] Implement loader order per design §7.3: framework `src/libraries/` → bundle `src/libraries/` → framework `src/python/` → bundle `src/python/` → legacy flat `extensions/` (deprecated fallback).
- [ ] Wire call order in `DLTPipelineBuilder` / `initialize_pipeline` per §7.3.
- [ ] Emit `DeprecationWarning` + structured log when falling back to flat `extensions/` on `sys.path` (design §7.5); do not add `extensions/libraries/` fallback (never released — omit entirely).
- [ ] Unit tests: temp dirs, idempotent `sys.path`, import smoke for both roots, deprecation warning fires.

---

## Phase E2 — Init scripts (`src/init/pre/` & `src/init/post/`)

- [ ] Add constants for `./src/init/pre` and `./src/init/post` (framework + pipeline; `./src/local/init/pre|post` on framework overlay TBD §5.1).
- [ ] Point `bundle_loader` (or successor) at only these paths — `runpy`, sorted `*.py`, skip `_` prefix — framework bundle before pipeline bundle; match design §7.4.
- [ ] Wire `DLTPipelineBuilder.initialize_pipeline()`: pre runs after `sys.path` registration and before SDP declarations; post runs after declarations (§7.3).
- [ ] No backward-compat path for `extensions/pre_init` / `extensions/post_init` (never released publicly); remove from codebase in this phase.
- [ ] Unit tests: temp dirs, execution order, skipped `_*.py`, failure semantics.

---

## Phase F — Templates & samples

- [ ] `pipeline_bundle_template/`: add `src/libraries/`, `src/python/`, `src/init/pre/`, `src/init/post/`, `src/local/` (empty dirs + README); align with design §7.
- [ ] Update bundle README / `build_pipeline_bundle_structure.rst`.
- [ ] Migrate `bronze_sample` and other samples to new paths; keep flat `extensions/` working with deprecation warning until PR5 removes it.
- [ ] Update sample Data Flow Spec JSON/YAML `module` strings if any reference old extension paths.

---

## Phase G — Sphinx & developer docs

- [ ] **Rewrite `feature_python_extensions.rst`** to cover all three scenarios:
  1. **Cluster library installation** — wheels in bundle (`src/libraries/`), UC Volumes, PyPI, Artifactory/Nexus; customer manages `libraries:` entries in DAB YAML; framework does not auto-generate.
  2. **`sys.path` registration** — `src/libraries/` added to `sys.path` for loose `.py`/packages; no-op for `.whl` files; `src/python/` for spec-referenced modules.
  3. **Spec Python** — flat vs package layout options; when to use each; both supported.
- [ ] New page: **repository layout** (framework bundle vs pipeline bundle; `src/` directory map).
- [ ] Glossary: `src/python/` = "spec Python root"; `src/libraries/` = "bundle libraries root"; init scripts (not "hooks").
- [ ] Document `src/local/` fork-safe pattern and `src/local/config/` sparse override convention.
- [ ] Update `feature_logging.rst` cross-link if logger factory modules live under `src/libraries/` (align with logging PR).
- [ ] Contributor doc: editable install (`pip install -e ".[contrib]"`), wheel release process, extras policy.

---

## Phase H — Wheel / CI hardening

- [ ] CI: build wheel (`python -m build`); smoke install in clean venv; verify `import lakeflow_framework` and `import lakeflow_framework.contrib`.
- [ ] CI: verify `pip install lakeflow-framework` (no extras) does not pull in contrib-only deps.
- [ ] Document customer workflow: flat directory deploy vs `pip install` + `framework.sourcePath` overlay.

---

## Phase I — Cleanup & deprecation removal

- [ ] Remove flat **`extensions/`** `sys.path` registration — deprecated in PR1 / v0.13.0; **removed in PR5 / v1.0.0**. Migration: move files from `extensions/` to `src/python/`; spec `module` strings unchanged.
- [ ] Remove **`config/override/`** support — deprecated in PR1 / v0.13.0; **removed in PR5 / v1.0.0**. Migration: move overrides to `src/local/config/`.
- [ ] `extensions/libraries/` was never released in `main` — already dropped in PR1; no further action here.
- [ ] Compat shims (`utility`, `constants`, `pipeline_config`, etc.) **stay until 1.0** — do not remove in this phase.
- [ ] CHANGELOG entries for all removed paths with migration instructions.

---

## Phase J — Full path / constants refactor (PR6)

- [ ] Move all remaining bundle-root paths under `src/`: `dataflows/` → `src/dataflows/`, `pipeline_configs/` → `src/pipeline_configs/`, `python_functions/` → `src/python_functions/`.
- [ ] Confirm `config/` already at `src/config/` (released); ensure consistency.
- [ ] Update all `PipelineBundlePaths` and `FrameworkPaths` constants to `./src/` prefix consistently.
- [ ] Migrate all samples, templates, and docs to the new paths.
- [ ] Update `validate_dataflows.py` and any scripts that hard-code bundle-root paths.
- [ ] Deprecate old path constants with warning if externally configurable; remove in following minor.
- [ ] CHANGELOG + migration guide entry.

---

## Verification (each milestone)

- [ ] Flat deploy: existing sample pipeline runs unchanged or with documented path change.
- [ ] `pip install -e ".[contrib]"`: notebooks can `import lakeflow_framework` and `import lakeflow_framework.contrib`.
- [ ] `pip install lakeflow-framework` (no extras): contrib deps not installed.
- [ ] Empty `src/libraries/` and empty `src/python/`: no errors on init.
- [ ] Module under `src/python/`: importable for spec resolution after registration.
- [ ] Package under `src/python/`: namespaced module (`myorg.transforms.fn`) importable for spec resolution.
- [ ] Scripts under `src/init/pre/` and `src/init/post/`: discovered and run in correct order (framework then bundle).
- [ ] Deprecation warning fires when `extensions/` flat root used; no warning for `src/python/` or `src/libraries/`.
- [ ] `config/override/` deprecation warning fires; `src/local/config/` override works silently.
- [ ] **Wheel + overlay (§5.1):** with `lakeflow_framework` installed from wheel and `framework.sourcePath` pointing at a minimal overlay containing `src/local/config/` + `src/local/python/`, pipeline initialises and picks up org modules and config from disk.
- [ ] **Strategy B resolver:** defaults resolve correctly for disk-only flat, wheel-only, and both; sparse `src/local/config/` file overrides only the specified keys.

---

## Notes

- Use **design doc** for rationale; this file stays a **checklist**.
- Add PR / issue links next to phases when work starts.
- **Logging PR** (separate branch): align with `src/libraries/` factory module convention and §7.3 init order when merging.
