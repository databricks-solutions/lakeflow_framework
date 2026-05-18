# local/init/pre/

**Pre-init lifecycle scripts** — `.py` files run **before** SDP table/view declarations
inside `DLTPipelineBuilder.initialize_pipeline()` for **all** pipelines using this framework bundle.

Execution rules:
- Framework bundle scripts (this directory) run before pipeline bundle `src/init/pre/` scripts.
- Within this directory, scripts run in **sorted filename order**.
- Files whose names start with `_` are skipped.
- Each file is executed with `runpy.run_path(..., run_name='__main__')`.
- A script that raises an exception **fails the pipeline**.

Use numeric prefixes to fix order: `01_setup.py`, `02_register.py`.

Scripts may call `pipeline_config.get_spark()`, `get_logger()`, and other
framework singletons directly — they are initialised before pre-init runs.

Typical uses: org-wide Spark configuration, registering shared UDFs, setting up
pluggable loggers, or any one-time setup that should apply across all pipelines.
