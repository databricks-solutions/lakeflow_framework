Python Code, Libraries & Init Scripts
=======================================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Pipeline`
   * - **Databricks Docs:**
     - - `Manage Python dependencies for pipelines <https://docs.databricks.com/aws/en/ldp/developer/external-dependencies>`_
       - `Pipeline environment <https://docs.databricks.com/aws/en/dev-tools/bundles/resources#pipelineenvironment>`_

Overview
--------

The framework supports three mechanisms for adding custom code to the framework or a pipeline bundle. Each
addresses a different concern and has a dedicated place in both bundle structures:

.. list-table::
   :header-rows: 1
   :widths: 5 20 20 55

   * - #
     - Mechanism
     - Location
     - Purpose
   * - 1
     - **Cluster libraries**
     - External:

         - PyPI
         - UC Volume
         - Artifact repository e.g. Artifactory, Nexus

       | **OR**
       | Bundled wheel: ``src/libraries/``
     - Third-party or in-house Python packages installed on the cluster before the pipeline
       runs. The framework plays no role in installation; the Databricks Asset Bundle
       `pipeline environments <https://docs.databricks.com/aws/en/dev-tools/bundles/resources#pipelineenvironment>`_
       mechanism handles it. Bundling under ``src/libraries/`` is a fallback for when an
       external registry is not available or practical.
   * - 2
     - **Pipeline Python Code**
     - ``src/python/``
     - Custom modules and packages written by your team that are referenced directly by
       Data Flow Specs (sources, transforms, sinks). Added to ``sys.path`` at pipeline
       initialisation so specs can resolve them by module path.
   * - 3
     - **Init scripts**
     - ``src/init/pre/`` and ``src/init/post/``
     - Lightweight ``.py`` files that run at fixed points in the pipeline initialisation
       lifecycle. ``pre/`` scripts run before SDP data flow declarations; ``post/`` scripts
       run after. Use them for Spark configuration, event hook registration, or any
       one-time setup that must happen outside of Data Flow logic.

Each mechanism is independent. You can use any combination.

Two bundle contexts
-------------------

The framework operates with two bundles, each of which carries its own ``src/`` tree:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Bundle
     - Spark conf key
     - Role
   * - **Framework bundle**
     - ``framework.sourcePath``
     - Carries framework code. Custom code lives exclusively under ``src/local/`` —
       the fork-safe area for org-specific customisations that should not be merged
       back upstream.
   * - **Pipeline bundle**
     - ``bundle.sourcePath``
     - Carries your pipeline's Data Flow Specs, pipeline config, and any
       bundle-specific libraries, pipeline logic modules, and init scripts.

**src/local/ — framework bundle only**

``src/local/`` is the **only** place for custom code in the framework bundle
(``framework.sourcePath``). It is a customer-owned directory that framework upgrades
and upstream merges will never overwrite. The framework bundle has **no** top-level
``src/libraries/``, ``src/python/``, or ``src/init/`` — those paths exist only in
pipeline bundles:

- ``src/local/libraries/`` — org-wide shared modules or wheels (``sys.path`` registered)
- ``src/local/python/`` — org-wide pipeline logic modules available to all pipelines (``sys.path`` registered)
- ``src/local/init/pre/`` and ``src/local/init/post/`` — org-wide lifecycle scripts, run before the pipeline bundle's scripts at each phase

Where does custom code live?
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - What
     - Pipeline bundle
     - Framework bundle (``src/local/`` only)
   * - Bundle wheel (if bundled with pipeline)
     - ``src/libraries/``
     - ``src/local/libraries/``
   * - Loose ``.py`` modules on ``sys.path``
     - ``src/libraries/``
     - ``src/local/libraries/``
   * - Pipeline logic modules (spec-referenced)
     - ``src/python/``
     - ``src/local/python/``
   * - Pre-init lifecycle scripts
     - ``src/init/pre/``
     - ``src/local/init/pre/``
   * - Post-init lifecycle scripts
     - ``src/init/post/``
     - ``src/local/init/post/``

.. admonition:: Deprecation Notice
   :class: warning

   As of **v0.13.0**, the legacy ``extensions/`` directory (top-level ``.py`` files
   added to ``sys.path``) is **deprecated** and emits a ``DeprecationWarning`` at
   pipeline startup. It will be **removed in v1.0.0**. Migrate by moving ``.py`` files
   to ``src/python/`` — spec ``module`` strings in Data Flow Specs are unchanged.

Directory Structure
-------------------

