Table Migration
===============

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - NA

The table migration feature allows you to migrate data from existing Delta or SDP tables into a new Spark Declarative Pipeline. It supports both HMS and UC catalogs.

General Concepts
----------------

There are two options for table migration, these are explained in detail below:

1. **Migration with auto starting version management**

   This is the default mode (``autoStartingVersionsEnabled`` defaults to ``true``). In this mode, the table migration will copy the data from the source table to the target table and will also manage the starting version of the target table.

2. **Migration without auto starting version management**

   In this mode, the table will be copied into the target table, but any starting versions for the sources of the target table need to be explicitly set in the dataflow specification, within the reader options of the corresponding views.

Configuration
-------------

Set as an attribute when creating your Data Flow Spec, refer to the :doc:`dataflow_spec_ref_table_migration` section of the :doc:`dataflow_spec_reference` documentation for more information.

**Key Configuration Options:**

* ``enabled``: Boolean flag to enable/disable table migration
* ``catalogType``: Type of catalog (\"hms\" or \"uc\")
* ``autoStartingVersionsEnabled``: Boolean flag to enable automatic starting version management (defaults to ``true``)
* ``sourceDetails``: Configuration for the source table to migrate from

**Required Global Configuration**

When table migration is enabled, you must specify the volume path for checkpoint state storage in your ``global.json|yaml`` configuration file at either the framework level (``src/config/global.json|yaml``) or pipeline bundle level (``src/pipeline_configs/global.json|yaml``):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
           "table_migration_state_volume_path": "/Volumes/{catalog}/{schema}/{volume}/checkpoint_state"
         }

   .. tab:: YAML

      .. code-block:: yaml

         table_migration_state_volume_path: /Volumes/{catalog}/{schema}/{volume}/checkpoint_state

**Parameter Details:**

* ``table_migration_state_volume_path``: The full path to a volume where checkpoint state files will be stored. This path must:
  
  - Point to a valid Databricks Unity Catalog volume
  - Be accessible by the pipeline with read/write permissions
  - Have sufficient storage capacity for checkpoint state files
  - Follow the pattern: ``/Volumes/{catalog}/{schema}/{volume}/{path}``

**Example Volume Configuration:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
           "table_migration_state_volume_path": "/Volumes/main/lakeflow_samples_staging/stg_volume/checkpoint_state"
         }

   .. tab:: YAML

      .. code-block:: yaml

         table_migration_state_volume_path: /Volumes/main/lakeflow_samples_staging/stg_volume/checkpoint_state

.. note::
   
   The volume path is required because table migration uses persistent file storage to maintain checkpoint state across pipeline runs. Without this configuration, table migration will fail during initialization. 

Migration with Auto Starting Versions
--------------------------------------

When migrating a table with auto starting version management, you need to migrate in a specific way:

1. Ensure the ``table_migration_state_volume_path`` is configured in your ``global.json`` file and the volume is accessible.
2. Create your pipeline bundle and dataflow specs with the table migration options appropriately set.
3. Deploy your pipeline bundle but ensure that you do not start the pipeline.
4. Allow any jobs / pipeline currently populating your target table and it's source to complete and then pause the jobs / pipelines populating both the target table and it's sources.
5. Execute your new pipeline manually and once complete, ensure:

  * That the pipeline executed successfully.
  * The row count of the target table matches the row count of the table you migrated from.
  * The checkpoint state files have been created in your volume storage, and they contain records for each source table including the starting versions.

6. Enable your pipeline in it's intended trigger mode.

How it Works
~~~~~~~~~~~~

The table migration feature operates through a state management system that ensures data consistency and proper version tracking during the migration process. Here's how it works:

**1. Migration Manager Initialization**

When a dataflow specification includes table migration details, the framework initializes a ``TableMigrationManager`` that:

* Validates the target format is Delta (table migration is only supported for Delta targets)
* Stores migration configuration including source table details and catalog type (HMS or UC)
* Prepares the migration state tracking system

**2. State Tracking and Version Management**

For migrations with auto starting version management enabled, the system:

* Creates or reads from checkpoint state files stored in volumes, partitioned by pipeline ID and table name
* Uses separate storage for initial versions (baseline) and tracking (current state)
* Tracks the current version of each source Delta table using ``DESCRIBE HISTORY`` commands
* Maintains a "ready" flag for each source indicating whether it's safe to start reading from the calculated starting version
* Stores the migration baseline version for each source table in CSV format

