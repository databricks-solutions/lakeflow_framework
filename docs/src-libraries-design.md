# Lakeflow framework — repository layout, packaging & bundle `src/` (design draft)

**Status:** Decisions locked — implementation backlog in [src-libraries-plan.md](./src-libraries-plan.md). Further iterations should update the plan doc first.

This document covers **packaging** (`lakeflow_framework`, contrib, flat vs wheel), **fork-safe custom areas**, and the **pipeline / framework bundle `src/` layout** — with these **locked** paths under each bundle’s **`src/`** (see table below).

---

## Naming decisions (locked)

| Path | Role |
|------|------|
| **`src/libraries/`** | **Cluster-level library installation** (primary): recommended location for wheels referenced in DAB `libraries:` YAML (bundle wheels, UC Volumes, PyPI, Artifactory/Nexus). Also added to `sys.path` for loose `.py` / packages (secondary role — kept; see §7.1). |
| **`src/python/`** | **Custom Python used by Data Flow Specs** — modules referenced via spec `module` / python_function paths. This is **not** the Python interpreter; in docs/glossary, call it **“spec Python”** or **“dataflow spec Python”** to avoid confusion. |
| **`src/init/pre/`** | **Pre-initialisation** scripts for notebook / pipeline Python: executable **`.py`** files run **before** SDP declarations inside `initialize_pipeline` (semantics: **`runpy`**, sorted order, skip names starting with **`_`** — align with implementation). Framework bundle runs before pipeline bundle. |
| **`src/init/post/`** | **Post-initialisation** scripts: same execution model, run **after** SDP declarations in `initialize_pipeline`. Framework bundle runs before pipeline bundle. |

**Naming note:** use **“init”** (and **pre** / **post**), not **“hooks”**, for these directories — they are **lifecycle scripts**, not callback-registration hooks.

**Rejected for this layout (unless revised):** `src/vendor/`, `src/packages/`, `src/lib/` for the early-registration root — rationale unchanged (see previous revision history). **`dataflow_python/`** was considered; **`python/`** was chosen for brevity **with the glossary rule above**.

**Prerelease:** init has **not** been released to consumers yet — **no backward-compatibility requirement** for older paths such as `extensions/pre_init/`; implementation should target **`src/init/pre/`** and **`src/init/post/`** only unless internal pilots dictate otherwise.

---

## 1. Problem statement

Today the framework is often consumed as a **copied directory** on `sys.path` (flat modules under a `src/` tree), while OSS consumers increasingly expect a **named package**, optional **wheels**, and clear places for:

- **Core** maintained upstream,
- **Official but non-core** extensions,
- **Customer / org customisation** that survives `git merge` from upstream without living inside core,
- **Pipeline bundle** layout: **libraries**, **spec Python**, **init scripts** (`init/pre`, `init/post`), and notebooks under a single **`src/`** story — without overloading a single **`extensions/`** tree for unrelated concerns.

This design describes **target shape** and **relationships**; exact migration steps live in the plan.

---

## 2. Two consumption modes (both first-class)

| Mode | What the customer does | What the framework assumes |
|------|-------------------------|----------------------------|
| **A. Flat / uncompiled directory** | Deploy a checkout (or sync) whose root is passed as `framework.sourcePath` / `bundle.sourcePath`. Notebook extends `sys.path` (or equivalent) to import the framework. | Imports may use **compat shims** during transition (`utility` → `lakeflow_framework.util`, etc.). |
| **B. Wheel (optional)** | `pip install lakeflow-framework` (or a private wheel) and/or attach wheels via Databricks **pipeline `libraries:`**. | Primary import path is **`import lakeflow_framework...`**. Path injection may be reduced or skipped when libraries are supplied only via wheels (**TBD** flag / contract). |

**Principle:** One **source tree** should support **both** modes; wheels are a **build artefact**, not a separate codebase.

---

## 3. Installable core package: `lakeflow_framework`

**Target:** Move implementation code under a real Python package:

