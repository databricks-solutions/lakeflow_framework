# src/init/pre/

**Pre-init lifecycle scripts** — `.py` files / notebooks run **before** SDP table/view declarations
inside `DLTPipelineBuilder.initialize_pipeline()`.

Execution rules:
- Framework bundle scripts run before pipeline bundle scripts.
- Within each bundle, scripts run in **sorted filename order**.
- Files whose names start with `_` are skipped.
- Each file is executed with `runpy.run_path(..., run_name='__main__')`.
- A script that raises an exception **fails the pipeline**.

Use numeric prefixes to fix order: `01_setup.py`, `02_register.py`.

Scripts may call `pipeline_config.get_spark()`, `get_logger()`, and other
framework singletons directly — they are initialised before pre-init runs.
