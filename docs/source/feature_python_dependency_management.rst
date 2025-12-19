Python Dependency Management
============================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework` :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Pipeline`

Overview
--------

The Lakeflow Framework provides flexible Python dependency management at two levels:

1. **Framework Level**: Global dependencies required by the framework or custom extensions (``requirements.txt``)
2. **Pipeline Bundle Level**: Bundle-specific dependencies configured via Databricks Asset Bundles

This separation allows the framework to maintain its core dependencies independently while enabling pipeline developers to add custom packages for their specific use cases.

.. important::

    Databricks recommends using the **pipeline environment settings** to manage Python dependencies.

Framework Dependencies
----------------------

The framework includes a ``requirements.txt`` file at the root of the repository that defines global dependencies required for the framework to function.

Location
^^^^^^^^

::

    dlt_framework/
    ├── requirements.txt          # Framework dependencies
    ├── requirements-dev.txt      # Development dependencies (testing, docs, etc.)
    └── src/
        └── ...

Framework requirements.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text
   :caption: requirements.txt

    ## requirements.txt: dependencies for runtime.
    ## Core dependencies
    jsonschema

    ## Add any additional dependencies needed for custom functionality below here

.. note::

    The framework's core dependencies are intentionally minimal. Add any additional dependencies needed for custom functionality below the core dependencies, do not change the core dependencies.

Pipeline Bundle Dependencies
----------------------------

For pipeline-specific Python dependencies, Databricks recommends using the **pipeline environment** configuration in your Databricks Asset Bundle. For detailed information, see the official Databricks documentation:

- `Manage Python dependencies for pipelines <https://docs.databricks.com/aws/en/ldp/developer/external-dependencies>`_
- `Databricks Asset Bundles - Pipeline Environment <https://docs.databricks.com/aws/en/dev-tools/bundles/resources#pipelineenvironment>`_

Configuring Pipeline Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add the ``environment`` section to your pipeline resource definition in your Databricks Asset Bundle:

.. code-block:: yaml
   :caption: resources/pipeline.yml
   :emphasize-lines: 10-13

    resources:
      pipelines:
        my_pipeline:
          name: My Pipeline (${var.logical_env})
          channel: CURRENT
          serverless: true
          catalog: ${var.catalog}
          schema: ${var.schema}
          
          environment:
            dependencies:
              - -r
                ${workspace.file_path}/requirements.txt

          libraries:
            - notebook:
                path: ${var.framework_source_path}/dlt_pipeline

Using a Requirements File
^^^^^^^^^^^^^^^^^^^^^^^^^

The recommended approach is to reference a ``requirements.txt`` file in your pipeline bundle:

**Step 1: Create a requirements.txt in your pipeline bundle**

For example:
.. code-block:: text
   :caption: my_pipeline_bundle/requirements.txt
    requests>=2.28.0
    openpyxl

**Step 2: Reference it in your pipeline environment**

.. code-block:: yaml

    environment:
      dependencies:
        - -r
          ${workspace.file_path}/requirements.txt

.. important::

    The ``-r`` flag tells pip to read requirements from a file. The path ``${workspace.file_path}`` is substituted with the deployed bundle location in the Databricks workspace.

Inline Dependencies
^^^^^^^^^^^^^^^^^^^

For simple cases with few dependencies, you can specify packages inline:

.. code-block:: yaml

    environment:
      dependencies:
        - requests>=2.28.0
        - pandas>=2.0.0

Installing from Unity Catalog Volumes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also install Python wheel packages stored in Unity Catalog volumes:

.. code-block:: yaml

    environment:
      dependencies:
        - /Volumes/my_catalog/my_schema/my_volume/my_package-1.0-py3-none-any.whl

Best Practices
--------------

Version Pinning
^^^^^^^^^^^^^^^

Always pin dependency versions to ensure reproducible builds:

.. code-block:: text

    # Recommended: Pin to minimum version
    requests>=2.28.0
    
    # For strict reproducibility
    pandas==2.0.3
    
    # Avoid: Unpinned versions
    requests  # Not recommended

Documentation
^^^^^^^^^^^^^

Add comments to explain why each dependency is needed:

.. code-block:: text

    # HTTP client for external API integrations
    requests>=2.28.0
    
    # JSON schema validation for custom specs
    jsonschema>=4.0.0
    
    # Date parsing utilities for transform functions
    python-dateutil>=2.8.0

Testing Dependencies Locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before deploying, test that dependencies install correctly:

.. code-block:: bash

    # Create a virtual environment
    python -m venv test_env
    source test_env/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Verify imports work
    python -c "import requests; import pandas; print('Success!')"

Limitations
-----------

1. **JVM Libraries Not Supported**: Lakeflow Declarative Pipelines only support SQL and Python. JVM libraries (Scala/Java) cannot be used and may cause unpredictable behavior.

2. **Startup Time Impact**: Each additional dependency increases pipeline startup time. Keep dependencies minimal for faster pipeline starts.

3. **No Hot Reloading**: Dependencies are installed at pipeline startup. Adding new dependencies requires a pipeline restart.

4. **Cluster-Wide Scope**: Dependencies are installed for the entire pipeline cluster. Be mindful of potential conflicts between packages.

Troubleshooting
---------------

Dependencies Not Found
^^^^^^^^^^^^^^^^^^^^^^

If packages aren't being installed:

1. Verify the ``environment`` section is correctly indented in your YAML
2. Check that the path to ``requirements.txt`` is correct
3. Ensure the requirements file is included in your bundle deployment

.. code-block:: yaml

    # Verify correct path substitution
    environment:
      dependencies:
        - -r
          ${workspace.file_path}/requirements.txt  # Points to bundle root

Version Conflicts
^^^^^^^^^^^^^^^^^

If you encounter version conflicts:

1. Check for conflicting versions between framework and bundle requirements
2. Use ``pip check`` locally to identify conflicts
3. Consider pinning specific versions to resolve conflicts

.. code-block:: bash

    pip install -r requirements.txt
    pip check  # Shows any dependency conflicts


