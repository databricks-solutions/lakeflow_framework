Logical Environments
====================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Bundle`
   * - **Databricks Docs:**
     - NA

The logical environment feature allows you to specify additional naming separation for Pipeline and Unity Catalog resources. This allows for fine grain separation of resources when working with larger teams in development and SIT environments. 

The logical environment is appended as a suffix to the Pipeline name and the Unity Catalog resource names at Bundle deployment time.

Configuration
-------------

The logical environment is configured in two places.

1. **databricks.yml** Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defined in the variables section:

.. code-block:: yaml

    variables:
      logical_env:
        description: The logical environment
        default: ""

The value is passed / retrieved at bundle deployment time. The section :ref:`feature_logical_env_passing` below, describes the different ways to pass the logical environment value.

2. **pipeline resource YAML files** Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To leverage the pipeline resource YAML when deploying a Pipeline, the logical environment must be specified in a pipelines resource YAML file(s) in the ``logicalEnv`` section. For example:

.. code-block:: yaml
   :emphasize-lines: 4,17

    resources:
      pipelines:
        dlt_framework_samples_bronze_pipeline:
          name: dlt_framework_samples_bronze_pipeline${var.logical_env}
          channel: CURRENT
          serverless: true
          catalog: ${var.catalog}
          schema: ${var.schema}
          libraries:
            - notebook:
                path: ${var.framework_source_path}/dlt_pipeline

          configuration:
            bundle.sourcePath: /Workspace/${workspace.file_path}/src
            bundle.target: ${bundle.target}
            framework.sourcePath: ${var.framework_source_path}
            logicalEnv: ${var.logical_env}
            workspace.host: ${var.workspace_host}



.. _feature_logical_env_passing:

Passing the logical environment
--------------------------------

The logical environment can be passed in one of three ways at bundle deployment time. These also apply to any CI/CD pipeline that is used to deploy the bundle.

1. Environment Variable
~~~~~~~~~~~~~~~~~~~~~~~

An environment variable can be set prior to executing the ``databricks bundle deploy`` command. For example:

.. code-block:: bash

    export BUNDLE_VAR_logical_env=my_logical_env_suffix

Databricks reference: https://docs.databricks.com/en/dev-tools/bundles/variables.html#set-a-variables-value

2. Command Line Argument
~~~~~~~~~~~~~~~~~~~~~~~

The logical environment can be directly specified via the ``databricks bundle deploy`` command. For example:

.. code-block:: bash

    databricks bundle deploy --var="logical_env=my_logical_env_suffix"

Databricks reference: https://docs.databricks.com/en/dev-tools/bundles/variables.html#set-a-variables-value