The checkpoint state storage is split into two parts, the initial versions and the tracking. The initial versions contain the baseline version for each source table at the time of migration, and the tracking contains the full state tracking information as described below:

* ``pipelineId``: The unique identifier of the pipeline
* ``targetTable``: The fully qualified name of the target table
* ``tableName``: The fully qualified name of the source table
* ``viewName``: The name of the view in the pipeline
* ``version``: The baseline version captured during migration
* ``currentVersion``: The latest version of the source table
* ``ready``: Boolean flag indicating if current version > baseline version

The state tracking store also serves as an audit trail for the migration process, and can be used to verify the migration process and the starting versions applied to the views.

**3. One-Time Migration Flow**

During pipeline execution, a special import flow is created that:

* Reads from the table to be migrated
* Handles both simple append scenarios and CDC Type 2 scenarios with proper delete record handling
* For SCD Type 2 migrations, creates additional views to properly handle delete markers and end-dating logic
* Executes as a "run once" flow to perform the initial data copy

**4. Starting Version Configuration**

After the migration completes, for ongoing pipeline execution:

* **Ready Sources**: Views are configured with ``startingVersion`` set to (baseline_version + 1) to continue reading from where the migration left off
* **Not Ready Sources**: Views are configured with a ``WHERE 1=0`` clause to prevent any data reading until the source table advances past the migration baseline

**5. Integration with Pipeline Flows**

The migration system integrates seamlessly with the standard pipeline execution:

* The migration flow executes once only
* Starting versions are applied directly to the dataflow specification during initialization
* The migration state is persisted in volume-based CSV files with proper partitioning
* The checkpoint state files are automatically maintained and updated as source tables advance

**6. Post Migration**

Migration is complete once:

* The table to be migrated has been successfully copied to the target table
* All sources are "ready" and allowed to flow into the target table again. This can be confirmed by checking the checkpoint state files in the volume storage.

If migration is complete, you can either completely remove the ``tableMigrationDetails`` from the dataflow specification, or you can set its enabled flag to false. Once the dataflow spec has been updated and redeployed, all migration artifacts (views, checkpoint state files, and run once flow) will be removed and you will be left with a clean pipeline.

**Technical Implementation Details**

* **Volume-Based State Storage**: Migration state is stored in CSV files within volumes, providing durability and scalability
* **Partitioned Storage**: Files are partitioned by ``pipelineId`` and ``tableName`` for efficient access and organization  
* **Dual Storage Paths**: Separate paths for initial versions (baseline capture) and tracking (ongoing state management)
* **Schema Enforcement**: Explicit schema definitions ensure data consistency across storage operations
* **Direct Specification Modification**: Starting versions are applied directly to the dataflow specification rather than during runtime
* **Automatic State Management**: The system automatically handles reading, writing, and updating of checkpoint state files

**Storage Structure**

The checkpoint state is stored in the following structure using the configured ``table_migration_state_volume_path``:

.. code-block::

   {table_migration_state_volume_path}/
   ├── initial_versions/
   │   └── pipelineId={pipeline_id}/targetTable={target_table}/
   │       └── part-*.csv  # Initial baseline versions
   └── tracking/
       └── pipelineId={pipeline_id}/targetTable={target_table}/
           └── part-*.csv  # Current tracking state

For example, with the configuration ``"table_migration_state_volume_path": "/Volumes/main/staging/volume/checkpoint_state"``, the actual file paths would be:

.. code-block::

   /Volumes/main/staging/volume/checkpoint_state/
   ├── initial_versions/
   │   └── pipelineId=my_pipeline/targetTable=my_target_table/
   │       └── part-00000-*.csv
   └── tracking/
       └── pipelineId=my_pipeline/targetTable=my_target_table/
           └── part-00000-*.csv

This approach ensures that no data is lost or duplicated during the migration process while maintaining full lineage and audit capabilities.


Migration without Auto Starting Versions
-----------------------------------------

The process will vary here depending on your migration scenario. It is important that:

* The starting versions are specified in the dataflow specification, prior to publishing your pipeline bundle and executing the pipeline.
* The jobs populating the target table and it's sources are paused, for the duration of the migration.
* You ensure that you get the correct source versions matching the version of the target table, at the time of migration.