```text
src/
  lakeflow_framework/
    __init__.py
    ...                    # core: builder, spec builder, pipeline_config, etc.
```

- **Public API** surface should be documented (even if v1 is “best effort”).
- **Internal modules** may use a leading underscore or `_internal` **TBD**.

**Flat-mode compatibility:** thin modules at legacy locations (e.g. `src/utility.py`) re-export from `lakeflow_framework` until notebooks and samples migrate (removed at **1.0** — see §11).

---

## 4. Official non-core: `lakeflow_framework.contrib`

**Purpose:** Code that **ships with the project** and is **importable** but is **not** part of the narrow core API (heavier deps, optional integrations, slower stability promises).

```text
src/lakeflow_framework/contrib/
  __init__.py
  README.rst               # policy: semver rules, “experimental” labelling, etc.
  ...
```

**Distinction from customer code:** `contrib` is **versioned with the wheel** and lives in the **same repo** as core. Customer-only code does **not** go here.

---

## 5. Customer / org customisation (fork-merge safe)

**Goal:** Upstream merges should not routinely delete or conflict with **local policy and wrappers**.

Recommended pattern (**`src/local/` locked** — see §9):

```text
<framework_bundle_or_checkout>/
  src/
    lakeflow_framework/      # upstream-owned — merge from origin here (or supplied only via wheel — see §5.1)
    local/                   # customer-owned — documented as “do not upstream”; optional .gitignore template
      README.md
      config/                # sparse override fragments (locked — §5.2); replaces config/override/
      libraries/             # org-specific wheels / loose .py (sys.path registered)
      python/                # org-specific pipeline logic modules (sys.path registered)
      init/
        pre/                 # org-specific pre-init lifecycle scripts
        post/                # org-specific post-init lifecycle scripts
  config/
    override/                # DEPRECATED (v0.13.0) — migrate to src/local/config/; removed in v1.0.0
```

**Framework bundle: `src/local/` only.** The framework bundle does **not** use top-level `src/libraries/`, `src/python/`, or `src/init/` — those directories belong to the **pipeline bundle** layout. All customer code in the framework bundle lives exclusively under `src/local/`.
Alternatives: **git submodule** mounted at `local/`, or a **separate private package** that depends on `lakeflow_framework`. The design only requires **one documented sandbox** outside `lakeflow_framework/` for long-lived custom Python.

### 5.1 Wheel installs vs framework `local/` + `libraries` / `python` / `init`

**Problem:** `src/libraries/`, `src/python/`, and `src/init/…` are **directories on disk**. A **wheel** only installs importable packages under **`site-packages/`**; it does **not** give customers a writable tree for org-specific **`python/`** modules or **`init/`** scripts unless you treat those as package **data** (unusual for frequently edited pipeline code).

**Recommended model (wheel customers):**

1. **`pip install lakeflow-framework`** (or a private wheel) — provides **`lakeflow_framework`** **code** only.
2. **`framework.sourcePath`** continues to point at a **filesystem directory** used as the **framework deployment overlay** — same role as today for **on-disk config** (see **§5.2** for splitting defaults vs overrides) and optional **`src/local/…`**. This directory is **not** the wheel; it is usually a **small workspace folder** (Repos, volume, or repo checkout) that contains **overrides** and **customer trees** (and may omit a full **`config/default/`** once defaults ship in the wheel — after **PR3**).
3. Under that overlay, customers place all custom code under **`src/local/`** — the only supported location for custom code in the framework bundle:

   ```text
   <framework_overlay>/src/local/libraries/   # org-specific wheels / loose .py
   <framework_overlay>/src/local/python/      # org-specific pipeline logic modules
   <framework_overlay>/src/local/init/pre/    # org-specific pre-init scripts
   <framework_overlay>/src/local/init/post/   # org-specific post-init scripts
   ```

4. The framework **loader** (when implemented) registers **`src/local/{libraries,python,init/…}`** as the framework-side roots for custom code. There are no top-level `src/libraries/`, `src/python/`, or `src/init/` directories in the framework bundle.

