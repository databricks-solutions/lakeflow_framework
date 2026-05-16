# local/python/

Org-wide pipeline logic modules available to **all** pipelines that use this framework bundle.

Place here all Python modules and packages **referenced by Data Flow Specs** across your
organisation: sources, transforms, sinks, and shared utility modules called from spec
`pythonModule` / `pythonTransform.module` paths.

This directory is added to `sys.path` by the framework at pipeline initialisation — before
the pipeline bundle's `src/python/` — so org-wide modules are available to all specs.

**Flat layout** (simple shared modules):
```
local/python/
  org_sources.py
  org_transforms.py
  org_sinks.py
```

**Package layout** (larger orgs, avoids name collisions):
```
local/python/
  myorg/
    __init__.py
    transforms/
      __init__.py
      customer_aggregation.py
```

Spec string examples:
- Flat:    `"pythonModule": "org_transforms.my_function"`
- Package: `"pythonModule": "myorg.transforms.customer_aggregation.my_function"`
