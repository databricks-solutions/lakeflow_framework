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
