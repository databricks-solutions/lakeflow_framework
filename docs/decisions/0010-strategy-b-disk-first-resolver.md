# ADR-0010: Strategy B — Workspace Files-first config and schema resolution

**Date:** 2026-05-23
**Status:** Accepted
**PR:** refactor/lakeflow-framework-package (v0.16.0)

---

## Context

With the introduction of the `lakeflow_framework` Python package (ADR-0009),
default config files (`config/default/`) and JSON schemas (`schemas/`) are
bundled inside the wheel via `importlib.resources`. Previously they lived only
in Workspace Files at `{framework_path}/lakeflow_framework/config/default/`.

Two deployments now co-exist:

| Deploy mode | Where defaults live |
|-------------|---------------------|
| Flat DAB deploy | On workspace files under `framework.sourcePath` |
| Wheel install | Bundled inside the wheel (`importlib.resources`) |
| Wheel + local overlay | Wheel bundled, plus `src/local/config/` fragments |

The resolver (`load_framework_default_json`) must decide which source to read
first when both a Workspace Files path and the wheel package data are potentially available.

### Options considered

**Option A — Package-first (wheel-first)**
- Always read from `importlib.resources`; treat Workspace Files as an optional
  override layer.
- `+` Simple: the wheel is always the canonical source of defaults.
- `−` **Breaking for existing flat-deploy customers.** Their defaults live in
  Workspace Files; if the wheel shadow-contains a newer (or different) version of a default
  file, behaviour silently changes on upgrade.
- `−` Contradicts the "explicit wins" principle: a customer who set
  `framework.sourcePath` explicitly expects Workspace Files to be authoritative.

**Option B — Workspace Files-first (chosen)**
- When `framework.sourcePath` is set and the file exists in Workspace Files, use it.
- Fall back to `importlib.resources` only when no Workspace Files path is configured or
  the file is absent from Workspace Files.
- Always deep-merge `src/local/config/` overlay on top (unchanged from
  ADR-0006).

**Option C — Explicit-only**
- Require callers to pass either a Workspace Files path or `importlib.resources` traversable;
  no automatic fallback.
- `−` Forces every call site to be aware of the deploy mode; adds boilerplate
  at all 15+ call sites.

## Decision

Adopt **Strategy B (Workspace Files-first)** via `load_framework_default_json`:

```python
def load_framework_default_json(
    name: str,
    framework_path: Optional[str] = None,
) -> Dict:
    """
    Resolution order:
    1. Workspace Files  — {framework_path}/lakeflow_framework/config/default/{name}
               if framework_path is set and the file exists.
    2. Package data — importlib.resources (wheel or src/lakeflow_framework/ on sys.path).
    3. src/local/config/{name} overlay — deep-merged on top of (1) or (2)
               when framework_path is set and the fragment exists.
    """
```

### Resolution sequence in detail

1. **Workspace Files (explicit):** if `framework_path` is provided and
   `{framework_path}/lakeflow_framework/config/default/{name}` exists, load it.
2. **Package data (fallback):** otherwise use
   `importlib.resources.files("lakeflow_framework") / "config" / "default" / name`.
   This works for both an installed wheel and an editable / flat-deploy install
   (the `src/lakeflow_framework/` directory is on `sys.path` in both cases).
3. **Local overlay:** if `framework_path` is set and
   `{framework_path}/src/local/config/{name}` exists, deep-merge it on top of
   whichever base was loaded (dict keys merged recursively; overlay wins on
   conflict; non-dict values replaced wholesale). This preserves the ADR-0006
   sparse-overlay guarantee regardless of deploy mode.

The same logic applies to schema resolution via
`load_framework_schema(name)` in `config_resolver`, which returns an
`importlib.resources` traversable suitable for `jsonschema.RefResolver` and
similar validators.

### Rationale for Workspace Files-first

- **Zero-change upgrade for flat-deploy customers.** Their `framework.sourcePath`
  points to the deployed `src/` directory in Workspace Files; those files are
  found at step 1 and the wheel is never consulted. Behaviour is identical to
  pre-v0.16.0.
- **Explicit wins.** Setting `framework.sourcePath` is a deliberate act.
  Workspace Files-first honours that intent; package-first would silently override it.
- **Wheel-install customers get clean defaults from the package.** They do not
  set `framework.sourcePath` (or set it only for local overlays), so step 1
  is skipped and `importlib.resources` is used — exactly as expected.
- **Testability.** Workspace Files-first is trivially testable: point
  `framework_path` at a temp directory and place a fixture file there.
  Package-data fallback is also testable by omitting `framework_path`.

## Consequences

- **`load_framework_default_json`** is the single resolver for all default
  config and schema reads; call sites that previously used
  `os.path.join(framework_path, FrameworkPaths.CONFIG_PATH, name)` are
  migrated to it.
- Flat-deploy customers see **no behaviour change** on upgrade to v0.16.0.
- Wheel-install customers get defaults from the wheel with no `framework.sourcePath`
  required.
- The `src/local/config/` sparse overlay (ADR-0006) continues to work in all
  three deploy modes — it is applied at step 3 independent of which base was
  used in steps 1–2.
- If a future release ships an intentionally different default (e.g. a renamed
  key), flat-deploy customers picking up a new wheel without re-deploying their
  bundle will continue to use their Workspace Files defaults until they re-deploy.
  This is safe and predictable: Workspace Files-first ensures the Workspace Files always win.