**Why this works with wheels:** `resolve_framework_config_path(framework_path)` and init/spec registration already key off **`framework.sourcePath`** as a **path on disk**. The wheel satisfies **`import lakeflow_framework`**; the overlay satisfies **“where are my org’s `logger.json`, `python/` transforms, and `init/` scripts?”** No need to pack editable **`python/`** trees into the wheel.

**Notebook / job setup (document in deploy guides):**

- Install the wheel (cluster / pipeline **`libraries:`** or `%pip`).
- Set **`framework.sourcePath`** to the **overlay** directory. It **must** supply whatever **config merge** requires: today a full **`config/`** tree on disk; after **PR3**, only sparse override fragments in **`src/local/config/`** are needed when defaults load from the wheel — **`config/default/`** on disk becomes optional for wheel-based installs.
- Ensure the notebook (or cluster) can **`import lakeflow_framework`** (wheel) **and** pass the overlay path into Spark conf so the builder loads JSON and **`src/local/…`** from disk.

**Anti-pattern:** Pointing **`framework.sourcePath`** only at **`site-packages/.../lakeflow_framework`** — that tree is **not** a substitute for **`config/`** and is a poor place for org **`python/`** and **`init/`** edits. **Do not** document that as supported.

**Entry point notebook (customer responsibility):** The current `dlt_pipeline.ipynb` uses `%pip install -r ../requirements.txt` (relative to `src/`) and a flat `from dlt_pipeline_builder import ...`. Customers moving to a wheel deploy must maintain their own copy of the entry point notebook that replaces these with `%pip install lakeflow-framework==x.y.z` and `from lakeflow_framework.dlt_pipeline_builder import DLTPipelineBuilder`. The framework does not ship a separate wheel-variant notebook — this is a customer-owned migration step.

**Open (implementation):** exact **merge / precedence** when both **`src/libraries/`** and **`src/local/libraries/`** exist on the framework overlay **TBD**.

### 5.2 Framework configuration: package **defaults** + overlay / **`local`** **overrides**

**Intent:** Align with wheels: **ship canonical defaults inside `lakeflow_framework`** (package data or `importlib.resources`), and keep **customer-specific and fork-safe changes only on disk** under the **`framework.sourcePath`** overlay — ideally under **`src/local/`** so upstream merges rarely touch them.

**Serialization (current scope):** use **JSON** for packaged defaults and for **`src/local/config/`** fragments where applicable; keep **YAML** only where the framework already supports it today (e.g. `global.yaml`). **TOML as a config carrier is not in scope** unless this section is revised later.

| Layer | Location (target) | Role |
|-------|-------------------|------|
| **Defaults** | **`lakeflow_framework`** package tree, e.g. **`lakeflow_framework/config/default/`** (or equivalent) bundled in the **wheel** | Versioned with the release; read-only at runtime; always available after **`pip install`**. |
| **Overrides** | **`src/local/config/`** (locked — see §11); **`config/override/`** deprecated v0.13.0, removed v1.0.0 | JSON/YAML (and **`logger.json`**) fragments that **deep-merge** over or replace slices of defaults — same rules as today’s `global.json` merge. |

**Merge semantics (locked):** build a **base defaults** dict using **§5.2.1** (Strategy B), then **deep-merge** `src/local/config/` files on top so later layers win on conflict. Override files are **sparse / partial** — a `src/local/config/global.json` containing only the keys being changed is valid and sufficient; the resolver fills in all other keys from the base defaults. Customers must **never** need to copy an entire defaults file just to change one setting.

### 5.2.1 Unified default loading — **disk** (`framework.sourcePath`) **and** **package** (wheel)

**`importlib.resources` alone is not enough** for all deployments: it only reads files **inside the installed package**. A **flat checkout** often has **`{framework.sourcePath}/config/default/*.json`** on disk while code is on **`sys.path`** without those JSON files being visible as package resources. The framework therefore exposes **one logical “read this default file” path** (e.g. `global.json`, `logger.json`) implemented as a **small resolver** — not two parallel call sites.

**Resolved — Strategy B (package-first) locked:**

