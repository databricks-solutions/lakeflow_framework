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

Overview
--------

Framework-level settings (global JSON/YAML, substitutions, secrets, spec
mappings, operational metadata) live under ``src/config/default/``. Individual
values can be overridden per-deployment using sparse files in
``src/local/config/`` — only the keys you want to change are needed.

Configuration
-------------

| **Scope: Global (framework bundle)**
| **Default:** ``src/config/default/`` — authoritative, always read.
| **Override:** ``src/local/config/`` — sparse override; deep-merged on top of defaults.

Under ``src/config/default/`` you normally have:

* exactly one global file: ``global.json``, ``global.yaml``, or ``global.yml``
* a ``dataflow_spec_mapping/`` directory (see :doc:`feature_versioning_dataflow_spec`)
* optional per-target substitution and secrets files (see :doc:`feature_substitutions`, :doc:`feature_secrets`)
* optional ``operational_metadata_<layer>.json`` (see :doc:`feature_operational_metadata`)
* optional ``logger.json`` (see :doc:`feature_logging`)

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

Local override (``src/local/config/``)
---------------------------------------

Place sparse JSON/YAML files in ``src/local/config/`` to override individual
keys without copying the entire default file. The framework **deep-merges** the
overlay on top of the defaults at runtime:

* Dict values are merged recursively — only the keys present in the overlay
  are changed.
* Non-dict values and lists are replaced wholesale.
* Keys not present in the overlay retain their default values.

Example — change one global setting without touching the rest of ``global.json``:

.. code-block:: json

   {
     "dataflow_spec_version": "0.0.3"
   }

Save this as ``src/local/config/global.json``. All other keys from
``src/config/default/global.json`` are kept unchanged.

For **directory-based config** (e.g. ``dataflow_spec_mapping/``), place the
entire override directory in ``src/local/config/`` — the local directory takes
full precedence over the default.

See ``src/local/config/README.md`` in the framework bundle for the full list of
supported files and migration instructions.

.. deprecated:: v0.14.0

   **config/override/**

   The ``config/override/`` mechanism (whole-tree replacement) is deprecated as
   of v0.14.0 and will be removed in v1.0.0. Migrate to ``src/local/config/``
   sparse files instead.

   **Migration steps:**

   1. Identify which keys in your ``config/override/`` files differ from
      ``config/default/``.
   2. Create sparse files in ``src/local/config/`` containing only those keys.
   3. Remove all files from ``config/override/`` (leave the ``.gitkeep``).

   A ``DeprecationWarning`` is emitted at pipeline startup when
   ``config/override/`` contains non-hidden files.