::

    my_pipeline_bundle/
    ├── src/
    │   ├── libraries/            # Optional: bundle-local wheels + sys.path loose .py
    │   │   ├── my_package.whl    # Referenced in resource.yaml libraries: section
    │   │   └── shared_utils.py   # Available on sys.path (not spec-referenced)
    │   │
    │   ├── python/               # Spec-referenced Python (sys.path)
    │   │   ├── sources.py        # Custom source functions
    │   │   ├── transforms.py     # Custom transform functions
    │   │   └── sinks.py          # Custom sink functions
    │   │
    │   ├── init/
    │   │   ├── pre/              # Run before SDP declarations
    │   │   │   └── 01_setup.py
    │   │   └── post/             # Run after SDP declarations
    │   │       └── 01_hooks.py
    │   │
    │   ├── dataflows/
    │   └── pipeline_configs/
    │       └── ...
    └── requirements_additional.txt   # Optional pip dependencies
    └── resource.yaml

Cluster Library Installation
-----------------------------

Cluster libraries are Python packages installed on the Databricks cluster by the
Declarative Automation Bundle(DAB) `pipeline environments <https://docs.databricks.com/aws/en/dev-tools/bundles/resources#pipelineenvironment>`_ mechanism; the framework is not involved
in installation at all.

You can reference libraries from any source that DAB supports. ``src/libraries/`` is
not the preferred location, it is simply the natural place to put a wheel *if* you
choose to bundle it alongside your pipeline code. Most teams source libraries from one
of the following:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Source
     - Example ``environment.dependencies`` entry in ``resource.yaml``
   * - **PyPI** *(most common)*
     - ``- requests>=2.28``
   * - **UC Volumes**
     - ``- /Volumes/catalog/schema/my_pkg.whl``
   * - **Artifact repository** (Artifactory, Nexus)
     - ``- https://artifactory.example.com/path/my_pkg.whl``
   * - **Bundle wheel** (wheel travels with pipeline code)
     - ``- /Workspace/${workspace.file_path}/src/libraries/my_package.whl``

``src/libraries/`` is only needed for the last case. The framework also adds this
directory to ``sys.path`` for loose ``.py`` modules or packages that you want
importable without a full wheel build — this is a secondary, convenience role.

.. code-block:: yaml
   :caption: resource.yaml (DAB pipeline definition)

   pipelines:
     my_pipeline:
       environment:
         dependencies:
           - /Workspace/${workspace.file_path}/src/libraries/my_package.whl

.. note::

   The framework also adds ``src/libraries/`` to ``sys.path`` so **loose** ``.py``
   modules and packages placed there are directly importable. This is a **no-op for
   ``.whl`` files** — wheels must be declared in ``libraries:`` YAML and are installed
   by the cluster, not ``sys.path``.

Pipeline Python Code (``src/python/``)
---------------------------------------

``src/python/`` is the **single home for all Python modules and packages referenced by Data Flow
Specs** — sources, transforms, sinks, and shared utility modules. The framework adds
this directory to ``sys.path`` at pipeline initialisation so modules are importable
as top-level names.

Import layout options
^^^^^^^^^^^^^^^^^^^^^

Both flat and package layouts are supported. Choose based on bundle size and
collision risk:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Layout
     - Example spec string
     - When to use
   * - **Flat** — ``.py`` files directly under ``src/python/``
     - ``"pythonModule": "transforms.my_function"``
     - Simple bundles with few modules; matches the sample style; short, readable spec strings.
   * - **Package** — namespaced subdirectory with ``__init__.py``
     - ``"pythonModule": "myorg.transforms.my_function"``
     - Larger bundles; avoids name collisions when multiple bundles are on the same
       cluster; scales as the module count grows.

Python Sources
^^^^^^^^^^^^^^

Custom code that generates DataFrames for use as data sources.

.. code-block:: python
   :caption: src/python/sources.py

   from pyspark.sql import DataFrame, SparkSession
   from typing import Dict

   def get_customer_cdf(spark: SparkSession, tokens: Dict) -> DataFrame:
       source_table = tokens["sourceTable"]
       return (
           spark.readStream
           .options(readChangeFeed="true")
           .table(source_table)
       )

    def get_api_data(spark: SparkSession, tokens: Dict) -> DataFrame:
        """
        Fetch data from an external API.
        """
        import requests  # From requirements_additional.txt
        
        api_url = tokens["apiUrl"]
        response = requests.get(api_url)
        data = response.json()
        
        return spark.createDataFrame(data)

