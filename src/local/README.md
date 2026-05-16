# src/local/

**Customer-owned, fork-safe area for org-specific customisations.**

This directory is never touched by upstream framework upgrades or template merges. Place
anything here that is specific to your organisation and should not be contributed back
upstream.

```
src/local/
  libraries/    # Org-wide cluster-install wheels + sys.path loose .py modules
  python/       # Org-wide pipeline logic modules referenced by Data Flow Specs
  init/
    pre/        # Org-wide pre-init lifecycle scripts (run before SDP declarations)
    post/       # Org-wide post-init lifecycle scripts (run after SDP declarations)
```

All sub-directories are optional — create only what your organisation needs.

> **Note:** `src/local/` exists only in the **framework bundle** (`framework.sourcePath`).
> Pipeline bundles do not have a `local/` directory — use `src/python/`, `src/libraries/`,
> and `src/init/` directly inside each pipeline bundle for bundle-specific code.
