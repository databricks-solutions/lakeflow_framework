Framework Configuration
=======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Framework Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Global`
   * - **Databricks Docs:**
     - NA

The framework bundle ships a ``config`` directory at ``src/config`` (under the framework root you deploy). That directory holds **global** settings and supporting files used when the pipeline starts: the merged configuration drives spec format, Spark settings, table defaults, optional migrations, and related behaviour described in the feature pages linked below.

This page summarises **what** lives under framework ``config``, what is **required** versus **optional**, and how the optional ``config_override`` directory changes **which** folder the framework reads from—without changing your bundle layout or Spark settings keys.

What lives under ``src/config``
--------------------------------

Typical contents of ``src/config`` include:

* **Global framework file** — exactly one of ``global.json``, ``global.yaml``, or ``global.yml`` (see **Mandatory** below).
* **Dataflow spec mapping** — directory ``dataflow_spec_mapping/`` with versioned mapping JSON (**mandatory**; see **Mandatory** below and :doc:`feature_versioning_dataflow_spec`).
* **Per-environment substitutions** — ``<deployment target>_substitutions.json`` or ``.yaml`` / ``.yml`` (see :doc:`feature_substitutions`).
* **Per-environment secrets** — ``<deployment target>_secrets.json`` or ``.yaml`` / ``.yml`` (see :doc:`feature_secrets`).
* **Operational metadata** — ``operational_metadata_<layer>.json`` when you use pipeline layers (see :doc:`feature_operational_metadata`).

Paths are always resolved relative to the **active** framework config directory (either ``config`` or ``config_override``); see **Choosing the active config directory** below.

Mandatory
---------

The active framework config directory (``config`` or ``config_override``) **must** include all of the following.

**Global framework config file**

The framework **must** find **exactly one** of:

* ``global.json``
* ``global.yaml``
* ``global.yml``

If none exist, startup fails. If more than one exist, startup fails with an error—keep a single global file.

**``dataflow_spec_mapping`` directory**

The ``dataflow_spec_mapping/`` directory **must** exist under the active config root; it holds versioned mapping definitions used when specs are built and migrated. If ``config_override`` is in use and this directory (or a global file) is missing, startup fails—see **Completeness requirement** below.

**Other files**

Substitutions, secrets, and ``operational_metadata_<layer>.json`` files are **not** required for every deployment; add them when you use those features (see the linked feature pages).

Optional (keys inside ``global.*``)
-----------------------------------

The global file is a single JSON or YAML document. Common keys include:

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Key
     - Purpose
   * - ``pipeline_bundle_spec_format``
     - Default spec format (JSON or YAML) for pipeline bundles, and whether pipeline bundles may override it. See :doc:`feature_spec_format`.
   * - ``mandatory_table_properties``
     - Delta table properties applied to created tables. See :doc:`feature_mandatory_table_properties`.
   * - ``spark_config``
     - Spark configuration key/value pairs applied at pipeline init. See :doc:`feature_spark_configuration`.
   * - ``table_migration_state_volume_path``
     - Volume path for table migration checkpoints when using that feature. See :doc:`feature_table_migration`.
   * - ``dataflow_spec_version``
     - Optional global dataflow spec mapping version. See :doc:`feature_versioning_dataflow_spec`.
   * - ``override_max_workers``
     - Caps parallel workers when building dataflows from specs (when parallel build is enabled). See :doc:`feature_builder_parallelization`.
   * - ``pipeline_builder_disable_threading``
     - When ``true``, dataflows are created sequentially instead of in parallel. See :doc:`feature_builder_parallelization`.

Other keys may be added over time.

Configuration layout (default ``config``)
------------------------------------------

| **Scope: Global (framework bundle)**
| Under the default root ``src/config``:

* Global file: ``src/config/global.json`` (or ``.yaml`` / ``.yml``) — **mandatory**.
* ``dataflow_spec_mapping/`` directory — **mandatory** (same under ``src/config_override`` when that root is active).
* Substitutions: ``src/config/<deployment target>_substitutions.json`` (or YAML), matching targets in ``databricks.yml``. See :doc:`feature_substitutions`.
* Secrets: ``src/config/<deployment target>_secrets.json`` (or YAML). See :doc:`feature_secrets`.
* Mappings: ``src/config/dataflow_spec_mapping/<version>/dataflow_spec_mapping.json``. See :doc:`feature_versioning_dataflow_spec`.
* Operational metadata: ``src/config/operational_metadata_<layer>.json``. See :doc:`feature_operational_metadata`.

``config_override`` directory
-----------------------------

You may add a sibling directory ``src/config_override`` next to ``src/config``. It is intended for **forks** or deployments that want to override upstream ``config`` content without editing files under ``config`` (for example, to reduce merge conflicts when pulling updates from the open-source project).

**When it is ignored**

If ``config_override`` exists but contains **only** hidden entries (file or folder names starting with ``.``—for example ``.gitkeep``), the framework treats the directory as unused and continues to load everything from ``src/config``.

**When it is used**

If ``config_override`` contains **at least one** non-hidden file or folder, the framework switches the **active** framework config directory to ``config_override``. In that mode **all** framework config that normally comes from ``src/config``—global file, substitutions, secrets, ``dataflow_spec_mapping``, and operational metadata JSON—is read from ``src/config_override`` instead, using the **same** relative paths and filenames as under ``config``.

**Completeness requirement**

As soon as ``config_override`` is considered “in use” (because of a non-hidden entry), the framework requires a **full** mirror of what it needs from the default tree:

* A global file (one of ``global.json``, ``global.yaml``, ``global.yml``), and
* A ``dataflow_spec_mapping`` directory.

If either is missing, startup raises ``FileNotFoundError``. To resolve, copy the **entire** ``config`` tree into ``config_override`` and customise there, rather than adding only partial files.

Choosing the active config directory
------------------------------------

At startup the framework picks **one** root directory for all framework-level config paths:

* **Default:** ``./config`` under the framework bundle root.
* **Override:** ``./config_override`` when that directory is “in use” and passes the completeness check above.

You do not configure this choice in JSON; it follows the rules in the previous section. From a consumer perspective, treat ``config_override`` as an optional **drop-in replacement** for ``config`` with identical layout.

.. tip::

   Keep ``config_override`` empty of non-hidden files until you are ready to maintain a full copy; that way the framework keeps using ``src/config`` unchanged.
