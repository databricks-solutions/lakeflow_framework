Framework configuration
=======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Global`
   * - **Databricks Docs:**
     - NA

Framework-level settings (global JSON/YAML, substitutions, secrets, spec mappings, operational metadata) live under **one** active directory. The framework chooses between a **default** tree and an optional **override** tree; everything else reads paths relative to that choice.

Configuration
-------------

| **Scope: Global (framework bundle)**
| **Default:** ``./config/default/`` (for example ``src/config/default/`` when the framework root is ``src``).
| **Override:** ``./config/override/`` (for example ``src/config/override/``). Optional; see **Override** below.

Under the active directory you normally have:

* exactly one global file: ``global.json``, ``global.yaml``, or ``global.yml``
* a ``dataflow_spec_mapping/`` directory (see :doc:`feature_versioning_dataflow_spec`)
* optional per-target substitution and secrets files (see :doc:`feature_substitutions`, :doc:`feature_secrets`)
* optional ``operational_metadata_<layer>.json`` (see :doc:`feature_operational_metadata`)

Mandatory
---------

* **Global file:** exactly one of ``global.json``, ``global.yaml``, ``global.yml``. More than one is an error.
* **Mappings:** the ``dataflow_spec_mapping/`` directory must exist.

Optional
--------

Inside the global file, all top-level keys are optional. Common ones:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Key
     - See
   * - ``pipeline_bundle_spec_format``
     - :doc:`feature_spec_format`
   * - ``mandatory_table_properties``
     - :doc:`feature_mandatory_table_properties`
   * - ``spark_config``
     - :doc:`feature_spark_configuration`
   * - ``table_migration_state_volume_path``
     - :doc:`feature_table_migration`
   * - ``dataflow_spec_version``
     - :doc:`feature_versioning_dataflow_spec`
   * - ``override_max_workers`` / ``pipeline_builder_disable_threading``
     - :doc:`feature_builder_parallelization`

Override
--------

* If ``./config/override/`` has **no** non-hidden files (only names starting with ``.``, such as ``.gitkeep``), the framework uses ``./config/default/``.
* If it has **any** non-hidden file or folder, the framework uses ``./config/override/`` instead—but then that directory must already contain **both** a valid global file and a ``dataflow_spec_mapping/`` directory. Otherwise startup fails with a message to copy the full layout from ``./config/default/``.
* If **neither** directory has non-hidden content, startup fails: add configuration under ``./config/default/``.

.. tip::

   Leave ``config/override`` empty until you can mirror the whole ``config/default`` tree.
