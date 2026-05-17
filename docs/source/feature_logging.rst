Logging
=======

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework Bundle` :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Global` :bdg-success:`Pipeline`
   * - **Databricks Docs:**
     - NA

The Lakeflow Framework provides structured logging to track pipeline execution and troubleshoot issues. By default, logging uses Python's standard ``logging`` module with a framework stdout handler (logger name ``DltFramework``).

You can optionally plug in a **custom logger** via a dedicated ``logger.json`` config file.

.. admonition:: Setting Precedence
  :class: warning

  * Framework code and extensions should use the singleton accessor ``pipeline_config.get_logger()`` rather than creating their own loggers.

Log Levels
----------

The framework supports standard Python logging levels:

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about pipeline execution (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failed operations
- **CRITICAL**: Critical errors that may cause pipeline failure

Spark ``logLevel`` Configuration
--------------------------------

The default log level for all pipelines is **INFO**.

To specify a different log level, set the ``logLevel`` parameter in the **Configuration** section of a Spark Declarative Pipeline. Spark ``logLevel`` takes precedence over the ``level`` field in ``logger.json`` when the logger is resolved.

Setting the Log Level in the Pipeline YAML
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add ``logLevel`` in the configuration section of your pipeline resource YAML:

.. image:: images/screenshot_pipeline_log_level_yaml.png

Setting the Log Level in the Databricks UI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Browse to your pipeline, open **Settings**, and add ``logLevel`` under **Advanced Configuration**:

.. image:: images/screenshot_pipeline_log_level_ui.png

Pluggable Logger Configuration (``logger.json``)
------------------------------------------------

Custom logging is configured in **``logger.json``** files—not in ``global.json``—so the framework can initialize logging before loading merged global configuration.

| **Scope: Framework**
| Shipped defaults: ``{framework_path}/config/default/logger.json``
| Custom framework settings: ``{framework_path}/config/override/logger.json`` (when the override directory is active; see :doc:`feature_framework_configuration`)

.. important::

   Do **not** edit ``config/default/logger.json`` in the framework bundle. To change framework-level logging, add a new ``logger.json`` under ``config/override/``. When ``config/override/`` is in use, the framework reads **all** framework configuration from that directory (not only ``logger.json``), so the override tree must include the required layout described in :doc:`feature_framework_configuration`.

| **Scope: Pipeline bundle**
| ``{bundle_path}/pipeline_configs/logger.json``

If a file is missing, that side contributes an empty configuration. The shipped framework default disables the custom logger path:

.. code-block:: json

   {
     "enabled": false,
     "allow_pipeline_logger_override": false,
     "mirror_to_stdout": true,
     "level": "INFO",
     "factory_args": {}
   }

Configuration Schema
^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 22 12 12 54

   * - Field
     - Default
     - Framework
     - Description
   * - ``enabled``
     - ``false``
     - ✓ / ✓
     - When ``true``, load and invoke the custom logger factory. When ``false``, use the framework default stdout logger only.
   * - ``library``
     - —
     - ✓ / ✓
     - Optional distribution name to probe (for example ``custom_logger``). If set and not importable, the framework falls back to the default logger and logs a warning.
   * - ``module``
     - —
     - ✓ / ✓
     - Python module to import (for example ``custom_logger.databricks``).
   * - ``factory``
     - —
     - ✓ / ✓
     - Callable on ``module`` (for example ``get_logger``). Invoked as ``factory(dbutils, spark, **factory_args)``.
   * - ``factory_args``
     - ``{}``
     - ✓ / ✓
     - Keyword arguments passed to the factory after ``dbutils`` and ``spark``. Overlapping keys are deep-merged according to precedence rules below.
   * - ``level``
     - ``"INFO"``
     - ✓ / ✓
     - Minimum log level for the resolved logger (may be overridden by Spark ``logLevel``).
   * - ``mirror_to_stdout``
     - ``true``
     - ✓ / ✓
     - When the custom logger initializes successfully, also emit log lines via the framework default stdout handler (see **Composite logging** below).
   * - ``allow_pipeline_logger_override``
     - ``false``
     - ✓ only
     - Framework-only control for merge precedence. Ignored if present in the bundle file.

Merge Precedence (Framework + Bundle)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After mandatory Spark configuration provides ``framework.sourcePath`` and ``bundle.sourcePath``, the framework loads both ``logger.json`` files and merges them:

| ``allow_pipeline_logger_override: false`` (default)
| **Framework wins** on conflicting top-level keys and overlapping ``factory_args`` keys.

| ``allow_pipeline_logger_override: true`` (framework ``logger.json`` only)
| **Pipeline bundle wins** on conflicts.

Keys present in only one file are retained. The pipeline bundle must not rely on defining ``allow_pipeline_logger_override``; set it only in the framework file.

Example — enable logger in the pipeline bundle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install the library on the pipeline (wheel or PyPI in the pipeline **libraries** list), then add ``pipeline_configs/logger.json``:

.. code-block:: json

   {
     "enabled": true,
     "library": "custom_logger",
     "module": "custom_logger.lakeflow_logger",
     "factory": "get_logger",
     "factory_args": {
       "log_to_output": false,
       "disable_export": false,
       "async_log_processing": false
     },
     "level": "INFO",
     "mirror_to_stdout": true
   }

.. tip::

   When ``mirror_to_stdout`` is ``true``, set ``factory_args.log_to_output`` to ``false`` on custom_logger to avoid duplicate output in the notebook cell (Application Insights via the custom logger, framework-formatted lines on stdout for the pipeline **Logs** UI).

Resolution and Fallback
^^^^^^^^^^^^^^^^^^^^^^^

Logger resolution is implemented in ``src/logger.py`` and runs at the start of ``DLTPipelineBuilder`` initialization:

1. Load framework and bundle ``logger.json``.
2. Merge per precedence rules.
3. If ``enabled`` is ``false``, return the framework default stdout logger.
4. If ``library`` is set but not importable, fall back to the default logger with a warning.
5. Otherwise import ``module``, call ``factory(dbutils, spark, **factory_args)``, and validate that the returned object exposes ``debug``, ``info``, ``warning``, ``error``, ``critical``, and ``exception``.
6. On **any** failure (import, factory, invalid return type, downstream init errors), fall back to the default logger with a warning—the pipeline does not fail because of logging misconfiguration.
7. If the custom logger succeeds and ``mirror_to_stdout`` is ``true`` (default), wrap it in a **CompositeLogger** (custom primary + framework stdout mirror).

Composite Logging
^^^^^^^^^^^^^^^^^

When a custom logger initializes successfully and ``mirror_to_stdout`` is ``true``, the framework uses a single **CompositeLogger** instance registered in ``pipeline_config``:

- Log calls go to the **custom logger first** (primary), then to the **framework default stdout logger** (mirror).
- Failures in the primary logger are logged on the mirror; the pipeline continues.
- Failures in the mirror must not break the pipeline.

Set ``mirror_to_stdout`` to ``false`` only if:

- Your logger logs to stdout
- You do not need stdout / Databricks pipeline **Logs** UI output from the framework handler; generally if your logger does not log to you should leave ``mirror_to_stdout`` set to true.

Using the Logger in Code
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pipeline_config import get_logger

   logger = get_logger()
   logger.info("Processing batch %s", batch_id)

``utility.set_logger`` remains for backward compatibility and delegates to the framework default logger factory; new code should use ``pipeline_config.get_logger()``.

Custom loggers that support async flushing may require an explicit ``close()`` at the end of the pipeline. Consider a **post_init** hook under ``extensions/post_init/`` that calls ``close()`` on the primary logger when exposed.

Permissions to View Logs
^^^^^^^^^^^^^^^^^^^^^^^^

By default, only the pipeline owner has permission to view logs for a pipeline execution.

To grant other users access, add the following Spark configuration to the framework using the :doc:`feature_spark_configuration` feature:

.. code-block:: text

    "spark.databricks.acl.needAdminPermissionToViewLogs": "false"

This is documented in the Databricks documentation: https://docs.databricks.com/en/compute/clusters-manage.html

Viewing the default STDOUT Logs
--------------------------------

View logs in the Databricks UI:

1. Open the desired pipeline.
2. Select the desired **Update ID** (pipeline execution).
3. On the right, open the **Update** tab and click **Logs** at the bottom.

   .. image:: images/screenshot_logs_viewing_1.png

4. A new browser tab opens with output in the **STDOUT** section (including framework mirror output when ``mirror_to_stdout`` is enabled):

   .. image:: images/screenshot_logs_viewing_2.png

Example Log Messages
--------------------

Pipeline initialization:

.. code-block:: text

   2025-02-06 04:05:46,161 - DltFramework - INFO - Initializing Pipeline...
   2025-02-06 04:05:46,772 - DltFramework - INFO - Retrieving Global Framework Config From: {path}
   2025-02-06 04:05:46,908 - DltFramework - INFO - Retrieving Pipeline Configs From: {path}

Flow creation:

.. code-block:: text

   2025-02-06 04:05:48,254 - DltFramework - INFO - Creating Flow: flow_name
   2025-02-06 04:05:48,254 - DltFramework - INFO - Creating View: view_name, mode: stream, source type: delta

Error handling:

.. code-block:: text

   2025-02-06 04:06:26,527 - DltFramework - ERROR - Failed to process Data Flow Spec: {error_details}