| Strategy | Order | Best for |
|----------|--------|----------|
| **A. Disk-first** | If **`{framework_path}/config/default/<file>`** exists → read from disk; **else** → read packaged **`lakeflow_framework/config/default/<file>`** via **`importlib.resources`**. | **Pure flat clones** that never `pip install` the framework; disk is authoritative when present. |
| **B. Package-first** | Load **packaged** default (after **`pip install`** it always exists); if **`{framework_path}/config/default/<file>`** exists on disk → **deep-merge** so **disk wins** on overlapping keys (dev / fork parity). | **Wheel + overlay** where the wheel is source of truth but a checkout can **override** defaults without copying the whole tree. |

**Flat-only (no wheel):** strategy **A** behaves naturally: only disk is used if packaged data is absent or not installed. **Wheel + minimal overlay:** strategy **B** gives defaults from the wheel and deltas from **`src/local/config/`** (or **`config/override/`** until removed in v1.0.0) without duplicating **`config/default/`** in Repos.

**YAML:** apply the same resolver pattern for `global.yaml` / `global.yml` where supported — try disk path under **`config/default/`**, then packaged analogue **TBD**.

**Implementation touchpoints:** centralise in one module (e.g. `load_framework_default_json(name, framework_path)`) used by **`resolve_framework_config_path`**, **`utility.load_config_file`**, and logger/config bootstrap — **replace ad-hoc `os.path.join(framework_path, "config/default", …)`** at call sites over time **TBD**.

**Benefits for wheel customers:** no need to copy the entire **`config/default/`** tree into Repos; the overlay carries **only** org deltas under **`src/local/`**.

---

## 6. Two “bundles” and one mental model

| Bundle | Spark conf | Role |
|--------|------------|------|
| **Framework bundle** | `framework.sourcePath` | Carries framework code + framework `config/` + optional **`src/libraries/`**, **`src/python/`**, **`src/init/pre/`**, **`src/init/post/`**. |
| **Pipeline bundle** | `bundle.sourcePath` | Carries pipeline specs, `pipeline_configs/`, `src/` (**libraries**, **python**, **init/pre**, **init/post**, notebooks). |

Both are **directories** in mode A; either may additionally publish **wheels** in mode B.

---

## 7. Canonical `src/` layout (pipeline bundle)

**Target tree** (init script paths **locked** — §7.4):

```text
<pipeline_bundle>/
  src/
    libraries/                 # Early-registered bundle libraries (locked name)
    python/                    # Data Flow Spec–referenced Python (locked name)
    init/
      pre/                     # Pre–SDP-declaration init scripts (runpy)
      post/                    # Post–SDP-declaration init scripts (runpy)
    pipeline_configs/
    dataflows/
    python_functions/
    notebooks/                 # optional subfolder; or notebooks at src/ root — template decision
    ...                        # e.g. dlt_pipeline.ipynb
```

### 7.1 `src/libraries/` (bundle libraries — cluster install + optional `sys.path`)

**Primary role — cluster-level library installation:** `src/libraries/` is the **recommended location** for wheels and packages that need to be **installed on the cluster** via the SDP / Databricks Asset Bundle pipeline `libraries:` mechanism. Customers reference wheels from their `resource.yaml` / DAB YAML directly:

```yaml
pipelines:
  my_pipeline:
    libraries:
      - whl: ./src/libraries/my_package.whl
```

This supports all Databricks pipeline library sources — **wheels in the bundle**, **UC Volumes paths**, **PyPI**, and **artifact repositories** (Artifactory, Nexus, etc.) — because the DAB `libraries:` YAML is the install mechanism; the framework is not involved in installation.

**Secondary role — `sys.path` registration:** The framework also adds `src/libraries/` to `sys.path` so loose `.py` modules and packages placed there are directly importable without installation. This is a no-op for `.whl` files (wheels require cluster install via `libraries:` YAML). Both roles coexist: a `libraries/` directory can hold wheels referenced in DAB YAML **and** loose Python modules on `sys.path` at the same time.

