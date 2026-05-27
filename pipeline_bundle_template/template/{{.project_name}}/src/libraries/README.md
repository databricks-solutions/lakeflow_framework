# src/libraries/

Place here:
- **Wheel files** (`.whl`) referenced in your DAB `libraries:` YAML for cluster installation, if bundling in DAB.
- **Loose `.py` modules or packages** that need to be importable but are not directly referenced
  by a Data Flow Spec `module` path (e.g. shared helpers, factory modules for pluggable loggers).

This directory is added to `sys.path` by the framework at pipeline initialisation.
Wheel files here must also be declared in your pipeline `resource.yaml` / DAB YAML:

```yaml
pipelines:
  my_pipeline:
    environment:
      dependencies:
        - /Workspace/${workspace.file_path}/src/libraries/my_package.whl
```

See the design guide for the distinction between `src/libraries/` and `src/python/`.
