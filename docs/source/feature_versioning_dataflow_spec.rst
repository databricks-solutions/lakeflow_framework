Versioning - DataFlow Specs
===========================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Global` :bdg-success:`Individual DataFlow Specs`
   * - **Databricks Docs:**
     - NA

Overview
--------
The Lakeflow Framework supports dataflow specification versioning to enable backwards compatibility and gradual migration of dataflow specifications. 
This feature allows different mapping versions to be applied to transform the structure and content of dataflow specifications during processing. This is particularly useful for:

- Maintaining backwards compatibility when dataflow specification schemas evolve
- Gradually migrating existing dataflow specifications to new formats
- Testing new specification formats without breaking existing workflows
- Restructuring dataflow specifications to accommodate schema changes

The versioning system applies transformation mappings that can rename fields, move content to different locations, and remove obsolete fields in the dataflow specifications, allowing older specification formats to work with newer framework versions.


Mapping File Structure
----------------------
DataFlow specification mappings are stored in version-specific directories under:
``src/config/dataflow_spec_mapping/[version]/dataflow_spec_mapping.json``

Each mapping file contains transformation rules organized by:

- **global**: Mappings applied to all dataflow specification types
- **[dataflow_type]**: Mappings applied only to specific dataflow types (e.g., "standard", "flow", "materialized_view")

The mapping file supports three types of transformations:

1. **Renaming**: Change key names while preserving structure
2. **Moving**: Relocate keys and values to different parts of the specification
3. **Deleting**: Remove obsolete keys and their values

Mapping Operations
------------------

Rename Operations
~~~~~~~~~~~~~~~~~
Rename operations change key names while preserving the value and structure. Two types of renaming are supported:

- **rename_all**: Recursively renames keys throughout the entire specification structure
- **rename_specific**: Renames keys at specific nested paths

.. code-block:: json

    {
        "global": {
            "rename_all": {
                "oldKeyName": "newKeyName",
                "cdcApplyChanges": "cdcSettings"
            },
            "rename_specific": {
                "targetDetails.topic": "targetDetails.name"
            }
        }
    }

Move Operations
~~~~~~~~~~~~~~~
Move operations relocate keys and their values to different locations within the specification structure using dot notation for nested paths:

.. code-block:: json

    {
        "global": {
            "move": {
                "legacyConfig": "settings.advanced.legacyConfig",
                "sourceMetadata": "targetDetails.metadata",
                "targetDetails.topic": "targetDetails.sinkOptions.topic"
            }
        }
    }

Delete Operations
~~~~~~~~~~~~~~~~~
Delete operations remove keys and their values from the specification:

.. code-block:: json

    {
        "global": {
            "delete": [
                "deprecatedField",
                "obsoleteTimestamp"
            ]
        }
    }

Complete Example
~~~~~~~~~~~~~~~~
A comprehensive mapping file combining all operation types:

.. code-block:: json

    {
        "global": {
            "rename_all": {
                "cdcApplyChanges": "cdcSettings",
                "cdcApplyChangesFromSnapshot": "cdcSnapshotSettings"
            },
            "rename_specific": {
                "targetDetails.topic": "targetDetails.name"
            },
            "move": {
                "legacyConfig": "settings.advanced.legacyConfig",
                "targetDetails.topic": "targetDetails.sinkOptions.topic"
            },
            "delete": [
                "deprecatedField",
                "obsoleteTimestamp"
            ]
        },
        "flow": {
            "rename_all": {
                "flowSpecificOldField": "flowSpecificNewField"
            },
            "move": {
                "flowConfig": "flowGroups.0.configuration"
            },
            "delete": [
                "temporaryField"
            ]
        }
    }

Configure Global DataFlow Version
----------------------------------
To set a global dataflow specification version that applies to all specifications in a pipeline, configure the ``dataflow_spec_version`` parameter in your pipeline configuration.

This can be set in your pipeline substitutions file:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "dataflow_spec_version": "0.1.0"
         }

   .. tab:: YAML

      .. code-block:: yaml

         dataflow_spec_version: 0.1.0

When a global version is set, all dataflow specifications in the pipeline will use this mapping version unless overridden at the individual specification level.


Configure Individual DataFlow Specification Version
----------------------------------------------------
Individual dataflow specifications can override the global version by setting the ``dataFlowVersion`` field in their specification file:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "dataFlowId": "customer_data_flow",
             "dataFlowGroup": "customers",
             "dataFlowType": "standard",
             "dataFlowVersion": "0.1.0",
             "data": {
                 "sourceType": "delta",
                 "targetFormat": "delta",
                 "targetDetails": {
                     "table": "customers"
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         dataFlowId: customer_data_flow
         dataFlowGroup: customers
         dataFlowType: standard
         dataFlowVersion: 0.1.0
         data:
           sourceType: delta
           targetFormat: delta
           targetDetails:
             table: customers

The individual specification version takes precedence over the global version for that specific dataflow.

.. note::
   If neither global nor individual dataflow version is specified, no mappings will be applied and the specifications will be processed with their original structure.


Transformation Order
--------------------
The framework applies transformations in a specific order to ensure consistent results:

1. **Move Operations**: Keys are copied to their new locations first
2. **Rename Specific Operations**: Keys are renamed using ``rename_specific`` (targeted)
3. **Rename All Operations**: Keys are renamed using ``rename_all`` (recursive)
4. **Move Cleanup**: Original source keys from move operations are removed
5. **Delete Operations**: Keys specified in delete operations are removed


Best Practices
--------------
1. **Default Behavior**
   - Only use dataflow versioning when backwards compatibility is required
   - New specifications should use the current schema format without versioning

2. **Version Consistency**
   - Use consistent version numbers across related dataflow specifications

3. **Migration Strategy**
   - Start with global version configuration for bulk migrations
   - Use individual specification versions for gradual, selective migration
   - Remove version specifications once migration is complete
   - Plan transformation order carefully when combining multiple operation types

4. **Path Notation**
   - Use dot notation for nested paths (e.g., ``"parentKey.childKey.grandchildKey"``)
   - Ensure target paths exist or can be created for move operations
   - Be careful with path conflicts when moving and renaming the same keys

5. **Testing**
   - Thoroughly test mapping transformations in development environments
   - Validate that transformed specifications maintain expected functionality
   - Test all operation types (rename, move, delete) both individually and in combination
   - Keep original specifications as backup during migration


Version Management
------------------
1. Mapping versions should follow semantic versioning (MAJOR.MINOR.PATCH)
2. Each mapping version should be stored in its own directory under ``src/config/dataflow_spec_mapping/``
3. Maintain documentation of what each version transforms and why
4. Keep mapping files immutable once deployed to ensure consistency
5. Create new mapping versions rather than modifying existing ones
6. Archive obsolete mapping versions only after confirming no pipelines depend on them


Troubleshooting
---------------
**Common Issues:**

- **Mapping not applied**: Verify the version string exactly matches the directory name under ``dataflow_spec_mapping/``
- **Key not transformed**: Check that the key exists in the appropriate section (global or type-specific) of the mapping file
- **Specification validation errors**: Ensure transformed keys match the expected schema after mapping application
- **Move operation fails**: Verify source keys exist and target paths are valid using dot notation
- **Path conflicts**: Check for conflicts between move targets and existing keys
- **Delete operation errors**: Ensure keys to be deleted exist at the specified paths

**Debugging:**
Enable debug logging to see transformation application details:

.. code-block:: python

    # Framework logs will show:
    # "Global Dataflow Spec Mapping Version: [version]"
    # "Retrieved Dataflow Spec Specific Mapping Version: [version]. Dataflow Spec ID: [id]"
    # "Mapping applied to spec: [spec_path]" 
    # "New spec: [spec_data]" 