**Resolved — contents:** May contain **wheels** (`.whl`), top-level **`*.py`** modules, and **packages** (directories with `__init__.py`). Invalid layouts (e.g. `foo.py` next to a `foo/` package directory) are Python import errors — the framework does not validate or police this; it is **up to the customer** to keep a coherent tree.

**Framework responsibility (no cross-root shadowing):** The framework registers `src/libraries/` and `src/python/` as **separate** directories in a **fixed, documented order** (see §7.3). It does **not** support merging both roles into one registered path or making the same import name resolve from two framework-managed trees for the same bundle.

### 7.2 `src/python/` (Data Flow Spec–referenced Python)

- **Purpose:** All customer-written importable Python **referenced by Data Flow Specs** — sources, transforms, sinks, and shared utility modules supporting those transforms. This is the single home for spec `module` / `pythonModule` / `pythonTransform.module` resolution. There is **no load-order reason** to split customer Python between `libraries/` and `python/` — both are registered on `sys.path` before any spec module executes, so modules in either root can freely import from the other. The separation exists to distinguish **"what gets installed on the cluster"** (`libraries/`) from **"what spec references by module path"** (`python/`).
- **`sys.path`:** The framework adds `src/python/` (framework bundle then pipeline bundle) so modules are importable as top-level names.
- **Glossary:** In all user-facing docs, define `src/python/` explicitly as **"spec Python root"**, not "the Python language" or `python_functions/`.

**Resolved — import style (§11):** Both **flat** and **package** layouts are supported and documented. Each pipeline only sees two `src/python/` roots (framework bundle + its own pipeline bundle), so collision risk is limited. Documentation should present both options with guidance on when to use each:

| Layout | Example spec string | When to use |
|--------|-------------------|-------------|
| **Flat** — top-level `.py` files directly under `src/python/` | `transforms.customer_aggregation` | Simple bundles with few modules; matches current sample style; short, readable spec strings. |
| **Package** — org-namespaced subdirectory with `__init__.py` | `myorg.transforms.customer_aggregation` | Larger bundles with many modules; avoids name collisions between framework-supplied and bundle-supplied spec Python; scales better as the module count grows. |

Both layouts coexist freely within a single `src/python/` root. The framework recommends **packages** when the bundle ships both framework-side and pipeline-side spec Python, and **flat** for simple single-bundle pipelines.

**Documentation note (§11 / Phase G):** Existing docs, samples, and `feature_python_extensions.rst` must be **revamped** to clearly cover all three scenarios:

1. **Cluster library installation** — wheels, PyPI packages, UC Volume paths, artifact repo paths (Artifactory, Nexus) declared in `resource.yaml` / DAB `libraries:` YAML; `src/libraries/` as the recommended in-bundle location for wheel files referenced there. Customer manages all `libraries:` entries in YAML — the framework does not auto-generate them.
2. **`sys.path` registration for `src/libraries/`** — kept for loose `.py` files and packages (see §7.1); document the distinction from cluster installation via `libraries:` YAML and clarify this is a no-op for `.whl` files.
3. **Spec Python under `src/python/`** — customer modules and packages (transforms, sources, sinks, shared utilities) called by Data Flow Specs via `pythonModule` / `pythonTransform.module`.

### 7.3 Recommended init order (**partially locked** — steps 5 & 7 paths fixed in §7.4; logger ordering still **TBD**)

1. Mandatory Spark conf / paths resolved  
2. **`src/libraries/`** (framework then bundle) — **before** logger if logger must import from here **TBD**  
3. Logger / other early plugins **TBD**  
4. **`src/python/`** registered on `sys.path`; flat **`extensions/`** also registered (**deprecated** — see §7.5) if present, for backward compatibility with existing bundles  
5. **`src/init/pre/`** — run framework scripts, then bundle scripts (sorted `*.py`, **`_` prefix skipped**)  
6. SDP declarations / rest of `initialize_pipeline`  
7. **`src/init/post/`** — same framework-then-bundle ordering  

