# src/python/

Place here all customer Python modules and packages **referenced by Data Flow Specs**:
sources, transforms, sinks, and shared utility modules called from spec `pythonModule` /
`pythonTransform.module` paths.

This directory is added to `sys.path` by the framework at pipeline initialisation.

**Flat layout** (simple bundles, matches sample style):
```
src/python/
  sources.py
  transforms.py
  sinks.py
```

**Package layout** (larger bundles, avoids name collisions):
```
src/python/
  myorg/
    __init__.py
    transforms/
      __init__.py
      customer_aggregation.py
```

Spec string examples:
- Flat:    `"pythonModule": "transforms.my_function"`
- Package: `"pythonModule": "myorg.transforms.customer_aggregation.my_function"`
