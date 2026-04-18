Validation
==========

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Pipeline Bundle`
   * - **Databricks Docs:**
     - NA

Overview
--------
The framework uses the Python ``jsonschema`` library to define the schema and validation rules for the: 

- Data Flow Specifications
- Expectations
- Secrets Configurations

This provides the following functionality:

- :doc:`feature_auto_complete`
- Validation in your CI/CD pipelines
- Validation at Spark Declarative Pipeline initialization time

How Validation Works
--------------------

The framework uses the ``jsonschema`` library to validate the Data Flow Specifications, Expectations, and Secrets Configurations.
Essentially each time a pipeline executes the following steps are performed:

.. list-table::
   :widths: 10 30 60
   :header-rows: 1

   * - Step
     - Name
     - Description
   * - 1
     - Load and Initialize Framework
     - Load and initialize the Framework
   * - 2
     - Retrieve Data Flow Specifications
     - 
       a. **Retrieve and validate:**
          - Read and validate ALL the Data Flow Specifications, Expectations, and Secrets Configurations from the workspace files location of the Pipeline Bundle.
          - If a file is not valid it will be added to an error list.
          - If any files failed validation, the pipeline will fail and the user will receive a list of validation errors.
       b. **Apply pipeline filters:**
          - The framework will apply any pipeline filters to the in memory dictionary.
          - The only exception to this is the File Filter which means the framework will specifically only read that file(s).
   * - 3
     - Generate Pipeline Definition
     - The Framework will then use the in memory dictionary to initialize the Spark Declarative Pipeline.
   * - 4
     - Execute Pipeline
     - The pipeline will then execute the logic defined in the Data Flow Specifications.

Ignoring Validation Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~

Ignoring validation errors can be useful when iterating in Dev or SIT environments and you want to focus on specific Data Flow Specs (selected by your pipeline filters), without being blocked by validation errors.

You can ignore validation errors by setting the ``pipeline.ignoreValidationErrors`` configuration to ``True``.

You can do this in the pipeline resource YAML file or via the Databricks UI in the Spark Declarative Pipeline Settings.

.. code-block:: yaml
    :emphasize-lines: 21

    resources:
        pipelines:
            dlt_framework_samples_bronze_base_pipeline:
            name: Lakeflow Framework Samples - Bronze - Base Pipeline (${var.logical_env})
            channel: CURRENT
            serverless: true
            catalog: ${var.catalog}
            schema: ${var.schema}
            libraries:
                - notebook:
                    path: ${var.framework_source_path}/dlt_pipeline

            configuration:
                bundle.sourcePath: ${workspace.file_path}/src
                bundle.target: ${bundle.target}
                framework.sourcePath: ${var.framework_source_path}
                workspace.host: ${var.workspace_host}
                pipeline.layer: ${var.layer}
                logicalEnv: ${var.logical_env}
                pipeline.dataFlowGroupFilter: base_samples
                pipeline.ignoreValidationErrors: True

Validation via CI/CD
--------------------

You can validate Data Flow Specification ``*_main.json`` files in CI without running a Spark Declarative Pipeline. The framework repository includes a ``scripts/validate_dataflows.py`` script: run it from a checkout of Lakeflow Framework repo so it can load JSON Schemas (under ``src/schemas/``) and optional dataflow spec version mappings, then point it at a directory or single ``*_main.json`` in your pipeline bundle or monorepo.

Validating in GitHub Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are using GitHub Actions for your CI/CD pipelines, you can use the **composite action** in this repository at ``.github/actions/validate-dataflows/action.yaml``. It installs Python and ``jsonschema`` and invokes ``scripts/validate_dataflows.py`` for you without needing to explicitly checkout the Lakeflow Framework repo.

**Requirements**

* Check out **your** repository (the pipeline bundle or project that contains the dataflow specs) before running the action, so the ``path`` input resolves under ``github.workspace``.
* The action installs Python and ``jsonschema``, then runs the validator with your chosen options.

**Inputs**

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Input
     - Description
   * - ``path``
     - Directory or single ``*_main.json`` file to validate, relative to the workflow workspace. Default: ``.``
   * - ``no-mapping``
     - If ``true``, skip dataflow spec version mapping (strict validation only). Default: ``false``
   * - ``verbose``
     - If ``true``, enables verbose script output (``-v``). Default: ``false``

**Example workflow**

.. code-block:: yaml

   jobs:
     validate-dataflows:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - uses: databricks-solutions/lakeflow_framework/.github/actions/validate-dataflows@main
           with:
             path: src
             # no-mapping: 'false'
             # verbose: 'false'

The ``uses`` line can reference the ``databricks-solutions/lakeflow_framework`` (upstream) or **your organisation's fork/clone** of the Lakeflow Framework repository. The path ``.github/actions/validate-dataflows`` is the same; set the owner and pin ``@<ref>`` to a tag or commit that exists on whichever repository you rely on.

Pin to a tag or a commit instead of a moving branch for reproducible CI (e.g., replace @main with @v0.11.0).

.. note::

   If the framework repository is **private**, ensure the calling workflow has permission to read it (for example ``contents: read`` and access via the default ``GITHUB_TOKEN`` or a PAT as required by your org).