### 7.4 Init phases (`src/init/pre/` & `src/init/post/`) — **locked**

- **Purpose:** Notebook / pipeline **lifecycle scripts** around `DLTPipelineBuilder.initialize_pipeline()`: **pre** runs before SDP table/view declarations; **post** runs after. Same semantics as today’s **`runpy.run_path`** approach, **new canonical paths only** (this feature is **not** released yet — no requirement to keep **`extensions/pre_init/`** / **`extensions/post_init/`**).
- **Framework vs pipeline:** For each phase, execute **all** eligible scripts under the **framework** bundle’s `src/init/{pre|post}/` first, then the **pipeline** bundle’s — **sorted filename order** within each root.
- **Docs / product language:** Prefer **“init scripts”** or **“init phases”**; avoid **“hooks”** to reduce confusion with callback-style APIs.

### 7.5 Backwards compatibility: legacy `extensions/` on `sys.path`

**Policy:** The only released legacy behaviour is **flat `extensions/`** added to `sys.path` (top-level `.py` files directly under `extensions/`). The `extensions/libraries/` subfolder convention was **never released** (branch-only) and carries no backward-compat obligation. New bundles should use **`src/python/`** for spec Python and **`src/libraries/`** for cluster-install artefacts and loose shared modules.

**Removal timeline (locked):** deprecation warning ships in **PR1 / v0.13.0** (when `src/python/` and `src/libraries/` land); flat `extensions/` `sys.path` support is **removed in the following minor release (v1.0.0)**. Migration is mechanical: move files from `extensions/` to `src/python/`; spec `module` strings in Data Flow Specs are unchanged.

| Legacy behaviour | What is on `sys.path` | Status |
|------------------|----------------------|--------|
| **Flat `extensions/`** | The `extensions/` directory root (top-level `*.py` files) | **Deprecated** — emit `DeprecationWarning` + structured log in **v0.13.0**; **removed in v1.0.0**. |
| **`extensions/libraries/`** | N/A — never shipped in `main` | **No backward-compat obligation** — drop without deprecation window. |

**Implementation note (current code):** `bundle_loader.add_extensions_libraries_to_sys_path` prefers **`extensions/libraries/`**; if missing, it falls back to the **extensions root** when top-level `*.py` files exist there. That fallback is the clearest example of **“`extensions` on `sys.path`”** to deprecate.

**Non-goals for v1 of this policy:** changing **init script** execution (`runpy`) semantics; only **import path** / **`sys.path`** registration is in scope here.

### 7.6 Target state (after v1.0.0)

- Only **`src/libraries/`**, **`src/python/`**, **`src/init/pre/`**, and **`src/init/post/`** are documented for new **pipeline** bundles.
- **`src/local/`** (locked — §9) exists only in the **framework bundle** (`framework.sourcePath`).
- Flat **`extensions/`** `sys.path` behaviour **removed in v1.0.0** (one minor after deprecation lands in v0.13.0).
- **`extensions/libraries/`** never shipped in `main` — dropped in PR1 with no deprecation window.

---

## 8. Framework bundle directory

**Context:** `framework.sourcePath` points at the **root of the framework deployment** (the “framework bundle”). Diagram uses **`<framework_bundle>/`** as that root.

```text
<framework_bundle>/                    # root = framework.sourcePath (overlay when using a wheel)
  src/
    lakeflow_framework/                # present in flat checkout; absent on disk when code comes from wheel only
      contrib/
    local/                             # customer-owned; framework upgrades never touch this subtree
      config/                          # sparse override fragments (locked — §5.2); replaces deprecated config/override/
      libraries/                       # org-specific wheels / loose .py (sys.path registered)
      python/                          # org-specific pipeline logic modules (sys.path registered)
      init/
        pre/                           # org-specific pre-init lifecycle scripts
        post/                          # org-specific post-init lifecycle scripts
    # legacy shims during migration, e.g. utility.py — removed at 1.0 (see §11)
  config/                              # optional when defaults live in wheel (§5.2); full tree for flat OSS
    default/
    override/                # DEPRECATED (v0.13.0) — migrate to src/local/config/; removed in v1.0.0
```

