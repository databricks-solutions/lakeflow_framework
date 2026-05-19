# local/libraries/

Org-wide shared libraries available to **all** pipelines that use this framework bundle.

Place here:
- **Wheel files** (`.whl`) referenced in your DAB `libraries:` YAML for cluster installation.
- **Loose `.py` modules or packages** that need to be importable across all pipelines but are
  not directly referenced by a Data Flow Spec `module` path (e.g. shared helpers, factory
  modules for pluggable loggers).

This directory is added to `sys.path` by the framework at pipeline initialisation — before the
pipeline bundle's `src/libraries/` — so org-wide modules take precedence.

Wheel files here must also be declared in each pipeline's `resource.yaml` / DAB YAML:

```yaml
pipelines:
  my_pipeline:
    environment:
      dependencies:
        - /Workspace/<framework_source_path>/src/local/libraries/my_package.whl
```

See `feature_python_extensions` in the docs for the distinction between `local/libraries/`
(framework bundle, org-wide) and `src/libraries/` (pipeline bundle, bundle-specific).
