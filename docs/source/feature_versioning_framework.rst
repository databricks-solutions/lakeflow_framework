Versioning - Framework
======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Framework Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Global`
   * - **Databricks Docs:**
     - NA

Overview
--------
The Lakeflow Framework supports versioning to allow different pipelines to use specific versions of the framework. 
This feature enables deploying specific versions of the framework to target environments. This is particularly useful for:

- Rolling back pipelines to use previous versions of the framework where current version is not suitable
- Testing new framework versions with specific pipelines
- Supporting gradual framework upgrades across different pipelines where some pipelines are not ready to upgrade yet 

In production environments (and CI/CD pipelines in general), the framework should be deployed twice:
1. First deployment with version set to "current" (default)
2. Second deployment with version set to a specific version number

This dual deployment strategy ensures that a previous stable version of the framework is always available for rollback purposes.


Deploy the framework with a specific version
-----------------------------------------------
The framework's version is configured in the databricks.yaml file, defaulting to "current":

.. code-block:: yaml

    variables:
      version:
        description: The framework version to deploy this bundle as
        default: current

To deploy a specific version, override the default using the ``BUNDLE_VAR_version`` environment variable:

.. code-block:: bash

    export BUNDLE_VAR_version="1.2.3"

For CI/CD deployments, execute two deployments:

.. code-block:: bash

    # First deployment - latest version
    export BUNDLE_VAR_version="current"
    databricks bundle deploy

    # Second deployment - specific version for rollback
    export BUNDLE_VAR_version="1.2.3"
    databricks bundle deploy


Set framework version for pipelines
-----------------------------------
By default, all pipelines (including production) should use the "current" version of the framework. Version locking should only be used in rollback scenarios when issues are discovered.

To specify which framework version a pipeline should use, set the ``framework_source_path`` variable in the pipeline bundle. The path follows this pattern:
``/Workspace/Users/[user]/.bundle/[framework_name]/[target]/[version]/files/src``

Set this path using the ``BUNDLE_VAR_framework_source_path`` environment variable during pipeline deployment:

.. code-block:: bash

    export BUNDLE_VAR_framework_source_path="/Workspace/Users/[user]/.bundle/[framework_name]/[target]/[version]/files/src"

.. note::
   The ``framework_source_path`` setting applies to all pipelines in the bundle. While individual pipeline versions can be 
   modified directly in the Databricks workspace, this is not recommended for production environments.

Best Practices
--------------
1. Default Version
   - Always default to the "current" version for both development and production pipelines
   - This ensures you benefit from the latest features and fixes

2. Version Locking
   - Only lock to specific versions during rollback scenarios
   - Return to "current" once issues are resolved

3. Rollback Strategy
   - In case of issues, quickly rollback by specifying the previous working version
   - Update the framework_source_path in pipeline configuration to point to the previous version



Version Management
------------------
1. Framework versions should follow semantic versioning (MAJOR.MINOR.PATCH)
2. Each release should be tagged in the source control system
3. The "current" version always points to the latest stable release
4. Previous versions are maintained for rollback purposes
5. Keep a changelog of versions and their changes