**No top-level `src/libraries/`, `src/python/`, or `src/init/` in the framework bundle.** These directories exist only in pipeline bundles. The framework bundle exposes custom code exclusively through `src/local/`.
- **`config/`** sits beside **`src/`** when used; config is not under **`libraries/`** or **`python/`**. With **§5.2**, **`config/default/`** on disk may become **optional** for wheel-based installs.

---

## 9. Pipeline bundle: no `src/local/`

Pipeline bundles are self-contained and versioned independently — they do **not** have a `src/local/` directory. Fork-safe customisation lives only in the **framework bundle** (`framework.sourcePath`) under `src/local/`, where it applies across all pipelines. See §5 and §5.1.

---

## 10. Flat deploy vs wheel (summary)

| Concern | Flat directory | Wheel |
|---------|----------------|-------|
| Import | `sys.path` + shims / package | `import lakeflow_framework` |
| Bundle code in `src/libraries/` | Path injection | Optionally also packaged into a customer wheel **TBD** |
| Contrib | Same tree | Same wheel or **`lakeflow-framework[contrib]`** extra (locked — §11) |
| **Framework `libraries` / `python` / `init` (under `src/local/` only)** | Live under **`framework.sourcePath`/src/local/`** on disk | Same: **overlay directory on disk** + wheel for package code — see **§5.1** |
| **Framework configuration** | **`config/default`** (+ `override`) on disk under **`framework.sourcePath`**; base defaults via **§5.2.1** **disk-first (A)** when no wheel | **Packaged defaults** + **§5.2.1** **package-first (B)** recommended; overrides on disk: **`src/local/config/`** (locked — §5.2); **`config/override/`** deprecated v0.13.0, removed v1.0.0 |

---

## 11. Open questions (iteration backlog)

### Packaging & repo

- [x] PyPI package name: **`lakeflow-framework`** (locked); import name: **`lakeflow_framework`** (locked). No short alias convention — `import lakeflow_framework` is the canonical form in all docs and samples.
- [x] **Extras (locked):** `pip install lakeflow-framework` → core only; `pip install lakeflow-framework[contrib]` → core + contrib; `pip install lakeflow-framework[all]` → everything. Keeps core install lightweight; contrib deps are opt-in. Implementation in **PR2/PR3**.
- [x] Legacy top-level import shims (`utility`, `constants`, `pipeline_config`, etc.): **keep until 1.0** (locked). Shims re-export from `lakeflow_framework.*`; removed only at the 1.0 major version bump. No deprecation warning required before 1.0.

### `src/libraries/` & `src/python/`

- [x] Strict contents of `libraries/`: wheels (`.whl`), top-level **`*.py`** modules, and packages — see **§7.1**. Customer manages layout correctness.
- [x] Auto-generate Databricks `libraries:` from disk: **out of scope** — customer manages all `libraries:` entries in DAB YAML directly (see **§7.1**).
- [x] **`sys.path` registration for `src/libraries/`**: **keep** — needed for loose `.py` files and packages placed under `libraries/`; a no-op for any `.whl` files there (wheels require cluster install via `libraries:` YAML). See **§7.1**.
- [x] Import style under `src/python/` (flat vs package layout): **document both** — flat for simple bundles (short spec strings, matches current samples), package/namespaced for larger bundles (avoids collisions between framework and bundle spec Python, scales better). Each pipeline only sees framework + its own bundle so collision scope is narrow. See **§7.2**.
- [x] **Legacy `sys.path`:** flat `extensions/` deprecated with warning in **v0.13.0 (PR1)**; **removed in v1.0.0 (PR5)**. `extensions/libraries/` was never released — no deprecation window needed, drop immediately. See **§7.5**.
- [x] Constants: paths for new directories (`src/libraries/`, `src/python/`, `src/init/pre/`, `src/init/post/`) use `./src/` prefix; existing paths (`./config`, `./dataflows`, `./pipeline_configs`, `./python_functions`, `./extensions`) stay at bundle root for now — documented as transitional. Full constants + sample path refactor deferred to **PR6** (see §12 / plan).
- [ ] **Documentation revamp (Phase G):** rewrite `feature_python_extensions.rst` and related docs to cover all three scenarios clearly — cluster install via `libraries:` (wheels/PyPI/UC Volumes/Artifactory/Nexus), `sys.path` registration for `src/libraries/`, and spec Python under `src/python/` — see **§7.2** documentation note.

### Init & logger

- [x] Lock ordering vs pluggable logger and `logger.json` factory import path: **handled by separate logging branch/PR** — align that PR with `src/libraries/` factory module convention and init ordering in §7.3 when merging.
- [x] Document “factory modules live under `src/libraries/`”: **deferred to the logging PR** — if pluggable logger factory is adopted, factory modules must live under `src/libraries/` (registered before logger construction per §7.3 step 2).

### Framework configuration (§5.2)

- [x] Ship **`config/default`** as **package data** inside the wheel: wheel mirrors `src/config/default/` exactly (already released on disk); disk-first for flat deploys, wheel for wheel installs. `logger.json` and schemas follow same pattern. Implementation deferred to **PR3**.
- [x] **§5.2.1 resolver: Strategy B (package-first)** — locked. Load from wheel package data first (versioned-correct); fall back to `src/config/default/` on disk for flat deploys (no wheel); deep-merge `src/local/config/` overrides on top (customer wins on conflict). **Override files are sparse/partial** — a `src/local/config/global.json` with only the changed keys is valid; resolver fills remaining keys from defaults. Implementation deferred to **PR3**.
- [x] Override convention: **`src/local/config/`** is the single public convention (locked with `src/local/` name). **`config/override/`** deprecated in same release that introduces `src/local/` (**v0.13.0 / PR1**); removed in **v1.0.0 (PR5)** — same one-minor window as `extensions/`.
- [ ] Unit tests: flat-only (disk fallback), wheel-only (package data), both (Strategy B merge) — implementation in **PR3**.
- [ ] Update **`resolve_framework_config_path`** / callers to use Strategy B unified resolver — implementation in **PR3**.

### Customer sandboxes

- [x] Exact name: **`src/local/`** (locked) — de facto OSS standard ("local" = not for upstream, per git config hierarchy and Django `local_settings` convention); gitignore strategy and submodule doc deferred to Phase D.
- [x] **Framework bundle paths:** `src/local/{libraries,python,init/…}` are the **only** supported locations for custom code in the framework bundle — no top-level `src/libraries/`, `src/python/`, or `src/init/` in the framework bundle (those are pipeline-bundle-only). Loader precedence (§5.1) is therefore unambiguous: framework `src/local/…` before pipeline bundle `src/…`.
- [ ] **Framework wheel + overlay (§5.1):** document supported `framework.sourcePath` + `pip install` combo in deploy guides — implementation in **PR3**.

---

## 12. Release and PR / branch strategy (summary)

Ship **layout + loaders + author docs/templates** in **PR1** (**`src/libraries/`**, **`src/python/`**, **`src/init/pre|post`**, **`src/local/`**), with **`extensions/` deprecated-but-working** (**§7.5**). Land **`lakeflow_framework` package + `contrib` + shims** in **PR2**. Keep **packaged config + §5.2.1 resolver** (**§5.2**) in **PR3** so forked customers can merge path and import changes separately from config-loader churn.

**Detail:** branch names, suggested **0.x** tagging, “one PR vs split,” and phase mapping — see **[src-libraries-plan.md](./src-libraries-plan.md)** (section **Recommended PR and branch sequence**).

---

## 13. References (in-repo)

- `src/bundle_loader.py` — `sys.path` + init script discovery (to align with §7.4 paths when implemented).
- `src/constants.py` — `FrameworkPaths`, `PipelineBundlePaths`.
- `docs/source/feature_python_extensions.rst`, `docs/source/feature_logging.rst`.
- `pipeline_bundle_template/`, `samples/`.