**Reference in Data Flow Spec:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 10

         {
             "dataFlowId": "customer_from_extension",
             "dataFlowGroup": "my_dataflows",
             "dataFlowType": "standard",
             "sourceSystem": "custom",
             "sourceType": "python",
             "sourceViewName": "v_customer",
             "sourceDetails": {
                 "tokens": {"sourceTable": "{staging_schema}.customer"},
                 "pythonModule": "sources.get_customer_cdf"
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "customer"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 9

         dataFlowId: customer_from_extension
         dataFlowGroup: my_dataflows
         dataFlowType: standard
         sourceSystem: custom
         sourceType: python
         sourceViewName: v_customer
         sourceDetails:
           tokens:
             sourceTable: '{staging_schema}.customer'
           pythonModule: sources.get_customer_cdf
         mode: stream
         targetFormat: delta
         targetDetails:
           table: customer

Transforms
^^^^^^^^^^

Custom code that transforms DataFrames after they are read from a source.

**Function Signatures:**

.. code-block:: python

    # Without tokens
    def my_transform(df: DataFrame) -> DataFrame:
        ...

    # With tokens
    def my_transform_with_tokens(df: DataFrame, tokens: Dict) -> DataFrame:
        ...

**Example:**

.. code-block:: python
   :caption: src/python/transforms.py

    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F

    def explode_deletes(df: DataFrame) -> DataFrame:
        """
        Duplicates delete records and adjusts sequence_by timestamp.
        For deletes: is_delete=0 gets +1ms, is_delete=1 gets +2ms.
        """
        # Create array: [0,1] for deletes, [0] for others, then explode
        sequence_column = "LOAD_TIMESTAMP"
        change_type_column = "meta_cdc_operation"

        is_delete = F.col(change_type_column) == "delete"
        array_col = F.when(is_delete, F.array(F.lit(0), F.lit(1))).otherwise(F.array(F.lit(0)))
        
        return (
            df.withColumnRenamed("_change_type", change_type_column)
            .withColumn("is_delete", F.explode(array_col))
            .withColumn(
                sequence_column, 
                F.when(is_delete & (F.col("is_delete") == 0), 
                    F.col(sequence_column) + F.expr("INTERVAL 1 millisecond"))
                .when(is_delete & (F.col("is_delete") == 1), 
                    F.col(sequence_column) + F.expr("INTERVAL 2 millisecond"))
                .otherwise(F.col(sequence_column))
            )
        )

**Reference in Data Flow Spec:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 12-14

         {
             "dataFlowId": "customer",
             "dataFlowGroup": "my_dataflows",
             "dataFlowType": "standard",
             "sourceSystem": "example",
             "sourceType": "delta",
             "sourceViewName": "v_customer",
             "sourceDetails": {
                 "database": "{bronze_schema}",
                 "table": "customer",
                 "cdfEnabled": true,
                 "pythonTransform": {
                     "module": "transforms.explode_deletes"
                 }
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "customer"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 11-12

         dataFlowId: customer
         dataFlowGroup: my_dataflows
         dataFlowType: standard
         sourceSystem: erp
         sourceType: delta
         sourceViewName: v_customer
         sourceDetails:
           database: '{bronze_schema}'
           table: customer
           cdfEnabled: true
           pythonTransform:
             module: transforms.explode_deletes
         mode: stream
         targetFormat: delta
         targetDetails:
           table: customer

Sinks
^^^^^

Custom functions for ``foreach_batch_sink`` targets that process micro-batches.

.. code-block:: python
   :caption: src/python/sinks.py

   from pyspark.sql import DataFrame
   from typing import Dict

   def write_to_external_api(df: DataFrame, batch_id: int, tokens: Dict) -> None:
       import requests
       api_url = tokens["apiUrl"]
       for record in df.toJSON().collect():
           requests.post(api_url, json=record)

Init scripts (``src/init``)
---------------------------

Init scripts are Notebooks and other plain ``.py`` files executed by the framework around
``DLTPipelineBuilder.initialize_pipeline()``.

- **pre** (``src/init/pre/``) — runs after configs and specs are loaded, **before**
  any ``DataFlow.create_dataflow()`` / SDP declarations.
- **post** (``src/init/post/``) — runs **after** all data flows for the pipeline have
  been created (the SDP graph is assembled; the pipeline update has not started yet).

Execution rules
^^^^^^^^^^^^^^^

- Framework bundle scripts run before pipeline bundle scripts at each phase.
- Within each directory, scripts run in **sorted filename order**.
- Files whose names start with ``_`` are **skipped**.
- Each file is executed with ``runpy.run_path(..., run_name='__main__')``.
- A script that raises an exception **fails the pipeline**.

Use numeric prefixes to fix order: ``01_setup.py``, ``02_register.py``.

.. code-block:: python
   :caption: src/init/pre/01_setup.py

   """Register a custom Spark config before SDP declarations."""
   import pipeline_config

   spark = pipeline_config.get_spark()
   spark.conf.set("spark.sql.adaptive.enabled", "true")

.. code-block:: python
   :caption: src/init/post/01_hooks.py

   """Register a pipeline event hook after the SDP graph is assembled."""
   from pyspark import pipelines as dp
   import pipeline_config

   logger = pipeline_config.get_logger()

   @dp.on_event_hook
   def log_event(event):
       logger.info("Pipeline event: %s", event)

Additional Resources
--------------------

- :doc:`feature_python_dependency_management` — managing Python dependencies
- :doc:`feature_python_source` — using Python as a source type
- :doc:`feature_python_functions` — Python transform functions (file path approach)
- :doc:`dataflow_spec_ref_source_details` — complete source configuration reference
- :doc:`dataflow_spec_ref_target_details` — complete target configuration reference
